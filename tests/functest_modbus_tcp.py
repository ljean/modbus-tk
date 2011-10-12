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
import modbus_tk.modbus_tcp as modbus_tcp
import threading
import struct
import logging
import socket
import modbus_tk.utils as utils
import time
import sys
from functest_modbus import TestQueries, TestQueriesSetupAndTeardown

LOGGER = modbus_tk.utils.create_logger("udp")

class TestConnection(unittest.TestCase):
    """Test the TcpMbap class"""
    def setUp(self):
        self.server = modbus_tcp.TcpServer()
        self.master = modbus_tcp.TcpMaster()
    
    def tearDown(self):
        self.master.close()
        self.server.stop()

    def testConnectOnSlave(self):
        """Setup a slave and check that the master can connect"""
        self.server.start()
        time.sleep(1.0)
        
        self.master.set_timeout(1.0)
        self.master.open()
        time.sleep(1.0)
        
        #close everything
        self.master.close()
        self.server.stop()
        time.sleep(1.0)
        
        #and try to reconnect --> should fail
        try:
            self.master.open()
        except socket.error, message:
            return
        self.assert_(False)
        
    def testConnectionErrorNoTimeoutDefined(self):
        """Check that an error is raised on connection error"""
        master = modbus_tcp.TcpMaster()
        try:
            master.open()
        except socket.error, message:
            return
        self.assert_(False)
                
    def testReadBlock(self):
        """Add 1 block on the slave and let's the master running the values"""
        slave = self.server.add_slave(1)
        slave.add_block("hr0-100", modbus_tk.defines.HOLDING_REGISTERS, 0, 100)
        slave.set_values("hr0-100", 0, range(100))
        
        self.server.start()
        time.sleep(1.0)
        self.master.open()
        time.sleep(1.0)
        
        result = self.master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 0, 100)
        self.assertEqual(tuple(range(100)), result)
        
        self.master.close()
        self.server.stop()

    def testCleanConnections(self):
        """Check that the server is cleaning closed connections"""
        self.server.start()
        time.sleep(1.0)
        
        masters = [modbus_tcp.TcpMaster() for i in xrange(10)]
        for m in masters:
            m.open()
            
        for m in masters:
            m.close()
            
        time.sleep(5.0)
        self.assertEqual(1, len(self.server._sockets))
        
    def testReopenMaster(self):
        """Check that master can open the connection several times"""
        slave = self.server.add_slave(1)
        slave.add_block("myblock", modbus_tk.defines.HOLDING_REGISTERS, 500, 100)
        slave.set_values("myblock", 500, range(100))
        
        self.server.start()
        time.sleep(1.0)
        
        self.master.set_timeout(1.0)
        self.master.open()
        
        for x in xrange(5):
            self.master.close()
            time.sleep(1.0)
            self.master.open()
            time.sleep(1.0)
            result = self.master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 500, 100)
            self.assertEqual(tuple(range(100)), result)
    
    def testReopenServer(self):
        """Check that server can open the connection several times"""
        slave = self.server.add_slave(1)
        slave.add_block("myblock", modbus_tk.defines.HOLDING_REGISTERS, 500, 100)
        slave.set_values("myblock", 500, range(100))
        
        self.server.start()
        time.sleep(1.0)
        
        for x in xrange(3):
            time.sleep(1.0)
            self.server.stop()
            time.sleep(1.0)
            self.server.start()
            time.sleep(1.0)
            
            m = modbus_tcp.TcpMaster()
            m.open()
            result = m.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 500, 100)
            self.assertEqual(tuple(range(100)), result)


class TcpTestQueries(TestQueries, unittest.TestCase):
    """Test the modbus protocol over TCP communication"""
    def _get_server(self):
        return modbus_tcp.TcpServer()
        
    def _get_master(self):
        return modbus_tcp.TcpMaster()        


class TestTcpSpecific(TestQueriesSetupAndTeardown, unittest.TestCase):
    
    def _get_server(self):
        return modbus_tcp.TcpServer()
        
    def _get_master(self):
        return modbus_tcp.TcpMaster()
        
    def testReadWithWrongFunction(self):
        """check that an error is raised where reading on 2 consecutive blocks"""
        self.assertRaises(modbus_tk.modbus.ModbusFunctionNotSupportedError, self.master.execute, 1, 55, 0, 10)
        bad_query = struct.pack(">HHHBH", 0, 0, 3, 0, 55)
        try:
            self.master._sock.send(bad_query)
        except modbus_tk.modbus.ModbusError, ex:
            self.assertEqual(ex.get_exception_code(), 1)
            return
            
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
                LOGGER.debug("set_val started")
                id = 11
                for i in xrange(50):
                    for s in slaves:
                        s.set_values("a", 0, [i]*100)
                        result = self_.master.execute(id, modbus_tk.defines.READ_HOLDING_REGISTERS, 0, 100)
                        id += 1
                        if id > 12: id = 11
                        #time.sleep(0.2)
            except Exception, msg:
                LOGGER.error(msg)
                q.put(1)
        
        threads = [threading.Thread(target=set_val, args=(self, slaves, q)) for i in xrange(5)]
        for t in threads: t.start()
        LOGGER.debug("all threads have been started")
        for t in threads: t.join()
        LOGGER.debug("all threads have done")
        self.assert_(q.empty())
            
    def testWriteSingleCoilInvalidValue(self):
        """Check taht an error is raised when writing a coil with an invalid value"""
        self.master._send(struct.pack(">HHHBBHH", 0, 0, 6, 1, modbus_tk.defines.WRITE_SINGLE_COIL, 0, 1))
        response = self.master._recv()
        self.assertEqual(response, struct.pack(">HHHBBB", 0, 0, 3, 1, modbus_tk.defines.WRITE_SINGLE_COIL+128, 3))

if __name__ == '__main__':
        unittest.main(argv = sys.argv)
