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
import serial
import sys

LOGGER = modbus_tk.utils.create_logger()

def crc16_alternative(data):
    table =("0000", "C0C1", "C181", "0140", "C301", "03C0", "0280", "C241",
            "C601", "06C0", "0780", "C741", "0500", "C5C1", "C481", "0440",
            "CC01", "0CC0", "0D80", "CD41", "0F00", "CFC1", "CE81", "0E40",
            "0A00", "CAC1", "CB81", "0B40", "C901", "09C0", "0880", "C841",
            "D801", "18C0", "1980", "D941", "1B00", "DBC1", "DA81", "1A40",
            "1E00", "DEC1", "DF81", "1F40", "DD01", "1DC0", "1C80", "DC41",
            "1400", "D4C1", "D581", "1540", "D701", "17C0", "1680", "D641",
            "D201", "12C0", "1380", "D341", "1100", "D1C1", "D081", "1040",
            "F001", "30C0", "3180", "F141", "3300", "F3C1", "F281", "3240",
            "3600", "F6C1", "F781", "3740", "F501", "35C0", "3480", "F441",
            "3C00", "FCC1", "FD81", "3D40", "FF01", "3FC0", "3E80", "FE41",
            "FA01", "3AC0", "3B80", "FB41", "3900", "F9C1", "F881", "3840",
            "2800", "E8C1", "E981", "2940", "EB01", "2BC0", "2A80", "EA41",
            "EE01", "2EC0", "2F80", "EF41", "2D00", "EDC1", "EC81", "2C40",
            "E401", "24C0", "2580", "E541", "2700", "E7C1", "E681", "2640",
            "2200", "E2C1", "E381", "2340", "E101", "21C0", "2080", "E041",
            "A001", "60C0", "6180", "A141", "6300", "A3C1", "A281", "6240",
            "6600", "A6C1", "A781", "6740", "A501", "65C0", "6480", "A441",
            "6C00", "ACC1", "AD81", "6D40", "AF01", "6FC0", "6E80", "AE41",
            "AA01", "6AC0", "6B80", "AB41", "6900", "A9C1", "A881", "6840",
            "7800", "B8C1", "B981", "7940", "BB01", "7BC0", "7A80", "BA41",
            "BE01", "7EC0", "7F80", "BF41", "7D00", "BDC1", "BC81", "7C40",
            "B401", "74C0", "7580", "B541", "7700", "B7C1", "B681", "7640",
            "7200", "B2C1", "B381", "7340", "B101", "71C0", "7080", "B041",
            "5000", "90C1", "9181", "5140", "9301", "53C0", "5280", "9241",
            "9601", "56C0", "5780", "9741", "5500", "95C1", "9481", "5440",
            "9C01", "5CC0", "5D80", "9D41", "5F00", "9FC1", "9E81", "5E40",
            "5A00", "9AC1", "9B81", "5B40", "9901", "59C0", "5880", "9841",
            "8801", "48C0", "4980", "8941", "4B00", "8BC1", "8A81", "4A40",
            "4E00", "8EC1", "8F81", "4F40", "8D01", "4DC0", "4C80", "8C41",
            "4400", "84C1", "8581", "4540", "8701", "47C0", "4680", "8641",
            "8201", "42C0", "4380", "8341", "4100", "81C1", "8081", "4040" )
    w = int("ffff", 16)
    for c in data:
        i = (ord(c) ^ w) & 255
        w = (w>>8) & int("ffff",16)
        w = w ^ int(table[i],16)
    return modbus_tk.utils.swap_bytes(w)

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
            swap_str = str_val[2:4]+str_val[0:2]
            self.assertEqual(modbus_tk.utils.swap_bytes(int(str_val, 16)), int(swap_str, 16))

    def testCrc16ReturnsAlwaysTheSame(self):
        """Check that the CRC16 returns the same result for the same value"""
        test_strings = ("hello world", "a", "12345678910111213141516", "", "modbus-tk", "www.apidev.fr")
        for s in test_strings:
            self.assertEqual(modbus_tk.utils.calculate_crc(s), modbus_tk.utils.calculate_crc(s))

    def testCrc16ReturnsDifferentForDifferentStrings(self):
        """Check that the CRC16 returns a different value if strings are different"""
        test_strings = ("hello world", "a", "12345678910111213141516", "", "modbus-tk", "www.apidev.fr")
        for s in test_strings:
            self.assertNotEqual(modbus_tk.utils.calculate_crc(s), modbus_tk.utils.calculate_crc(s+"_"))

    def testCrc16(self):
        """Check that the CRC16 is generated properly"""
        test_strings = ("hello world", "a", "12345678910111213141516", "", "modbus-tk", "www.apidev.fr")
        for s in test_strings:
            self.assertEqual(crc16_alternative(s), modbus_tk.utils.calculate_crc(s))

    def testCrc16ForAllCharValues(self):
        """Check that the CRC16 is generated properly for all chars"""
        s = ""
        for i in xrange(256):
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
        request = query.build_request("", 0)
        expected = struct.pack(">B", 0)
        expected_crc = crc16_alternative(expected)
        expected += struct.pack(">H", expected_crc)
        self.assertEqual(expected, request)
        
    def testBuildRequestWithSlave(self):
        """Test the string returned by building a request with a slave"""
        query = modbus_rtu.RtuQuery()
        for i in xrange(0, 256):
            request = query.build_request("", i)
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
        for i in xrange(247):
            for pdu in ["", "a", "a"*127, "abcdefghi"]:
                request = query.build_request(pdu, i)
                expected = struct.pack(">B"+str(len(pdu))+"s", i, pdu)
                expected_crc = crc16_alternative(expected)
                expected += struct.pack(">H", expected_crc)
                self.assertEqual(expected, request)
        
    def testParseRespone(self):
        """Test that Modbus Rtu part of the response is understood"""
        query = modbus_rtu.RtuQuery()
        for i in xrange(247):
            for pdu in ["", "a", "a"*127, "abcdefghi"]:
                request = query.build_request("a", i)
                response = struct.pack(">B"+str(len(pdu))+"s", i, pdu)
                response_crc = crc16_alternative(response)
                response += struct.pack(">H", response_crc)
                extracted = query.parse_response(response)
                self.assertEqual(extracted, pdu)
    
    def testParseTooShortRespone(self):
        """Test an error is raised if the response is too short"""
        query = modbus_rtu.RtuQuery()
        for i in xrange(3):
            self.assertRaises(modbus_tk.modbus.ModbusInvalidResponseError, query.parse_response, "a"*i)
        
    def testParseWrongSlaveResponse(self):
        """Test an error is raised if the slave id is wrong"""
        query = modbus_rtu.RtuQuery()
        pdu = "a"
        request = query.build_request(pdu, 5)
        response = struct.pack(">B"+str(len(pdu))+"s", 8, pdu)
        response_crc = crc16_alternative(response)
        response += struct.pack(">H", response_crc)
        self.assertRaises(modbus_tk.modbus.ModbusInvalidResponseError, query.parse_response, response)

    def testParseWrongCrcResponse(self):
        """Test an error is raised if wrong transaction id"""
        query = modbus_rtu.RtuQuery()
        pdu = "a"
        request = query.build_request(pdu, 5)
        response = struct.pack(">B"+str(len(pdu))+"s", 5, pdu)
        response_crc = crc16_alternative(response)+1
        response += struct.pack(">H", response_crc)
        self.assertRaises(modbus_tk.modbus.ModbusInvalidResponseError, query.parse_response, response)
    
    def testParseTooShortRequest(self):
        """Test an error is raised if the request is too short"""
        query = modbus_rtu.RtuQuery()
        for i in xrange(3):
            self.assertRaises(modbus_tk.modbus.ModbusInvalidRequestError, query.parse_request, "a"*i)

    def testParseRequest(self):
        """Test that Modbus Rtu part of the request is understood"""
        query = modbus_rtu.RtuQuery()
        i = 0
        for pdu in ["", "a", "a"*127, "abcdefghi"]:
            request = query.build_request(pdu, i)
            (slave, extracted_pdu) = query.parse_request(request)
            self.assertEqual(extracted_pdu, pdu)
            self.assertEqual(slave, i)
            i += 1

    def testBuildResponse(self):
        """Test that the response of an request is build properly"""
        query = modbus_rtu.RtuQuery()
        i = 0
        for pdu in ["", "a", "a"*127, "abcdefghi"]:
            request = query.build_request(pdu, i)
            response = query.build_response(pdu)
            response_pdu = query.parse_response(response)
            self.assertEqual(pdu, response_pdu)
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
        for i in xrange(len(baudrates)):
            self.assertAlmostEqual(modbus_tk.utils.calculate_rtu_inter_char(baudrates[i]), ts[i], places=place[i])
        
if __name__ == '__main__':
    unittest.main(argv = sys.argv)
