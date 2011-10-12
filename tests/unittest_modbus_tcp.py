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
import sys

LOGGER = modbus_tk.utils.create_logger()

class TestMbap(unittest.TestCase):
    """Test the TcpMbap class"""
    def setUp(self):
        self.mbap1 = modbus_tcp.TcpMbap()
        
        self.mbap1.transaction_id = 1
        self.mbap1.protocol_id = 2
        self.mbap1.length = 3
        self.mbap1.unit_id = 4
        
    
    def tearDown(self):
        pass

    def testClone(self):
        """test the clone function makes a copy of the object"""
        mbap2 = modbus_tcp.TcpMbap()
        
        mbap2.clone(self.mbap1)
        
        self.assertEqual(self.mbap1.transaction_id, mbap2.transaction_id)
        self.assertEqual(self.mbap1.protocol_id, mbap2.protocol_id)
        self.assertEqual(self.mbap1.length, mbap2.length)
        self.assertEqual(self.mbap1.unit_id, mbap2.unit_id)
        
        self.assertNotEqual(self.mbap1, mbap2)
        
    def testCheckIds(self):
        """Test that the check ids pass with correct mbap"""
        mbap2 = modbus_tcp.TcpMbap()
        mbap2.transaction_id = 1
        mbap2.protocol_id = 2
        mbap2.length = 10
        mbap2.unit_id = 4
        
        self.mbap1.check_response(mbap2, 3-1)
        
    def testCheckIdsWrongLength(self):
        """Test that the check ids fails when the length is not Ok"""
        mbap2 = modbus_tcp.TcpMbap()
        mbap2.transaction_id = 1
        mbap2.protocol_id = 2
        mbap2.length = 10
        mbap2.unit_id = 4
        
        self.assertRaises(modbus_tcp.ModbusInvalidMbapError, self.mbap1.check_response, mbap2, 0)    
        
    def testCheckIdsWrongTransactionId(self):
        """Test that the check ids fails when the transaction id is not Ok"""
        mbap2 = modbus_tcp.TcpMbap()
        mbap2.transaction_id = 2
        mbap2.protocol_id = 2
        mbap2.length = 10
        mbap2.unit_id = 4
        
        self.assertRaises(modbus_tcp.ModbusInvalidMbapError, self.mbap1.check_response, mbap2, 2)    
    
    def testCheckIdsWrongProtocolId(self):
        """Test that the check ids fails when the transaction id is not Ok"""
        mbap2 = modbus_tcp.TcpMbap()
        mbap2.transaction_id = 1
        mbap2.protocol_id = 3
        mbap2.length = 10
        mbap2.unit_id = 4
        
        self.assertRaises(modbus_tcp.ModbusInvalidMbapError, self.mbap1.check_response, mbap2, 2)    
    
    def testCheckIdsWrongUnitId(self):
        """Test that the check ids fails when the transaction id is not Ok"""
        mbap2 = modbus_tcp.TcpMbap()
        mbap2.transaction_id = 1
        mbap2.protocol_id = 2
        mbap2.length = 10
        mbap2.unit_id = 5
        
        self.assertRaises(modbus_tcp.ModbusInvalidMbapError, self.mbap1.check_response, mbap2, 2)
        
    def testPack(self):
        """Test that packing a mbap give the expected result"""
        self.assertEqual(self.mbap1.pack(), struct.pack(">HHHB", 1, 2, 3, 4))
    
    def testUnpack(self):
        """Test that unpacking a mbap give the expected result"""
        mbap2 = modbus_tcp.TcpMbap()
        mbap2.unpack(self.mbap1.pack())
        
        self.assertEqual(self.mbap1.transaction_id, mbap2.transaction_id)
        self.assertEqual(self.mbap1.protocol_id, mbap2.protocol_id)
        self.assertEqual(self.mbap1.length, mbap2.length)
        self.assertEqual(self.mbap1.unit_id, mbap2.unit_id)
        
        self.assertNotEqual(self.mbap1, mbap2)
        
class TestTcpQuery(unittest.TestCase):
    def setUp(self):
        pass        
    
    def tearDown(self):
        pass

    def testIncTrIdIsThreadSafe(self):
        """Check that the function in charge of increasing the transaction id is thread safe"""
        def inc_by():
            query = modbus_tcp.TcpQuery()
            for i in xrange(1000):
                query._get_transaction_id()
            
        query = modbus_tcp.TcpQuery()
        tr_id_before = query._get_transaction_id()
        threads = [threading.Thread(target=inc_by) for thread_nr in xrange(20)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(1000*20+1, query._get_transaction_id()-tr_id_before)
        
    def testCheckTrIdRollover(self):
        """Check that the transaction id will rollover when max valuie is reached"""
        query = modbus_tcp.TcpQuery()
        tr_id_before = query._get_transaction_id()
        for a in xrange(int("ffff", 16)):
            query._get_transaction_id()    
        self.assertEqual(query._get_transaction_id(), tr_id_before)
        
    def testIncIdOfRequest(self):
        """Check that the transaction id is increased when building the request"""
        queries = [modbus_tcp.TcpQuery() for i in xrange(100)]
        
        for i in xrange(len(queries)):
            queries[i].build_request("", 0)
        
        for i in xrange(len(queries)-1):
            self.assertEqual(queries[i]._request_mbap.transaction_id+1, queries[i+1]._request_mbap.transaction_id)
        
    def testBuildRequest(self):
        """Test the mbap returned by building a request"""
        query = modbus_tcp.TcpQuery()
        request = query.build_request("", 0)
        self.assertEqual(struct.pack(">HHHB", query._request_mbap.transaction_id, 0, 1, 0), request)
        
    def testBuildRequestWithSlave(self):
        """Test the mbap returned by building a request with a slave"""
        query = modbus_tcp.TcpQuery()
        for i in xrange(0, 255):
            request = query.build_request("", i)
            self.assertEqual(struct.pack(">HHHB", query._request_mbap.transaction_id, 0, 1, i), request)

    def testBuildRequestWithInvalidSlave(self):
        """Test that an error is raised when invalid slave is passed"""
        query = modbus_tcp.TcpQuery()
        for i in [-1, 256, 257, 65536]:
            self.assertRaises(modbus_tk.modbus.InvalidArgumentError, query.build_request, "", i)

    def testBuildRequestWithPdu(self):
        """Test the mbap returned by building a request with a pdu"""
        query = modbus_tcp.TcpQuery()
        for pdu in ["", "a", "a"*127, "abcdefghi"]:
            request = query.build_request(pdu, 0)
            self.assertEqual(struct.pack(">HHHB"+str(len(pdu))+"s", query._request_mbap.transaction_id, 0, len(pdu)+1, 0, pdu), request)
        
    def testParseRespone(self):
        """Test that Modbus TCP part of the response is understood"""
        query = modbus_tcp.TcpQuery()
        for pdu in ["", "a", "a"*127, "abcdefghi"]:
            request = query.build_request("a", 0)
            response = struct.pack(">HHHB"+str(len(pdu))+"s", query._request_mbap.transaction_id, query._request_mbap.protocol_id, len(pdu)+1, query._request_mbap.unit_id, pdu)
            extracted = query.parse_response(response)
            self.assertEqual(extracted, pdu)
    
    def testParseTooShortRespone(self):
        """Test an error is raised if the response is too short"""
        query = modbus_tcp.TcpQuery()
        self.assertRaises(modbus_tk.modbus.ModbusInvalidResponseError, query.parse_response, "")
        self.assertRaises(modbus_tk.modbus.ModbusInvalidResponseError, query.parse_response, "a"*6)
        
    def testParseWrongSlaveResponse(self):
        """Test an error is raised if the slave id is wrong"""
        query = modbus_tcp.TcpQuery()
        pdu = "a"
        request = query.build_request(pdu, 0)
        response = struct.pack(">HHHB"+str(len(pdu))+"s", query._request_mbap.transaction_id, query._request_mbap.protocol_id, len(pdu)+1, query._request_mbap.unit_id+1, pdu)
        self.assertRaises(modbus_tk.modbus_tcp.ModbusInvalidMbapError, query.parse_response, response)

    def testParseWrongTransactionResponse(self):
        """Test an error is raised if wrong transaction id"""
        query = modbus_tcp.TcpQuery()
        pdu = "a"
        request = query.build_request(pdu, 0)
        response = struct.pack(">HHHB"+str(len(pdu))+"s", query._request_mbap.transaction_id+1, query._request_mbap.protocol_id, len(pdu)+1, query._request_mbap.unit_id, pdu)
        self.assertRaises(modbus_tk.modbus_tcp.ModbusInvalidMbapError, query.parse_response, response)
    
    def testParseWrongProtocolIdResponse(self):
        """Test an error is raised if wrong protocol id"""
        query = modbus_tcp.TcpQuery()
        pdu = "a"
        request = query.build_request(pdu, 0)
        response = struct.pack(">HHHB"+str(len(pdu))+"s", query._request_mbap.transaction_id, query._request_mbap.protocol_id+1, len(pdu)+1, query._request_mbap.unit_id, pdu)
        self.assertRaises(modbus_tk.modbus_tcp.ModbusInvalidMbapError, query.parse_response, response)
    
    def testParseWrongLengthResponse(self):
        """Test an error is raised if the length is not ok"""
        query = modbus_tcp.TcpQuery()
        pdu = "a"
        request = query.build_request(pdu, 0)
        response = struct.pack(">HHHB"+str(len(pdu))+"s", query._request_mbap.transaction_id, query._request_mbap.protocol_id+1, len(pdu), query._request_mbap.unit_id, pdu)
        self.assertRaises(modbus_tk.modbus_tcp.ModbusInvalidMbapError, query.parse_response, response)
    
    def testParseWrongLengthResponse(self):
        """Test an error is raised if the length is not ok"""
        query = modbus_tcp.TcpQuery()
        pdu = "a"
        request = query.build_request(pdu, 0)
        response = struct.pack(">HHHB"+str(len(pdu))+"s", query._request_mbap.transaction_id, query._request_mbap.protocol_id+1, len(pdu), query._request_mbap.unit_id, pdu)
        self.assertRaises(modbus_tk.modbus_tcp.ModbusInvalidMbapError, query.parse_response, response)
    
    def testParseTooShortRequest(self):
        """Test an error is raised if the request is too short"""
        query = modbus_tcp.TcpQuery()
        self.assertRaises(modbus_tk.modbus.ModbusInvalidRequestError, query.parse_request, "")
        self.assertRaises(modbus_tk.modbus.ModbusInvalidRequestError, query.parse_request, "a"*6)

    def testParseRequest(self):
        """Test that Modbus TCP part of the request is understood"""
        query = modbus_tcp.TcpQuery()
        i = 0
        for pdu in ["", "a", "a"*127, "abcdefghi"]:
            request = query.build_request(pdu, i)
            (slave, extracted_pdu) = query.parse_request(request)
            self.assertEqual(extracted_pdu, pdu)
            self.assertEqual(slave, i)
            i += 1

    def testParseRequestInvalidLength(self):
        """Test that an error is raised if the length is not valid"""
        query = modbus_tcp.TcpQuery()
        i = 0
        for pdu in ["", "a", "a"*127, "abcdefghi"]:
            request = struct.pack(">HHHB", 0, 0, (len(pdu)+2), 0)
            self.assertRaises(modbus_tk.modbus_tcp.ModbusInvalidMbapError, query.parse_request, request+pdu)

    def testBuildResponse(self):
        """Test that the response of a request is build properly"""
        query = modbus_tcp.TcpQuery()
        i = 0
        for pdu in ["", "a", "a"*127, "abcdefghi"]:
            request = query.build_request(pdu, i)
            response = query.build_response(pdu)
            response_pdu = query.parse_response(response)
            self.assertEqual(pdu, response_pdu)
            i += 1

class TestTcpServer(unittest.TestCase):
    def setUp(self): pass
    def tearDown(self): pass
    
    def testGetRequestLength(self):
        """Test than _get_request_length returns the length field of request mbap"""
        s = modbus_tcp.TcpServer()
        request = struct.pack(">HHHB", 0, 0, 12, 1)
        self.assertEqual(s._get_request_length(request), 12)
        
        request = struct.pack(">HHH", 0, 0, 129)
        self.assertEqual(s._get_request_length(request), 129)
    
    def testGetRequestLengthFailsOnInvalid(self):
        """Test than an error is raised in _get_request_length is the length field of request mbap is not filled"""
        s = modbus_tcp.TcpServer()
        request = struct.pack(">HHB", 0, 0, 1)
        self.assertRaises(modbus_tk.modbus.ModbusInvalidRequestError, s._get_request_length, request)
        self.assertRaises(modbus_tk.modbus.ModbusInvalidRequestError, s._get_request_length, "")
                
if __name__ == '__main__':
    unittest.main(argv = sys.argv)
