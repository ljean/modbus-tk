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
        self.use_sw_timeout = False
        LOGGER.debug("RtuMaster %s is %s", self._serial.name, "opened" if self._serial.is_open else "closed")
        super(RtuMaster, self).__init__(self._serial.timeout)

        if t0:
            self._t0 = t0
        else:
            self._t0 = utils.calculate_rtu_inter_char(self._serial.baudrate)
        self._serial.inter_byte_timeout = interchar_multiplier * self._t0
        self.set_timeout(interframe_multiplier * self._t0)

        # For some RS-485 adapters, the sent data(echo data) appears before modbus response.
        # So read  echo data and discard it.  By yush0602@gmail.com
        self.handle_local_echo = False

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

    def set_timeout(self, timeout_in_sec, use_sw_timeout=False):
        """Change the timeout value"""
        Master.set_timeout(self, timeout_in_sec)
        self._serial.timeout = timeout_in_sec
        # Use software based timeout in case the timeout functionality provided by the serial port is unreliable
        self.use_sw_timeout = use_sw_timeout

    def _send(self, request):
        """Send request to the slave"""
        retval = call_hooks("modbus_rtu.RtuMaster.before_send", (self, request))
        if retval is not None:
            request = retval

        self._serial.reset_input_buffer()
        self._serial.reset_output_buffer()

        self._serial.write(request)
        self._serial.flush()

        # Read the echo data, and discard it
        if self.handle_local_echo:
            self._serial.read(len(request))

    def _recv(self, expected_length=-1):
        """Receive the response from the slave"""
        response = utils.to_data("")
        start_time = time.time() if self.use_sw_timeout else 0
        readed_len = 0
        while True:
            if self._serial.timeout:
                # serial.read() says if a timeout is set it may return less characters as requested
                # we should update expected_length by readed_len
                read_bytes = self._serial.read(expected_length - readed_len if (expected_length - readed_len) > 0 else 1)
            else:
                read_bytes = self._serial.read(expected_length if expected_length > 0 else 1)
            if self.use_sw_timeout:
                read_duration = time.time() - start_time
            else:
                read_duration = 0
            if (not read_bytes) or (read_duration > self._serial.timeout):
                break
            response += read_bytes
            if expected_length >= 0 and len(response) >= expected_length:
                # if the expected number of byte is received consider that the response is done
                # improve performance by avoiding end-of-response detection by timeout
                break
            readed_len += len(read_bytes)

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
        LOGGER.debug("RtuServer %s is %s", self._serial.name, "opened" if self._serial.is_open else "closed")

        self._t0 = utils.calculate_rtu_inter_char(self._serial.baudrate)
        self._serial.inter_byte_timeout = interchar_multiplier * self._t0
        self.set_timeout(interframe_multiplier * self._t0)

        self._block_on_first_byte = False

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

    def start(self):
        """Allow the server thread to block on first byte"""
        self._block_on_first_byte = True
        super(RtuServer, self).start()

    def stop(self):
        """Force the server thread to exit"""
        # Prevent blocking on first byte in server thread.
        # Without the _block_on_first_byte following problem could happen:
        #   1. Current blocking read(1) is cancelled
        #   2. Server thread resumes and start next read(1)
        #   3. RtuServer clears go event and waits for thread to finish
        #   4. Server thread finishes only when a byte is received
        # Thanks to _block_on_first_byte, if server thread does start new read
        # it will timeout as it won't be blocking.
        self._block_on_first_byte = False
        if self._serial.is_open:
            # cancel any pending read from server thread, it most likely is
            # blocking read(1) call
            self._serial.cancel_read()
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
            if self._block_on_first_byte:
                # do a blocking read for first byte
                self._serial.timeout = None
                try:
                    read_bytes = self._serial.read(1)
                    request += read_bytes
                except Exception as e:
                    self._serial.close()
                    self._serial.open()
                self._serial.timeout = self._timeout

            # Read rest of the request
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
                    if self._serial.in_waiting > 0:
                        # Most likely master timed out on this request and started a new one
                        # for which we already received atleast 1 byte
                        LOGGER.warning("Not sending response because there is new request pending")
                    else:
                        self._serial.write(response)
                        self._serial.flush()
                        time.sleep(self.get_timeout())

                call_hooks("modbus_rtu.RtuServer.after_write", (self, response))

        except Exception as excpt:
            LOGGER.error("Error while handling request, Exception occurred: %s", excpt)
            call_hooks("modbus_rtu.RtuServer.on_error", (self, excpt))
