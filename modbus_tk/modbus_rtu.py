#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Modbus TestKit: Implementation of Modbus protocol in python

 (C)2009 - Luc Jean - luc.jean@gmail.com
 (C)2009 - Apidev - http://www.apidev.fr

 This is distributed under GNU LGPL license, see license.txt

"""

from modbus import *
import logging
import sys
import time
from hooks import call_hooks 

#-------------------------------------------------------------------------------
class RtuQuery(Query):
    """Subclass of a Query. Adds the Modbus RTU specific part of the protocol"""

    def __init__(self):
        """Constructor"""
        Query.__init__(self)
        self._request_address = 0
        self._response_address = 0

    def build_request(self, pdu, slave):
        """Add the Modbus RTU part to the request"""
        self._request_address = slave
        if (self._request_address < 0) or (self._request_address > 255):
            raise InvalidArgumentError, "Invalid address %d" % (self._request_address)
        data = struct.pack(">B", self._request_address) + pdu
        crc = struct.pack(">H", utils.calculate_crc(data))
        return (data + crc)

    def parse_response(self, response):
        """Extract the pdu from the Modbus RTU response"""
        if len(response) < 3:
            raise ModbusInvalidResponseError, "Response length is invalid %d" % (len(response))

        (self._response_address, ) = struct.unpack(">B", response[0])
        if self._request_address != self._response_address:
            raise ModbusInvalidResponseError, "Response address %d is different from request address %d" % \
                (self._response_address, self._request_address)

        (crc, ) = struct.unpack(">H", response[-2:])

        if crc != utils.calculate_crc(response[:-2]):
            raise ModbusInvalidResponseError, "Invalid CRC in response"

        return response[1:-2]

    def parse_request(self, request):
        """Extract the pdu from the Modbus RTU request"""
        if len(request) < 3:
            raise ModbusInvalidRequestError, "Request length is invalid %d" % (len(request))

        (self._request_address, ) = struct.unpack(">B", request[0])

        (crc, ) = struct.unpack(">H", request[-2:])
        if crc != utils.calculate_crc(request[:-2]):
            raise ModbusInvalidRequestError, "Invalid CRC in request"

        return (self._request_address, request[1:-2])

    def build_response(self, response_pdu):
        """Build the response"""
        self._response_address = self._request_address
        data = struct.pack(">B", self._response_address) + response_pdu
        crc = struct.pack(">H", utils.calculate_crc(data))
        return (data + crc)

#-------------------------------------------------------------------------------
class RtuMaster(Master):
    """Subclass of Master. Implements the Modbus RTU MAC layer"""
    
    def __init__(self, serial, interchar_multiplier=1.5):
        """Constructor. Pass the pyserial.Serial object"""
        self._serial = serial
        LOGGER.info("RtuMaster %s is %s" % (self._serial.portstr, "opened" if self._serial.isOpen() else "closed"))
        Master.__init__(self, self._serial.timeout)
        self._t0 = utils.calculate_rtu_inter_char(self._serial.baudrate)
        self._serial.interCharTimeout = interchar_multiplier * self._t0
        self._serial.timeout = interchar_multiplier * self._t0

    def _do_open(self):
        """Open the given serial port if not already opened"""
        if not self._serial.isOpen():
            call_hooks("modbus_rtu.RtuMaster.before_open", (self, ))
            self._serial.open()

    def _do_close(self):
        """Close the serial port if still opened"""
        if self._serial.isOpen():
            self._serial.close()
            call_hooks("modbus_rtu.RtuMaster.after_close", (self, ))

    def set_timeout(self, timeout_in_sec):
        """Change the timeout value"""
        Master.set_timeout(self, timeout_in_sec)
        self._serial.timeout = timeout_in_sec

    def _send(self, request):
        """Send request to the slave"""
        retval = call_hooks("modbus_rtu.RtuMaster.before_send", (self, request))
        if retval <> None:
            request = retval

        self._serial.flushInput()
        self._serial.flushOutput()

        self._serial.write(request)
        time.sleep(3.5 * self._t0)

    def _recv(self, expected_length=-1):
        """Receive the response from the slave"""
        response = ""
        read_bytes = "dummy"
        while read_bytes:
            read_bytes = self._serial.read(1)
            response += read_bytes
            if expected_length>=0 and len(response)>=expected_length:
                #if the expected number of byte is received consider that the response is done
                #improve performance by avoiding end-of-response detection by timeout
                break

        retval = call_hooks("modbus_rtu.RtuMaster.after_recv", (self, response))
        if retval <> None:
            return retval
        return response

    def _make_query(self):
        """Returns an instance of a Query subclass implementing the modbus RTU protocol"""
        return RtuQuery()

#-------------------------------------------------------------------------------
class RtuServer(Server):
    """This class implements a simple and mono-threaded modbus rtu server"""

    def __init__(self, serial, databank=None):
        """Constructor: initializes the server settings"""
        Server.__init__(self, databank if databank else Databank())
        self._serial = serial
        LOGGER.info("RtuServer %s is %s" % (self._serial.portstr, "opened" if self._serial.isOpen() else "closed"))
        self._t0 = utils.calculate_rtu_inter_char(self._serial.baudrate)
        self._serial.interCharTimeout = 1.5 * self._t0
        self._serial.timeout = 10 * self._t0

    def close(self):
        """close the serial communication"""
        if self._serial.isOpen():
            call_hooks("modbus_rtu.RtuServer.before_close", (self, ))
            self._serial.close()
            call_hooks("modbus_rtu.RtuServer.after_close", (self, ))

    def __del__(self):
        """Destructor"""
        self.close()

    def _make_query(self):
        """Returns an instance of a Query subclass implementing the modbus RTU protocol"""
        return RtuQuery()

    def stop(self):
        """Force the server thread to exit"""
        Server.stop(self)

    def _do_init(self):
        """initialize the serial connection"""
        if not self._serial.isOpen():
            call_hooks("modbus_rtu.RtuServer.before_open", (self, ))
            self._serial.open()
            call_hooks("modbus_rtu.RtuServer.after_open", (self, ))

    def _do_exit(self):
        """close the serial connection"""
        self.close()

    def _do_run(self):
        """main function of the server"""
        try:
            #check the status of every socket
            response = ""
            request = ""
            read_bytes = "dummy"
            while read_bytes:
                read_bytes = self._serial.read(128)
                request += read_bytes

            #parse the request
            if request:
                retval = call_hooks("modbus_rtu.RtuServer.after_read", (self, request))
                if retval <> None:
                    request = retval
                response = self._handle(request)

                #send back the response
                retval = call_hooks("modbus_rtu.RtuServer.before_write", (self, response))
                if retval <> None:
                    response = retval

                if response:
                    self._serial.write(response)
                    time.sleep(3.5 * self._t0)

        except Exception, excpt:
            LOGGER.error("Error while handling request, Exception occurred: %s", excpt)
            call_hooks("modbus_rtu.RtuServer.on_error", (self, excpt))
