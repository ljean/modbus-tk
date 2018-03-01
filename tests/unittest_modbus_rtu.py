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
import struct
import sys
from modbus_tk.utils import to_data, PY2, PY3

LOGGER = modbus_tk.utils.create_logger()


def crc16_alternative(data):
    crc = 0xFFFF
    for i in data:
        if PY2:
            crc = crc ^ ord(i)
        else:
            crc = crc ^ i
        for j in range(8):
            tmp = crc & 1
            crc = crc >> 1
            if tmp:
                crc = crc ^ 0xA001
    return modbus_tk.utils.swap_bytes(crc)

class TestCrc(unittest.TestCase):
    """Check that the CRC16 calculation"""
    def setUp(self):
        pass        
    
    def tearDown(self):
        pass

    def testSwapBytes(self):
        """Check that swap_bytes is swapping bytes"""
        bytes_list = ("ACDC", "0010", "1000", "1975", "2002", "FAB4", "2BAD")
        for str_val in bytes_list:
            swap_str = str_val[2:4] + str_val[0:2]
            self.assertEqual(modbus_tk.utils.swap_bytes(int(str_val, 16)), int(swap_str, 16))

    def testCrc16ReturnsAlwaysTheSame(self):
        """Check that the CRC16 returns the same result for the same value"""
        test_strings = ("hello world", "a", "12345678910111213141516", "", "modbus-tk", "www.apidev.fr")
        for s in test_strings:
            s = to_data(s)
            self.assertEqual(modbus_tk.utils.calculate_crc(s), modbus_tk.utils.calculate_crc(s))

    def testCrc16ReturnsDifferentForDifferentStrings(self):
        """Check that the CRC16 returns a different value if strings are different"""
        test_strings = ("hello world", "a", "12345678910111213141516", "", "modbus-tk", "www.apidev.fr")
        for s in test_strings:
            s1 = to_data(s)
            s2 = to_data(s + '_')
            self.assertNotEqual(modbus_tk.utils.calculate_crc(s1), modbus_tk.utils.calculate_crc(s2))

    def testCrc16(self):
        """Check that the CRC16 is generated properly"""
        test_strings = ("hello world", "a", "12345678910111213141516", "", "modbus-tk", "www.apidev.fr")
        for s in test_strings:
            s = to_data(s)
            self.assertEqual(crc16_alternative(s), modbus_tk.utils.calculate_crc(s))

    def testCrc16ForAllCharValues(self):
        """Check that the CRC16 is generated properly for all chars"""
        s = to_data('')
        for i in range(256):
            s += struct.pack(">B", i)
            self.assertEqual(crc16_alternative(s), modbus_tk.utils.calculate_crc(s))


class TestRtuQuery(unittest.TestCase):
    """Check that RtuQuery class"""
    def setUp(self):
        pass        
    
    def tearDown(self):
        pass

    def testBuildRequest(self):
        """Test the string returned by building a request"""
        query = modbus_rtu.RtuQuery()
        request = query.build_request(to_data(""), 0)
        expected = struct.pack(">B", 0)
        expected_crc = crc16_alternative(expected)
        expected += struct.pack(">H", expected_crc)
        self.assertEqual(expected, request)
        
    def testBuildRequestWithSlave(self):
        """Test the string returned by building a request with a slave"""
        query = modbus_rtu.RtuQuery()
        for i in range(0, 256):
            request = query.build_request(to_data(""), i)
            expected = struct.pack(">B", i)
            expected_crc = crc16_alternative(expected)
            expected += struct.pack(">H", expected_crc)
            self.assertEqual(expected, request)
    
    def testBuildRequestWithInvalidSlave(self):
        """Test that an error is raised when invalid slave is passed"""
        query = modbus_rtu.RtuQuery()
        for i in ([256, -1, 312, 3541, 65536, 65656]):
            self.assertRaises(modbus_tk.modbus.InvalidArgumentError, query.build_request, "", i)

    def testBuildRequestWithPdu(self):
        """Test the request returned by building a request with a pdu"""
        query = modbus_rtu.RtuQuery()
        for i in range(247):
            for pdu in ["", "a", "a"*127, "abcdefghi"]:
                request = query.build_request(to_data(pdu), i)
                expected = struct.pack(">B"+str(len(pdu))+"s", i, to_data(pdu))
                expected_crc = crc16_alternative(expected)
                expected += struct.pack(">H", expected_crc)
                self.assertEqual(expected, request)
        
    def testParseRespone(self):
        """Test that Modbus Rtu part of the response is understood"""
        query = modbus_rtu.RtuQuery()
        for i in range(247):
            for pdu in ["", "a", "a"*127, "abcdefghi"]:
                request = query.build_request(to_data(pdu), i)
                response = struct.pack(">B"+str(len(pdu))+"s", i, to_data(pdu))
                response_crc = crc16_alternative(response)
                response += struct.pack(">H", response_crc)
                extracted = query.parse_response(response)
                self.assertEqual(extracted, to_data(pdu))
    
    def testParseTooShortRespone(self):
        """Test an error is raised if the response is too short"""
        query = modbus_rtu.RtuQuery()
        for i in range(3):
            self.assertRaises(modbus_tk.modbus.ModbusInvalidResponseError, query.parse_response, "a"*i)
        
    def testParseWrongSlaveResponse(self):
        """Test an error is raised if the slave id is wrong"""
        query = modbus_rtu.RtuQuery()
        pdu = to_data("a")
        request = query.build_request(pdu, 5)
        response = struct.pack(">B" + str(len(pdu)) + "s", 8, pdu)
        response_crc = crc16_alternative(response)
        response += struct.pack(">H", response_crc)
        self.assertRaises(modbus_tk.modbus.ModbusInvalidResponseError, query.parse_response, response)

    def testParseWrongCrcResponse(self):
        """Test an error is raised if wrong transaction id"""
        query = modbus_rtu.RtuQuery()
        pdu = to_data("a")
        request = query.build_request(pdu, 5)
        response = struct.pack(">B" + str(len(pdu)) + "s", 5, pdu)
        response_crc = crc16_alternative(response)+1
        response += struct.pack(">H", response_crc)
        self.assertRaises(modbus_tk.modbus.ModbusInvalidResponseError, query.parse_response, response)
    
    def testParseTooShortRequest(self):
        """Test an error is raised if the request is too short"""
        query = modbus_rtu.RtuQuery()
        for i in range(3):
            self.assertRaises(modbus_tk.modbus.ModbusInvalidRequestError, query.parse_request, to_data("a" * i))

    def testParseRequest(self):
        """Test that Modbus Rtu part of the request is understood"""
        query = modbus_rtu.RtuQuery()
        i = 0
        for pdu in ["", "a", "a"*127, "abcdefghi"]:
            request = query.build_request(to_data(pdu), i)
            (slave, extracted_pdu) = query.parse_request(request)
            self.assertEqual(extracted_pdu, to_data(pdu))
            self.assertEqual(slave, i)
            i += 1

    def testBuildResponse(self):
        """Test that the response of an request is build properly"""
        query = modbus_rtu.RtuQuery()
        i = 0
        for pdu in ["", "a", "a"*127, "abcdefghi"]:
            request = query.build_request(to_data(pdu), i)
            response = query.build_response(to_data(pdu))
            response_pdu = query.parse_response(response)
            self.assertEqual(to_data(pdu), response_pdu)
            i += 1

class TestRtuCom(unittest.TestCase):
    """Check rtu com settinsg are Ok"""
    
    def testCalculateT(self):
        """Test that the interchar is calculated ok"""
        baudrates = (50,75,110,134,150,200,300,600,1200,1800,2400,4800,9600,
                     19200,38400,57600,115200,230400,460800,500000,576000,921600,
                     1000000,1152000,1500000,2000000,2500000,3000000,3500000,4000000)
        ts = [0.22, 0.147, 0.1, 0.082, 0.073, 0.055, 0.037, 0.0183, 0.00917, 0.0061, 0.004583,
              0.00229, 0.001145, 0.000572]
        place = [2]*3 + [3]*5 + [4]*5 + [5]
        missing_count = (len(baudrates)-len(ts))
        ts += [0.0005]*missing_count
        place += [5]*missing_count
        for i in range(len(baudrates)):
            self.assertAlmostEqual(modbus_tk.utils.calculate_rtu_inter_char(baudrates[i]), ts[i], places=place[i])
        
if __name__ == '__main__':
    unittest.main(argv = sys.argv)
