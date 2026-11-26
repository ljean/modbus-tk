"""Regression tests for hook dispatch and the lock inversion in issue #140."""
import os
import subprocess
import sys
import threading
import unittest

from modbus_tk import defines, hooks, modbus


def deadlock_probe():
    slave = modbus.Slave(1)
    slave.add_block('values', defines.HOLDING_REGISTERS, 0, 1)
    callback_entered = threading.Event()
    writer_locked = threading.Event()
    callback_values = []
    block_values = []
    lock = slave._data_lock

    class ObservedLock:
        def __enter__(self):
            lock.acquire()
            if threading.current_thread().name == 'writer':
                writer_locked.set()

        def __exit__(self, *args):
            lock.release()

    # Observe the real slave lock without replacing its mutual exclusion.
    slave._data_lock = ObservedLock()

    def before_send(args):
        callback_entered.set()
        if not writer_locked.wait(2):
            raise RuntimeError('writer did not acquire the slave lock')
        callback_values.append(slave.get_values('values', 0, 1))

    hooks.install_hook('modbus_tcp.TcpServer.before_send', before_send)
    hooks.install_hook('modbus.ModbusBlock.setitem', lambda args: block_values.append(args[2]))
    reader = threading.Thread(target=hooks.call_hooks,
                              args=('modbus_tcp.TcpServer.before_send', ()), daemon=True)
    reader.start()
    if not callback_entered.wait(2):
        raise RuntimeError('callback did not start')
    writer = threading.Thread(target=slave.set_values, args=('values', 0, [42]),
                              name='writer', daemon=True)
    writer.start()
    writer.join(2)
    reader.join(2)
    assert not writer.is_alive() and not reader.is_alive(), 'hook/slave lock deadlock'
    assert callback_values == [(42,)], callback_values
    assert block_values == [[42]], block_values


class TestHooks(unittest.TestCase):
    def setUp(self):
        self.name = 'test.snapshot'
        hooks.install_hook(self.name, lambda args: None)
        hooks.uninstall_hook(self.name)

    def tearDown(self):
        hooks.uninstall_hook(self.name)

    def test_slave_lock_inversion(self):
        # A broken implementation must not leave deadlocked threads in the suite.
        env = os.environ.copy()
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env['PYTHONPATH'] = root + os.pathsep + env.get('PYTHONPATH', '')
        result = subprocess.run([sys.executable, __file__, '--deadlock-probe'],
                                env=env, capture_output=True, text=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_registration_changes_apply_to_next_dispatch(self):
        calls = []

        def first(args):
            calls.append('first')
            hooks.uninstall_hook(self.name)
            hooks.install_hook(self.name, lambda args: calls.append('new'))

        hooks.install_hook(self.name, first)
        hooks.install_hook(self.name, lambda args: calls.append('second'))
        hooks.call_hooks(self.name, ())
        self.assertEqual(calls, ['first', 'second'])
        hooks.call_hooks(self.name, ())
        self.assertEqual(calls, ['first', 'second', 'new'])

    def test_first_non_none_result_stops_dispatch(self):
        hooks.install_hook(self.name, lambda args: None)
        hooks.install_hook(self.name, lambda args: args[0])
        hooks.install_hook(self.name, lambda args: self.fail('called after a result'))
        self.assertEqual(hooks.call_hooks(self.name, (False,)), False)
        self.assertIsNone(hooks.call_hooks('test.absent', ()))


if __name__ == '__main__':
    if '--deadlock-probe' in sys.argv:
        deadlock_probe()
    else:
        unittest.main()
