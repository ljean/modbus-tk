#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Exercise the simulator's command dispatcher through its TCP RPC handler."""

import socket
import threading
import unittest

from modbus_tk import modbus_tcp, simulator
from modbus_tk.simulator_rpc_client import SimulatorRpcClient


class TestRpcClientFailures(unittest.TestCase):
    def test_socket_closed_on_failures(self):
        for stage in ("settimeout", "connect", "sendall", "recv"):
            error = socket.timeout("test timeout")

            class FailingSocket(object):
                closed = False

                def settimeout(self, timeout):
                    if stage == "settimeout":
                        raise error

                def connect(self, address):
                    if stage == "connect":
                        raise error

                def sendall(self, data):
                    if stage == "sendall":
                        raise error

                def recv(self, size):
                    raise error

                def close(self):
                    self.closed = True

            sock = FailingSocket()
            original = socket.socket
            try:
                socket.socket = lambda *args: sock
                with self.assertRaises(socket.timeout) as caught:
                    SimulatorRpcClient().has_slave(1)
                self.assertIs(caught.exception, error)
                self.assertTrue(sock.closed)
            finally:
                socket.socket = original


class BoundedTCPServer(simulator.SocketServer.TCPServer):
    def get_request(self):
        sock, address = simulator.SocketServer.TCPServer.get_request(self)
        sock.settimeout(1)
        return sock, address


class TestRpcHandler(unittest.TestCase):
    def setUp(self):
        # Use fresh queues and an ephemeral listening port, without starting
        # the interactive console or binding the normal fixed RPC/Modbus ports.
        self.old_input, self.old_output = simulator.INPUT_QUEUE, simulator.OUTPUT_QUEUE
        simulator.INPUT_QUEUE = simulator.queue.Queue()
        simulator.OUTPUT_QUEUE = simulator.queue.Queue()
        self.server = BoundedTCPServer(("127.0.0.1", 0), simulator.RpcHandler)
        self.client = SimulatorRpcClient(*self.server.server_address, timeout=2)
        self.errors = []
        self.server.handle_error = lambda *args: self.errors.append("RPC handler failed")
        old_rpc, old_console = simulator.RpcInterface, simulator.ConsoleInterface
        try:
            simulator.RpcInterface = lambda: None
            simulator.ConsoleInterface = lambda: None
            self.app = simulator.Simulator(server=modbus_tcp.TcpServer(port=0))
        finally:
            simulator.RpcInterface, simulator.ConsoleInterface = old_rpc, old_console

        def dispatch():
            try:
                self.app._handle()
            except Exception as error:
                self.errors.append(error)
                # Also unblock the RPC handler if the dispatcher failed.
                simulator.OUTPUT_QUEUE.put("dispatcher failed")

        self.dispatcher = threading.Thread(target=dispatch)
        self.dispatcher.daemon = True
        self.listener = threading.Thread(target=self.server.serve_forever, args=(0.01,))
        self.listener.daemon = True
        self.dispatcher.start()
        self.listener.start()

    def tearDown(self):
        if self.dispatcher.is_alive():
            simulator.INPUT_QUEUE.put("quit")
        self.server.shutdown()
        self.server.server_close()
        self.listener.join(2)
        self.dispatcher.join(2)
        try:
            self.assertFalse(self.listener.is_alive())
            self.assertFalse(self.dispatcher.is_alive())
        finally:
            simulator.INPUT_QUEUE, simulator.OUTPUT_QUEUE = self.old_input, self.old_output

    def request(self, command):
        sock = socket.create_connection(self.server.server_address, timeout=2)
        try:
            sock.sendall(command)
            chunks = []
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks)
        finally:
            sock.close()

    def test_rpc_commands_and_errors(self):
        self.assertEqual(self.request(b"  add_slave 1\r\n"), b"add_slave done: 1\r\n")
        self.assertEqual(self.request(b"add_block 1 data 3 0 2"), b"add_block done: data\r\n")
        self.assertEqual(self.request(b"set_values 1 data 0 12 34"), b"set_values done: 12 34\r\n")
        self.assertEqual(self.request(b"get_values 1 data 0 2"), b"get_values done: 12 34\r\n")
        self.assertEqual(self.request(b"unknown"), b"error: unknown command unknown\r\n")
        self.assertTrue(self.request(b"get_values 1 missing 0 1").startswith(b"get_values error: "))
        self.assertEqual(self.request(b"has_slave 1"), b"has_slave done: 1\r\n")
        self.assertEqual(self.request(b"add_block 1 \xc3\xa9 3 10 1"), b"add_block done: \xc3\xa9\r\n")
        self.assertEqual(self.request(b"get_values 1 \xc3\xa9 10 1"), b"get_values done: 0\r\n")
        self.assertEqual(self.request(b"quit"), b"bye-bye\r\n")
        self.dispatcher.join(2)
        self.assertFalse(self.dispatcher.is_alive())
        self.assertEqual(self.errors, [])

    def test_rpc_client_commands_and_errors(self):
        self.assertEqual(self.client.add_slave(2), "2")
        self.assertTrue(self.client.has_slave(2))
        self.assertEqual(self.client.add_block(2, "data", 3, 0, 3000), "data")
        self.assertEqual(self.client.set_values(2, "data", 0, (12, 34)), "12 34")
        self.assertEqual(self.client.get_values(2, "data", 0, 3000), (12, 34) + (0,) * 2998)
        with self.assertRaises(Exception) as error:
            self.client.get_values(2, "missing", 0, 1)
        self.assertTrue(str(error.exception).startswith("get_values error: "))
        self.assertEqual(self.client.get_values(2, "data", 0, 2), (12, 34))
        self.client.remove_all_blocks(2)
        self.client.remove_slave(2)
        self.assertFalse(self.client.has_slave(2))
        self.client.add_slave(3)
        self.client.remove_all_slaves()
        self.assertFalse(self.client.has_slave(3))
        self.assertEqual(self.errors, [])

    @unittest.skipIf(simulator.modbus_tk.utils.PY2, "Python 2 client uses byte strings")
    def test_rpc_client_utf8(self):
        self.client.add_slave(1)
        name = b"\xc3\xa9".decode("utf-8")
        self.assertEqual(self.client.add_block(1, name, 3, 0, 1), name)
        self.assertEqual(self.client.get_values(1, name, 0, 1), (0,))
        self.assertEqual(self.errors, [])

    @unittest.skipUnless(simulator.modbus_tk.utils.PY2, "Python 2 byte-string compatibility")
    def test_rpc_client_non_utf8_bytes(self):
        self.client.add_slave(1)
        self.assertEqual(self.client.add_block(1, b"\xff", 3, 0, 1), b"\xff")
        self.assertEqual(self.client.get_values(1, b"\xff", 0, 1), (0,))
        self.assertEqual(self.errors, [])


if __name__ == "__main__":
    unittest.main()
