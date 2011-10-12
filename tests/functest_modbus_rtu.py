#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Modbus TestKit: Implementation of Modbus protocol in python

 (C)2009 - Luc Jean - luc.jean@gmail.com
 (C)2009 - Apidev - http://www.apidev.fr

 This is distributed under GNU LGPL license, see license.txt
"""

import unittest
import modbus_tk
import modbus_tk.modbus_rtu as modbus_rtu
import modbus_tk.hooks as hooks
import threading
import struct
import logging
import modbus_tk.utils as utils
import time
import sys
import serial
from functest_modbus import TestQueries, TestQueriesSetupAndTeardown

LOGGER = modbus_tk.utils.create_logger("udp")

import os
if os.name == "nt":
    SERVER_PORT = "COM1"
    MASTER_PORT = "COM2"
elif os.name == "posix": 
    SERVER_PORT = "/dev/ttyS0"
    MASTER_PORT = "/dev/ttyS1"
else:
    raise Exception("The %d os is not supported yet" % (os.name))

class TestConnection(TestQueriesSetupAndTeardown, unittest.TestCase):
    def _get_server(self):
        return modbus_rtu.RtuServer(serial.Serial(port=SERVER_PORT, baudrate=9600))
        
    def _get_master(self):
        return modbus_rtu.RtuMaster(serial.Serial(port=MASTER_PORT, baudrate=9600))
    
    def testOpenConnection(self):
        """Check that master and server can open the serial port"""
        #close everything
        self.master.close()
        self.server.stop()
        time.sleep(1.0)
        
        self.master.open()
        self.master.open()
        
    def testErrorOnOpeningInUsePort(self):
        """Check that an error is raised if opening a port twice"""
        self.assertRaises(serial.SerialException, serial.Serial, SERVER_PORT)

    def testReadBlock(self):
        """Add 1 block on the slave and let's the master running the values"""
        slave = self.server.get_slave(1)
        slave.add_block("myblock", modbus_tk.defines.HOLDING_REGISTERS, 500, 100)
        slave.set_values("myblock", 500, range(100))
        
        result = self.master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 500, 100)
        self.assertEqual(tuple(range(100)), result)
        
        self.master.close()
        self.server.stop()

    def testReopenMaster(self):
        """Check that master can open the serial port several times"""
        #close everything
        slave = self.server.get_slave(1)
        slave.add_block("myblock", modbus_tk.defines.HOLDING_REGISTERS, 500, 100)
        slave.set_values("myblock", 500, range(100))
        
        for x in xrange(5):
            self.master.close()
            time.sleep(1.0)
            self.master.open()
            time.sleep(1.0)
            result = self.master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 500, 100)
            self.assertEqual(tuple(range(100)), result)
    
    def testReopenServer(self):
        """Check that server can open the serial port several times"""
        slave = self.server.get_slave(1)
        slave.add_block("myblock", modbus_tk.defines.HOLDING_REGISTERS, 500, 100)
        slave.set_values("myblock", 500, range(100))
        
        for x in xrange(5):
            self.server.stop()
            time.sleep(1.0)
            self.server.start()
            time.sleep(1.0)
            result = self.master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 500, 100)
            self.assertEqual(tuple(range(100)), result)
    
        

class TestRtuSpecific(TestQueriesSetupAndTeardown, unittest.TestCase):
    def _get_server(self):
        return modbus_rtu.RtuServer(serial.Serial(port=SERVER_PORT, baudrate=9600))
        
    def _get_master(self):
        return modbus_rtu.RtuMaster(serial.Serial(port=MASTER_PORT, baudrate=9600))        
    
    def testExpectedLength(self):
        """check that expected length doesn't cause an error"""
        self.slave1.set_values("hr0-100", 0, range(100))
        self.master.set_verbose(True)
        result = self.master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 0, 100, expected_length=205)
        self.master.set_verbose(False)
        self.assertEqual(tuple(range(100)), result)

    def testExpectedLengthTooShort(self):
        """check that an error is raised if expected_length is too low"""
        self.slave1.set_values("hr0-100", 0, range(100))
        ok = True
        def check_length_hook(args):
            (master, response) = args
            LOGGER.debug("expected: %d - actual: %d", check_length_hook.expected_length, len(response))
            check_length_hook.test.assertEqual(check_length_hook.expected_length, len(response))
                    
        check_length_hook.test = self
        hooks.install_hook("modbus_rtu.RtuMaster.after_recv", check_length_hook)
        
        for x in (5, 204):
            try:
                check_length_hook.expected_length = x
                self.master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 0, 100, expected_length=x)
            except: 
                pass
            else:
                ok = False
        hooks.uninstall_hook("modbus_rtu.RtuMaster.after_recv", check_length_hook)
            
        self.assert_(ok)

    def testExpectedLengthTooLong(self):
        """check that no impact if expected_length is too high"""
        self.slave1.set_values("hr0-100", 0, range(100))
        result = self.master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 0, 100, expected_length=3000)
        self.assertEqual(tuple(range(100)), result)

    def testReadWithWrongFunction(self):
        """check that an error is raised when sending a query with an invalid function code"""
        self.assertRaises(modbus_tk.modbus.ModbusFunctionNotSupportedError, self.master.execute, 1, 55, 0, 10)
        bad_query = struct.pack(">BB", 1, 55)
        crc = struct.pack(">H", utils.calculate_crc(bad_query))
        bad_query += crc
        try:
            self.master._send(bad_query)
            self.master._recv()
        except modbus_tk.modbus.ModbusError, ex:
            self.assertEqual(ex.get_exception_code(), 1)
            return

    def testWriteSingleCoilInvalidValue(self):
        """Check that an error is raised when writing a coil with an invalid value"""
        bad_query = struct.pack(">BBHH", 1, modbus_tk.defines.WRITE_SINGLE_COIL, 0, 1)
        crc = struct.pack(">H", utils.calculate_crc(bad_query))
        bad_query += crc
        self.master.set_verbose(True)
        self.master._send(bad_query)
        response = self.master._recv()
        self.assertEqual(response[:-2], struct.pack(">BBB", 1, modbus_tk.defines.WRITE_SINGLE_COIL+128, 3))
        
    def testMultiThreadAccess(self):
        """check that the modbus call are thread safe"""

        slaves = []
        slaves.append(self.server.add_slave(11))
        slaves.append(self.server.add_slave(12))
        import Queue
        
        q = Queue.Queue()

        for s in slaves:
            s.add_block("a", modbus_tk.defines.HOLDING_REGISTERS, 0, 100)
        
        def set_val(self_, slaves, q):
            try:
                id = 11
                for i in xrange(5):
                    for s in slaves:
                        s.set_values("a", 0, [i]*100)
                        result = self_.master.execute(id, modbus_tk.defines.READ_HOLDING_REGISTERS, 0, 100)
                        id += 1
                        if id > 12: id = 11
            except Exception, msg:
                LOGGER.error(msg)
                q.put(1)
        
        threads = [threading.Thread(target=set_val, args=(self, slaves, q)) for i in xrange(3)]
        for t in threads: t.start()
        LOGGER.debug("all threads have been started")
        for t in threads: t.join()
        LOGGER.debug("all threads have done")
        self.assert_(q.empty())


class RtuTestQueries(TestQueries, unittest.TestCase):
    """Test the modbus protocol over RTU communication"""
    def _get_server(self):
        port = serial.Serial(port=SERVER_PORT, baudrate=9600, bytesize=8, parity='N', stopbits=1, xonxoff=0)
        server = modbus_rtu.RtuServer(port)
        #server.set_verbose(True)
        return server
        
    def _get_master(self):
        port = serial.Serial(port=MASTER_PORT, baudrate=9600, bytesize=8, parity='N', stopbits=1, xonxoff=0)
        master = modbus_rtu.RtuMaster(port)
        #master.set_verbose(True)
        return master        
                       
if __name__ == '__main__':
    unittest.main(argv = sys.argv)
