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
import threading
import struct
import logging
import modbus_tk.utils as utils
import time
import sys

LOGGER = modbus_tk.utils.create_logger("udp")

class TestQueriesSetupAndTeardown:
    """This is not a test case, but can be used by Rtu and Tcp test cases"""
    
    def setUp(self):
        self.master = self._get_master()
        self.server = self._get_server()
        
        self.slave1 = self.server.add_slave(1)
        self.slave1.add_block("hr0-100", modbus_tk.defines.HOLDING_REGISTERS, 0, 100)
        self.slave1.add_block("hr100-100", modbus_tk.defines.HOLDING_REGISTERS, 100, 200)
        self.slave1.add_block("ai100-50", modbus_tk.defines.ANALOG_INPUTS, 100, 150)
        self.slave1.add_block("c0-100", modbus_tk.defines.COILS, 0, 100)
        self.slave1.add_block("di100-1", modbus_tk.defines.DISCRETE_INPUTS, 100, 1)
        self.slave1.add_block("di200-10", modbus_tk.defines.DISCRETE_INPUTS, 200, 10)
        self.slave1.add_block("hr1000-1500", modbus_tk.defines.HOLDING_REGISTERS, 1000, 500)
        self.slave1.add_block("c1000-4000", modbus_tk.defines.COILS, 1000, 3000)
                
        self.slave5 = self.server.add_slave(5)
        self.slave5.add_block("hr0-100", modbus_tk.defines.HOLDING_REGISTERS, 300, 20)
        
        self.server.start()
        time.sleep(0.1)
        self.master.set_timeout(1.0)
        self.master.open()
            
    def tearDown(self):
        self.master.close()
        self.server.stop()

class TestQueries(TestQueriesSetupAndTeardown):
    """This is not a test case, but can be used by Rtu and Tcp test cases"""
    
    """Test the modbus protocol"""
    def testReadHoldingRegisters(self):
        """set the values of holding registers check that the values are read correctly"""
        self.slave1.set_values("hr0-100", 0, range(100))
        result = self.master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 0, 100)
        self.assertEqual(tuple(range(100)), result)
        
        self.slave1.set_values("hr1000-1500", 1000, range(125))
        result = self.master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 1000, 125)
        self.assertEqual(tuple(range(125)), result)
        
    def testRead100HoldingRegistersOn2Blocks(self):
        """check that an error is raised where reading on 2 consecutive blocks"""
        try:
            self.master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 50, 100)
        except modbus_tk.modbus.ModbusError, ex:
            self.assertEqual(ex.get_exception_code(), 2)
            return
        self.assert_(False)

    def testRead5HoldingRegisters(self):
        """set the values of 3 registers and let's the master reading 5 values"""
        self.slave1.set_values("hr0-100", 1, [2, 2, 2])
        result = self.master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 0, 5)
        self.assertEqual((0, 2, 2, 2, 0), result)
        
    def testReadOneHoldingRegisters(self):
        """set the values of 3 registers and let's the master reading 5 values"""
        self.slave1.set_values("hr0-100", 6, 4)
        
        result = self.master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 6, 1)
        self.assertEqual((4, ), result)

    def testReadHoldingRegistersOnSlave5(self):
        """set and read the values of some registers on slave 5"""
        self.slave5.set_values("hr0-100", 310, (1, 2, 3))
        
        result = self.master.execute(5, modbus_tk.defines.READ_HOLDING_REGISTERS, 308, 10)
        self.assertEqual((0, 0, 1, 2, 3, 0, 0, 0, 0, 0), result)

    def testReadHoldingRegistersOutOfBlock(self):
        """read out of block and make sure that the correct exception is raised"""
        self.assertRaises(modbus_tk.modbus.ModbusError, self.master.execute, 1, modbus_tk.defines.READ_HOLDING_REGISTERS, 300, 10)
        
        try:
            self.master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 300, 10)
        except modbus_tk.modbus.ModbusError, ex:
            self.assertEqual(ex.get_exception_code(), 2)
            return
        self.assert_(False)

    def testReadTooManyHoldingRegisters(self):
        """check than an error is raised when reading too many holding registers"""
        try:
            self.master.execute(1, modbus_tk.defines.READ_HOLDING_REGISTERS, 1000, 126)
        except modbus_tk.modbus.ModbusError, ex:
            self.assertEqual(ex.get_exception_code(), 3)
            return
        self.assert_(False)
        
    def testReadAnalogInputs(self):
        """Test that response for read analog inputs function is ok"""
        self.slave1.set_values("ai100-50", 120, range(10))
        result = self.master.execute(1, modbus_tk.defines.READ_INPUT_REGISTERS, 120, 10)
        self.assertEqual(tuple(range(10)), result)
        result = self.master.execute(1, modbus_tk.defines.READ_INPUT_REGISTERS, 120, 1)
        self.assertEqual((0,), result)

    def testReadCoils(self):
        """Test that response for read coils function is ok"""
        self.slave1.set_values("c0-100", 0, [0, 1, 1]+[0, 1]*20)
        result = self.master.execute(1, modbus_tk.defines.READ_COILS, 0, 1)
        self.assertEqual((0,), result)
        result = self.master.execute(1, modbus_tk.defines.READ_COILS, 0, 3)
        self.assertEqual((0,1,1), result)
        result = self.master.execute(1, modbus_tk.defines.READ_COILS, 0, 8)
        self.assertEqual(tuple([0, 1, 1]+[0,1]*2+[0]), result)
        result = self.master.execute(1, modbus_tk.defines.READ_COILS, 0, 9)
        self.assertEqual(tuple([0, 1, 1]+[0,1]*3), result)
        result = self.master.execute(1, modbus_tk.defines.READ_COILS, 0, 20)
        self.assertEqual(tuple([0, 1, 1]+[0,1]*8+[0]), result)
        result = self.master.execute(1, modbus_tk.defines.READ_COILS, 0, 21)
        self.assertEqual(tuple([0, 1, 1]+[0,1]*9), result)
        
    def testReadManyCoils(self):
        """Test that response for read many coils function is ok"""
        self.slave1.set_values("c1000-4000", 1000, tuple([0,1]*1000))

        result = self.master.execute(1, modbus_tk.defines.READ_COILS, 1000, 1)
        self.assertEqual(1, len(result))
        self.assertEqual((0,), result)

        result = self.master.execute(1, modbus_tk.defines.READ_COILS, 1000, 8)
        self.assertEqual(8, len(result))
        self.assertEqual(tuple([0,1]*4), result)

        result = self.master.execute(1, modbus_tk.defines.READ_COILS, 1000, 1999)
        self.assertEqual(1999, len(result))
        self.assertEqual(tuple([0,1]*999+[0]), result)
        
        result = self.master.execute(1, modbus_tk.defines.READ_COILS, 1000, 2000)
        self.assertEqual(2000, len(result))
        self.assertEqual(tuple([0,1]*1000), result)

    def testReadCoilsOutOfBlocks(self):
        """Test that an error is raised when reading an invalid address"""
        try:
            self.master.execute(1, modbus_tk.defines.READ_COILS, 500, 12)
        except modbus_tk.modbus.ModbusError, ex:
            self.assertEqual(ex.get_exception_code(), 2)
            return
        self.assert_(False)
        
    def testReadTooManyCoils(self):
        """Test that an error is raised when too many coils are read"""
        try:
            self.master.execute(1, modbus_tk.defines.READ_COILS, 1000, 2001)
        except modbus_tk.modbus.ModbusError, ex:
            self.assertEqual(ex.get_exception_code(), 3)
            return
        self.assert_(False)

    def testReadDiscreteInputs(self):
        """Test that response for read digital inputs function is ok"""
        result = self.master.execute(1, modbus_tk.defines.READ_DISCRETE_INPUTS, 100, 1)
        self.assertEqual((0,), result)
        self.slave1.set_values("di100-1", 100, 1)
        result = self.master.execute(1, modbus_tk.defines.READ_DISCRETE_INPUTS, 100, 1)
        self.assertEqual((1,), result)
        self.slave1.set_values("di200-10", 200, range(8))
        result = self.master.execute(1, modbus_tk.defines.READ_DISCRETE_INPUTS, 200, 1)
        self.assertEqual((0,), result)
        result = self.master.execute(1, modbus_tk.defines.READ_DISCRETE_INPUTS, 200, 3)
        self.assertEqual((0,1,1), result)
        result = self.master.execute(1, modbus_tk.defines.READ_DISCRETE_INPUTS, 200, 8)
        self.assertEqual(tuple([0]+[1]*7), result)
        result = self.master.execute(1, modbus_tk.defines.READ_DISCRETE_INPUTS, 200, 10)
        self.assertEqual(tuple([0]+[1]*7+[0]*2), result)

    def testWriteSingleRegisters(self):
        """Write the values of a single register and check that it is correctly written"""
        result = self.master.execute(1, modbus_tk.defines.WRITE_SINGLE_REGISTER, 0, output_value=54)
        self.assertEqual((0, 54), result)
        self.assertEqual((54,), self.slave1.get_values("hr0-100", 0, 1))
        
        result = self.master.execute(1, modbus_tk.defines.WRITE_SINGLE_REGISTER, 10, output_value=33)
        self.assertEqual((10, 33), result)
        self.assertEqual((33,), self.slave1.get_values("hr0-100", 10, 1))
        
    def testWriteSingleRegistersOutOfBlocks(self):
        """Check taht an error is raised when writing a register out of block"""
        try:
            self.master.execute(1, modbus_tk.defines.WRITE_SINGLE_REGISTER, 500, output_value=11)
        except modbus_tk.modbus.ModbusError, ex:
            self.assertEqual(ex.get_exception_code(), 2)
            return
        self.assert_(False)

    def testWriteSingleCoil(self):
        """Write the values of coils and check that it is correctly written"""
        result = self.master.execute(1, modbus_tk.defines.WRITE_SINGLE_COIL, 0, output_value=1)
        self.assertEqual((0, int("ff00", 16)), result)
        self.assertEqual((1,), self.slave1.get_values("c0-100", 0, 1))
        
        result = self.master.execute(1, modbus_tk.defines.WRITE_SINGLE_COIL, 22, output_value=1)
        self.assertEqual((22, int("ff00", 16)), result)
        self.assertEqual((1,), self.slave1.get_values("c0-100", 22, 1))
        
        result = self.master.execute(1, modbus_tk.defines.WRITE_SINGLE_COIL, 22, output_value=0)
        self.assertEqual((22, 0), result)
        self.assertEqual((0,), self.slave1.get_values("c0-100", 22, 1))
            
    def testWriteSingleCoilOutOfBlocks(self):
        """Check taht an error is raised when writing a coil out of block"""
        try:
            self.master.execute(1, modbus_tk.defines.WRITE_SINGLE_COIL, 500, output_value=1)
        except modbus_tk.modbus.ModbusError, ex:
            self.assertEqual(ex.get_exception_code(), modbus_tk.defines.ILLEGAL_DATA_ADDRESS)
            return
        self.assert_(False)
        
    def testWriteMultipleRegisters(self):
        """Write the values of a multiple registers and check that it is correctly written"""
        result = self.master.execute(1, modbus_tk.defines.WRITE_MULTIPLE_REGISTERS, 0, output_value=(54, ))
        self.assertEqual((0, 1), result)
        self.assertEqual((54,), self.slave1.get_values("hr0-100", 0, 1))
        
        result = self.master.execute(1, modbus_tk.defines.WRITE_MULTIPLE_REGISTERS, 10, output_value=range(20))
        self.assertEqual((10, 20), result)
        self.assertEqual(tuple(range(20)), self.slave1.get_values("hr0-100", 10, 20))
        
        result = self.master.execute(1, modbus_tk.defines.WRITE_MULTIPLE_REGISTERS, 1000, output_value=range(123))
        self.assertEqual((1000, 123), result)
        self.assertEqual(tuple(range(123)), self.slave1.get_values("hr1000-1500", 1000, 123))
        
    def testWriteMultipleRegistersOutOfBlocks(self):
        """Check that an error is raised when writing a register out of block"""
        try:
            self.master.execute(1, modbus_tk.defines.WRITE_MULTIPLE_REGISTERS, 500, output_value=(11, 12))
        except modbus_tk.modbus.ModbusError, ex:
            self.assertEqual(ex.get_exception_code(), modbus_tk.defines.ILLEGAL_DATA_ADDRESS)
            return
        self.assert_(False)

    def testWriteTooManyMultipleRegisters(self):
        """Check that an error is raised when writing too many registers"""
        try:
            self.master.execute(1, modbus_tk.defines.WRITE_MULTIPLE_REGISTERS, 1000, output_value=range(124))
        except modbus_tk.modbus.ModbusError, ex:
            self.assertEqual(ex.get_exception_code(), modbus_tk.defines.ILLEGAL_DATA_VALUE)
            return
        self.assert_(False)
        
    def testWriteMultipleCoils(self):
        """Write the values of a multiple coils and check that it is correctly written"""
        result = self.master.execute(1, modbus_tk.defines.WRITE_MULTIPLE_COILS, 0, output_value=(1, ))
        self.assertEqual((0, 1), result)
        self.assertEqual((1,), self.slave1.get_values("c0-100", 0, 1))
        
        result = self.master.execute(1, modbus_tk.defines.WRITE_MULTIPLE_COILS, 10, output_value=[1]*20)
        self.assertEqual((10, 20), result)
        self.assertEqual(tuple([1]*20), self.slave1.get_values("c0-100", 10, 20))
        
        result = self.master.execute(1, modbus_tk.defines.WRITE_MULTIPLE_COILS, 1000, output_value=[1]*1968)
        self.assertEqual((1000, 1968), result)
        self.assertEqual(tuple([1]*1968), self.slave1.get_values("c1000-4000", 1000, 1968))

    def testWriteMultipleCoilsIssue23(self):
        """Write the values of a multiple coils and check that it is correctly written"""
        slave10 = self.server.add_slave(10)
        slave10.add_block("block", modbus_tk.defines.COILS, 0, 256)
        result = self.master.execute(10, modbus_tk.defines.WRITE_MULTIPLE_COILS, 0, output_value=[0, 0, 1, 1]*8)
        self.assertEqual((0, 32), result)
        self.assertEqual(tuple([0, 0, 1, 1]*8), slave10.get_values("block", 0, 32))

    def testWriteMultipleCoilsOutOfBlocks(self):
        """Check that an error is raised when writing a register out of block"""
        try:
            self.master.execute(1, modbus_tk.defines.WRITE_MULTIPLE_COILS, 500, output_value=(11, 12))
        except modbus_tk.modbus.ModbusError, ex:
            self.assertEqual(ex.get_exception_code(), modbus_tk.defines.ILLEGAL_DATA_ADDRESS)
            return
        self.assert_(False)

    def testWriteTooManyMultipleCoils(self):
        """Check that an error is raised when writing too many registers"""
        try:
            self.master.execute(1, modbus_tk.defines.WRITE_MULTIPLE_COILS, 1000, output_value=[1]*(int("7B0", 16)+1))
        except modbus_tk.modbus.ModbusError, ex:
            self.assertEqual(ex.get_exception_code(), modbus_tk.defines.ILLEGAL_DATA_VALUE)
            return
        self.assert_(False)

    def testBroadcast(self):
        """Check that broadcast queries are handled correctly"""
        self.slave1.add_block("D", modbus_tk.defines.COILS, 5000, 50)
        self.slave1.add_block("A", modbus_tk.defines.HOLDING_REGISTERS, 5000, 50)
        
        self.slave5.add_block("D", modbus_tk.defines.COILS, 5000, 50)
        self.slave5.add_block("A", modbus_tk.defines.HOLDING_REGISTERS, 5000, 50)
        
        self.master.execute(0, modbus_tk.defines.WRITE_MULTIPLE_REGISTERS, 5000, output_value=range(20))
        time.sleep(0.5)
        self.master.execute(0, modbus_tk.defines.WRITE_SINGLE_REGISTER, 5030, output_value=12)
        time.sleep(0.5)
        self.master.execute(0, modbus_tk.defines.WRITE_MULTIPLE_COILS, 5000, output_value=tuple([1]*10))
        time.sleep(0.5)
        self.master.execute(0, modbus_tk.defines.WRITE_SINGLE_COIL, 5030, output_value=1)
        time.sleep(0.5)
        
        self.assertEqual(self.slave1.get_values("A", 5000, 20), tuple(range(20)))
        self.assertEqual(self.slave5.get_values("A", 5000, 20), tuple(range(20)))
        
        self.assertEqual(self.slave1.get_values("A", 5030, 1), (12,))
        self.assertEqual(self.slave5.get_values("A", 5030, 1), (12,))
        
        self.assertEqual(self.slave1.get_values("D", 5000, 10), tuple([1]*10))
        self.assertEqual(self.slave5.get_values("D", 5000, 10), tuple([1]*10))
        
        self.assertEqual(self.slave1.get_values("D", 5030, 1), (1,))
        self.assertEqual(self.slave5.get_values("D", 5030, 1), (1,))
        
    def testBroadcastReading(self):
        """Check that broadcast queries are handled correctly"""
        functions = (modbus_tk.defines.READ_HOLDING_REGISTERS, modbus_tk.defines.READ_COILS,
                    modbus_tk.defines.READ_INPUT_REGISTERS, modbus_tk.defines.READ_DISCRETE_INPUTS)
        for fct in functions:
            self.assertEqual(None, self.master.execute(0, fct, 0, 5))
            
    def testInvalidRequest(self):
        """Check that an error is returned when the request is invalid"""
        query = self.server._make_query()
        requests = ((chr(1), 0x81), (chr(3), 0x83), ("", 0x81))
        for (request_pdu, rc) in requests:
            request = query.build_request(request_pdu, 1)
            response = self.server._databank.handle_request(query, request)
            expected_response = struct.pack(">BB", rc, modbus_tk.defines.SLAVE_DEVICE_FAILURE) 
            self.assertEquals(expected_response, response)
        
        
                       