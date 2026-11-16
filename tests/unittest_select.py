"""Socket readiness must also work with descriptor numbers above FD_SETSIZE."""

import errno
import os
import socket
import sys
import unittest

from modbus_tk import utils

try:
    import fcntl
    import resource
except ImportError:
    fcntl = None
    resource = None


class TestFlushSocket(unittest.TestCase):
    def setUp(self):
        if not hasattr(socket, 'socketpair'):
            self.skipTest('requires socketpair')
        self.reader, self.writer = socket.socketpair()
        self.addCleanup(self.reader.close)
        self.addCleanup(self.writer.close)

    def high_reader(self):
        if fcntl is None or sys.version_info < (3, 3):
            self.skipTest('requires Unix descriptors and Python 3.3 or later')
        soft_limit = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
        if soft_limit != resource.RLIM_INFINITY and soft_limit <= 1024:
            self.skipTest('current descriptor limit does not allow descriptor 1024')
        try:
            descriptor = fcntl.fcntl(self.reader.fileno(), fcntl.F_DUPFD, 1024)
        except OSError as error:
            if error.errno == errno.EMFILE:
                self.skipTest('no descriptor at or above 1024 is available within the process limit')
            raise
        try:
            reader = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, fileno=descriptor)
        except Exception:
            os.close(descriptor)
            raise
        self.addCleanup(reader.close)
        self.assertGreaterEqual(reader.fileno(), 1024)
        return reader

    def exercise_flush(self, reader):
        self.assertIsNone(utils.flush_socket(reader, 3))
        self.writer.sendall(b'stale response')
        self.assertIsNone(utils.flush_socket(reader, 3))
        reader.settimeout(0.05)
        with self.assertRaises(socket.timeout):
            reader.recv(1)
        self.writer.sendall(b'new response')
        self.assertEqual(reader.recv(12), b'new response')

    def test_high_descriptor(self):
        self.exercise_flush(self.high_reader())

    def test_low_descriptor(self):
        self.exercise_flush(self.reader)

    def test_high_descriptor_closed_peer_retains_limit(self):
        reader = self.high_reader()
        self.writer.close()
        with self.assertRaises(Exception) as raised:
            utils.flush_socket(reader, 3)
        self.assertEqual(str(raised.exception),
                         'flush_socket: maximum number of iterations reached')

    def test_poll_timeout_and_readiness(self):
        self.assertEqual(utils._select_sockets([self.reader], 0.02), [])
        self.writer.sendall(b'queued')
        self.assertEqual(utils._select_sockets([self.reader], 1), [self.reader])
        self.assertEqual(self.reader.recv(6), b'queued')
        self.writer.close()
        self.assertEqual(utils._select_sockets([self.reader], 1), [self.reader])
        self.assertEqual(self.reader.recv(1), b'')

    def test_select_fallback(self):
        original = getattr(utils.select, 'poll', None)
        utils.select.poll = None
        try:
            self.exercise_flush(self.reader)
        finally:
            if original is None:
                del utils.select.poll
            else:
                utils.select.poll = original
