#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Modbus TestKit: Implementation of Modbus protocol in python

 (C)2009 - Luc Jean - luc.jean@gmail.com
 (C)2009 - Apidev - http://www.apidev.fr

 This is distributed under GNU LGPL license, see license.txt

"""

import struct
import time

from modbus_tk import LOGGER
from modbus_tk.modbus import (
    Databank, Query, Master, Server,
    InvalidArgumentError, ModbusInvalidResponseError, ModbusInvalidRequestError
)
from modbus_tk.hooks import call_hooks
from modbus_tk import utils


class RtuQuery(Query):
    """Subclass of a Query. Adds the Modbus RTU specific part of the protocol"""

    def __init__(self):
        """Constructor"""
        super(RtuQuery, self).__init__()
        self._request_address = 0
        self._response_address = 0

    def build_request(self, pdu, slave):
        """Add the Modbus RTU part to the request"""
        self._request_address = slave
        if (self._request_address < 0) or (self._request_address > 255):
            raise InvalidArgumentError("Invalid address {0}".format(self._request_address))
        data = struct.pack(">B", self._request_address) + pdu
        crc = struct.pack(">H", utils.calculate_crc(data))
        return data + crc

    def parse_response(self, response):
        """Extract the pdu from the Modbus RTU response"""
        if len(response) < 3:
            raise ModbusInvalidResponseError("Response length is invalid {0}".format(len(response)))

        (self._response_address, ) = struct.unpack(">B", response[0:1])

        if self._request_address != self._response_address:
            raise ModbusInvalidResponseError(
                "Response address {0} is different from request address {1}".format(
                    self._response_address, self._request_address
                )
            )

        (crc, ) = struct.unpack(">H", response[-2:])

        if crc != utils.calculate_crc(response[:-2]):
            raise ModbusInvalidResponseError("Invalid CRC in response")

        return response[1:-2]

    def parse_request(self, request):
        """Extract the pdu from the Modbus RTU request"""
        if len(request) < 3:
            raise ModbusInvalidRequestError("Request length is invalid {0}".format(len(request)))

        (self._request_address, ) = struct.unpack(">B", request[0:1])

        (crc, ) = struct.unpack(">H", request[-2:])
        if crc != utils.calculate_crc(request[:-2]):
            raise ModbusInvalidRequestError("Invalid CRC in request")

        return self._request_address, request[1:-2]

    def build_response(self, response_pdu):
        """Build the response"""
        self._response_address = self._request_address
        data = struct.pack(">B", self._response_address) + response_pdu
        crc = struct.pack(">H", utils.calculate_crc(data))
        return data + crc


class RtuMaster(Master):
    """Subclass of Master. Implements the Modbus RTU MAC layer"""

    def __init__(self, serial, interchar_multiplier=1.5, interframe_multiplier=3.5, t0=None):
        """Constructor. Pass the pyserial.Serial object"""
        self._serial = serial
        LOGGER.info("RtuMaster %s is %s", self._serial.name, "opened" if self._serial.is_open else "closed")
        super(RtuMaster, self).__init__(self._serial.timeout)

        if t0:
            self._t0 = t0
        else:
            self._t0 = utils.calculate_rtu_inter_char(self._serial.baudrate)
        self._serial.inter_byte_timeout = interchar_multiplier * self._t0
        self.set_timeout(interframe_multiplier * self._t0)

    def _do_open(self):
        """Open the given serial port if not already opened"""
        if not self._serial.is_open:
            call_hooks("modbus_rtu.RtuMaster.before_open", (self, ))
            self._serial.open()

    def _do_close(self):
        """Close the serial port if still opened"""
        if self._serial.is_open:
            self._serial.close()
            call_hooks("modbus_rtu.RtuMaster.after_close", (self, ))
            return True

    def set_timeout(self, timeout_in_sec):
        """Change the timeout value"""
        Master.set_timeout(self, timeout_in_sec)
        self._serial.timeout = timeout_in_sec

    def _send(self, request):
        """Send request to the slave"""
        retval = call_hooks("modbus_rtu.RtuMaster.before_send", (self, request))
        if retval is not None:
            request = retval

        self._serial.reset_input_buffer()
        self._serial.reset_output_buffer()

        self._serial.write(request)

    def _recv(self, expected_length=-1):
        """Receive the response from the slave"""
        response = utils.to_data("")
        while True:
            read_bytes = self._serial.read(expected_length if expected_length > 0 else 1)
            if not read_bytes:
                break
            response += read_bytes
            if expected_length >= 0 and len(response) >= expected_length:
                #if the expected number of byte is received consider that the response is done
                #improve performance by avoiding end-of-response detection by timeout
                break

        retval = call_hooks("modbus_rtu.RtuMaster.after_recv", (self, response))
        if retval is not None:
            return retval
        return response

    def _make_query(self):
        """Returns an instance of a Query subclass implementing the modbus RTU protocol"""
        return RtuQuery()


class RtuServer(Server):
    """This class implements a simple and mono-threaded modbus rtu server"""
    _timeout = 0

    def __init__(self, serial, databank=None, error_on_missing_slave=True, **kwargs):
        """
        Constructor: initializes the server settings
        serial: a pyserial object
        databank: the data to access
        interframe_multiplier: 3.5 by default
        interchar_multiplier: 1.5 by default
        """
        interframe_multiplier = kwargs.pop('interframe_multiplier', 3.5)
        interchar_multiplier = kwargs.pop('interchar_multiplier', 1.5)

        databank = databank if databank else Databank(error_on_missing_slave=error_on_missing_slave)
        super(RtuServer, self).__init__(databank)

        self._serial = serial
        LOGGER.info("RtuServer %s is %s", self._serial.name, "opened" if self._serial.is_open else "closed")

        self._t0 = utils.calculate_rtu_inter_char(self._serial.baudrate)
        self._serial.inter_byte_timeout = interchar_multiplier * self._t0
        self.set_timeout(interframe_multiplier * self._t0)

    def close(self):
        """close the serial communication"""
        if self._serial.is_open:
            call_hooks("modbus_rtu.RtuServer.before_close", (self, ))
            self._serial.close()
            call_hooks("modbus_rtu.RtuServer.after_close", (self, ))

    def set_timeout(self, timeout):
        self._timeout = timeout
        self._serial.timeout = timeout

    def get_timeout(self):
        return self._timeout

    def __del__(self):
        """Destructor"""
        self.close()

    def _make_query(self):
        """Returns an instance of a Query subclass implementing the modbus RTU protocol"""
        return RtuQuery()

    def stop(self):
        """Force the server thread to exit"""
        super(RtuServer, self).stop()

    def _do_init(self):
        """initialize the serial connection"""
        if not self._serial.is_open:
            call_hooks("modbus_rtu.RtuServer.before_open", (self, ))
            self._serial.open()
            call_hooks("modbus_rtu.RtuServer.after_open", (self, ))

    def _do_exit(self):
        """close the serial connection"""
        self.close()

    def _do_run(self):
        """main function of the server"""
        try:
            # check the status of every socket
            request = utils.to_data('')
            while True:
                try:
                    read_bytes = self._serial.read(128)
                    if not read_bytes:
                        break
                except Exception as e:
                    self._serial.close()
                    self._serial.open()
                    break
                request += read_bytes

            # parse the request
            if request:

                retval = call_hooks("modbus_rtu.RtuServer.after_read", (self, request))
                if retval is not None:
                    request = retval

                response = self._handle(request)

                # send back the response
                retval = call_hooks("modbus_rtu.RtuServer.before_write", (self, response))
                if retval is not None:
                    response = retval

                if response:
                    self._serial.write(response)
                    time.sleep(self.get_timeout())

                call_hooks("modbus_rtu.RtuServer.after_write", (self, response))

        except Exception as excpt:
            LOGGER.error("Error while handling request, Exception occurred: %s", excpt)
            call_hooks("modbus_rtu.RtuServer.on_error", (self, excpt))
