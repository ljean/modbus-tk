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
import Queue
import time
import sys

LOGGER = modbus_tk.utils.create_logger()

class TestStress(unittest.TestCase):
    """Test the TcpMbap class"""
                
    def setUp(self):
        self.server = modbus_tcp.TcpServer()
                
    def tearDown(self):
        self.server.stop()

    def testGarbageData(self):
        """Send Garbage data and make sure that it doesn't kill everything"""
        slave1 = self.server.add_slave(1)
        slave1.add_block("c0-100", modbus_tk.defines.COILS, 0, 100)
        self.server.set_verbose(True)
        self.server.start()
        time.sleep(1.0)
        
        master1 = modbus_tcp.TcpMaster()
        master2 = modbus_tcp.TcpMaster()
        master1.open()
        master2.open()
        
        master1._send("hello world!")
        
        result = master2.execute(1, modbus_tk.defines.WRITE_SINGLE_COIL, 0, output_value=1)
        self.assertEqual((0, int("ff00", 16)), result)
        values = slave1.get_values("c0-100", 0, 1)
        self.assertEqual((1,), values)
        
        master1.close()
        master2.close()

    def testSeveralClients(self):
        """check that the server can serve 15 clients in parallel"""

        masters = [modbus_tcp.TcpMaster(timeout_in_sec=5.0)] * 15

        slave = self.server.add_slave(1)

        q = Queue.Queue()

        slave.add_block("a", modbus_tk.defines.HOLDING_REGISTERS, 0, 100)
        slave.set_values("a", 0, range(100))
        
        self.server.start()
        time.sleep(1.0)
        
        def read_vals(master):
            try:
                for i in xrange(100):
                    result = master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 0, 100)
                    if result != tuple(range(100)):
                        q.put(1)
                    time.sleep(0.1)
            except Exception, msg:
                LOGGER.error(msg)
                q.put(1)
        
        threads = []
        for m in masters:
            threads.append(threading.Thread(target=read_vals, args=(m, )))
        for t in threads: t.start()
        LOGGER.debug("all threads have been started")
        for t in threads: t.join()
        LOGGER.debug("all threads have done")
        self.assert_(q.empty())
                       
if __name__ == '__main__':
    unittest.main(argv = sys.argv)
