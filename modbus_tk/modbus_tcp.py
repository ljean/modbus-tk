#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Modbus TestKit: Implementation of Modbus protocol in python

 (C)2009 - Luc Jean - luc.jean@gmail.com
 (C)2009 - Apidev - http://www.apidev.fr

 This is distributed under GNU LGPL license, see license.txt
"""

import socket
import select
import struct

from modbus_tk import LOGGER
from modbus_tk.hooks import call_hooks
from modbus_tk.modbus import (
    Databank, Master, Query, Server,
    InvalidArgumentError, ModbusInvalidResponseError, ModbusInvalidRequestError
)
from modbus_tk.utils import threadsafe_function, flush_socket, to_data


#-------------------------------------------------------------------------------
class ModbusInvalidMbapError(Exception):
    """Exception raised when the modbus TCP header doesn't correspond to what is expected"""

    def __init__(self, value):
        Exception.__init__(self, value)


#-------------------------------------------------------------------------------
class TcpMbap(object):
    """Defines the information added by the Modbus TCP layer"""

    def __init__(self):
        """Constructor: initializes with 0"""
        self.transaction_id = 0
        self.protocol_id = 0
        self.length = 0
        self.unit_id = 0

    def clone(self, mbap):
        """Set the value of each fields from another TcpMbap instance"""
        self.transaction_id = mbap.transaction_id
        self.protocol_id = mbap.protocol_id
        self.length = mbap.length
        self.unit_id = mbap.unit_id

    def _check_ids(self, request_mbap):
        """
        Check that the ids in the request and the response are similar.
        if not returns a string describing the error
        """
        error_str = ""

        if request_mbap.transaction_id != self.transaction_id:
            error_str += "Invalid transaction id: request={0} - response={1}. ".format(
                request_mbap.transaction_id, self.transaction_id)

        if request_mbap.protocol_id != self.protocol_id:
            error_str += "Invalid protocol id: request={0} - response={1}. ".format(
                request_mbap.protocol_id, self.protocol_id
            )

        if request_mbap.unit_id != self.unit_id:
            error_str += "Invalid unit id: request={0} - response={1}. ".format(request_mbap.unit_id, self.unit_id)

        return error_str

    def check_length(self, pdu_length):
        """Check the length field is valid. If not raise an exception"""
        following_bytes_length = pdu_length+1
        if self.length != following_bytes_length:
            return "Response length is {0} while receiving {1} bytes. ".format(self.length, following_bytes_length)
        return ""

    def check_response(self, request_mbap, response_pdu_length):
        """Check that the MBAP of the response is valid. If not raise an exception"""
        error_str = self._check_ids(request_mbap)
        error_str += self.check_length(response_pdu_length)
        if len(error_str) > 0:
            raise ModbusInvalidMbapError(error_str)

    def pack(self):
        """convert the TCP mbap into a string"""
        return struct.pack(">HHHB", self.transaction_id, self.protocol_id, self.length, self.unit_id)

    def unpack(self, value):
        """extract the TCP mbap from a string"""
        (self.transaction_id, self.protocol_id, self.length, self.unit_id) = struct.unpack(">HHHB", value)


class TcpQuery(Query):
    """Subclass of a Query. Adds the Modbus TCP specific part of the protocol"""

    #static variable for giving a unique id to each query
    _last_transaction_id = 0

    def __init__(self):
        """Constructor"""
        super(TcpQuery, self).__init__()
        self._request_mbap = TcpMbap()
        self._response_mbap = TcpMbap()

    @threadsafe_function
    def _get_transaction_id(self):
        """returns an identifier for the query"""
        if TcpQuery._last_transaction_id < 0xffff:
            TcpQuery._last_transaction_id += 1
        else:
            TcpQuery._last_transaction_id = 0
        return TcpQuery._last_transaction_id

    def build_request(self, pdu, slave):
        """Add the Modbus TCP part to the request"""
        if (slave < 0) or (slave > 255):
            raise InvalidArgumentError("{0} Invalid value for slave id".format(slave))
        self._request_mbap.length = len(pdu) + 1
        self._request_mbap.transaction_id = self._get_transaction_id()
        self._request_mbap.unit_id = slave
        mbap = self._request_mbap.pack()
        return mbap + pdu

    def parse_response(self, response):
        """Extract the pdu from the Modbus TCP response"""
        if len(response) > 6:
            mbap, pdu = response[:7], response[7:]
            self._response_mbap.unpack(mbap)
            self._response_mbap.check_response(self._request_mbap, len(pdu))
            return pdu
        else:
            raise ModbusInvalidResponseError("Response length is only {0} bytes. ".format(len(response)))

    def parse_request(self, request):
        """Extract the pdu from a modbus request"""
        if len(request) > 6:
            mbap, pdu = request[:7], request[7:]
            self._request_mbap.unpack(mbap)
            error_str = self._request_mbap.check_length(len(pdu))
            if len(error_str) > 0:
                raise ModbusInvalidMbapError(error_str)
            return self._request_mbap.unit_id, pdu
        else:
            raise ModbusInvalidRequestError("Request length is only {0} bytes. ".format(len(request)))

    def build_response(self, response_pdu):
        """Build the response"""
        self._response_mbap.clone(self._request_mbap)
        self._response_mbap.length = len(response_pdu) + 1
        return self._response_mbap.pack() + response_pdu


class TcpMaster(Master):
    """Subclass of Master. Implements the Modbus TCP MAC layer"""

    def __init__(self, host="127.0.0.1", port=502, timeout_in_sec=5.0):
        """Constructor. Set the communication settings"""
        super(TcpMaster, self).__init__(timeout_in_sec)
        self._host = host
        self._port = port
        self._sock = None

    def _do_open(self):
        """Connect to the Modbus slave"""
        if self._sock:
            self._sock.close()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_timeout(self.get_timeout())
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        call_hooks("modbus_tcp.TcpMaster.before_connect", (self, ))
        self._sock.connect((self._host, self._port))
        call_hooks("modbus_tcp.TcpMaster.after_connect", (self, ))

    def _do_close(self):
        """Close the connection with the Modbus Slave"""
        if self._sock:
            call_hooks("modbus_tcp.TcpMaster.before_close", (self, ))
            self._sock.close()
            call_hooks("modbus_tcp.TcpMaster.after_close", (self, ))
            self._sock = None
            return True

    def set_timeout(self, timeout_in_sec):
        """Change the timeout value"""
        super(TcpMaster, self).set_timeout(timeout_in_sec)
        if self._sock:
            self._sock.setblocking(timeout_in_sec > 0)
            if timeout_in_sec:
                self._sock.settimeout(timeout_in_sec)

    def _send(self, request):
        """Send request to the slave"""
        retval = call_hooks("modbus_tcp.TcpMaster.before_send", (self, request))
        if retval is not None:
            request = retval
        try:
            flush_socket(self._sock, 3)
        except Exception as msg:
            #if we can't flush the socket successfully: a disconnection may happened
            #try to reconnect
            LOGGER.error('Error while flushing the socket: {0}'.format(msg))
            self._do_open()
        self._sock.send(request)

    def _recv(self, expected_length=-1):
        """
        Receive the response from the slave
        Do not take expected_length into account because the length of the response is
        written in the mbap. Used for RTU only
        """
        response = to_data('')
        length = 255
        while len(response) < length:
            rcv_byte = self._sock.recv(1)
            if rcv_byte:
                response += rcv_byte
                if len(response) == 6:
                    to_be_recv_length = struct.unpack(">HHH", response)[2]
                    length = to_be_recv_length + 6
            else:
                break
        retval = call_hooks("modbus_tcp.TcpMaster.after_recv", (self, response))
        if retval is not None:
            return retval
        return response

    def _make_query(self):
        """Returns an instance of a Query subclass implementing the modbus TCP protocol"""
        return TcpQuery()


class TcpServer(Server):
    """
    This class implements a simple and mono-threaded modbus tcp server
    !! Change in 0.5.0: By default the TcpServer is not bound to a specific address
    for example: You must set address to 'loaclhost', if youjust want to accept local connections
    """

    def __init__(self, port=502, address='', timeout_in_sec=1, databank=None, error_on_missing_slave=True):
        """Constructor: initializes the server settings"""
        databank = databank if databank else Databank(error_on_missing_slave=error_on_missing_slave)
        super(TcpServer, self).__init__(databank)
        self._sock = None
        self._sa = (address, port)
        self._timeout_in_sec = timeout_in_sec
        self._sockets = []

    def _make_query(self):
        """Returns an instance of a Query subclass implementing the modbus TCP protocol"""
        return TcpQuery()

    def _get_request_length(self, mbap):
        """Parse the mbap and returns the number of bytes to be read"""
        if len(mbap) < 6:
            raise ModbusInvalidRequestError("The mbap is only %d bytes long", len(mbap))
        length = struct.unpack(">HHH", mbap[:6])[2]
        return length

    def _do_init(self):
        """initialize server"""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self._timeout_in_sec:
            self._sock.settimeout(self._timeout_in_sec)
        self._sock.setblocking(0)
        self._sock.bind(self._sa)
        self._sock.listen(10)
        self._sockets.append(self._sock)

    def _do_exit(self):
        """clean the server tasks"""
        #close the sockets
        for sock in self._sockets:
            try:
                sock.close()
                self._sockets.remove(sock)
            except Exception as msg:
                LOGGER.warning("Error while closing socket, Exception occurred: %s", msg)
        self._sock.close()
        self._sock = None

    def _do_run(self):
        """called in a almost-for-ever loop by the server"""
        # check the status of every socket
        inputready = select.select(self._sockets, [], [], 1.0)[0]

        # handle data on each a socket
        for sock in inputready:
            try:
                if sock == self._sock:
                    # handle the server socket
                    client, address = self._sock.accept()
                    client.setblocking(0)
                    LOGGER.info("%s is connected with socket %d...", str(address), client.fileno())
                    self._sockets.append(client)
                    call_hooks("modbus_tcp.TcpServer.on_connect", (self, client, address))
                else:
                    if len(sock.recv(1, socket.MSG_PEEK)) == 0:
                        # socket is disconnected
                        LOGGER.info("%d is disconnected" % (sock.fileno()))
                        call_hooks("modbus_tcp.TcpServer.on_disconnect", (self, sock))
                        sock.close()
                        self._sockets.remove(sock)
                        break

                    # handle all other sockets
                    sock.settimeout(1.0)
                    request = to_data("")
                    is_ok = True

                    # read the 7 bytes of the mbap
                    while (len(request) < 7) and is_ok:
                        new_byte = sock.recv(1)
                        if len(new_byte) == 0:
                            is_ok = False
                        else:
                            request += new_byte

                    retval = call_hooks("modbus_tcp.TcpServer.after_recv", (self, sock, request))
                    if retval is not None:
                        request = retval

                    if is_ok:
                        # read the rest of the request
                        length = self._get_request_length(request)
                        while (len(request) < (length + 6)) and is_ok:
                            new_byte = sock.recv(1)
                            if len(new_byte) == 0:
                                is_ok = False
                            else:
                                request += new_byte

                    if is_ok:
                        response = ""
                        # parse the request
                        try:
                            response = self._handle(request)
                        except Exception as msg:
                            LOGGER.error("Error while handling a request, Exception occurred: %s", msg)

                        # send back the response
                        if response:
                            try:
                                retval = call_hooks("modbus_tcp.TcpServer.before_send", (self, sock, response))
                                if retval is not None:
                                    response = retval
                                sock.send(response)
                                call_hooks("modbus_tcp.TcpServer.after_send", (self, sock, response))
                            except Exception as msg:
                                is_ok = False
                                LOGGER.error(
                                    "Error while sending on socket %d, Exception occurred: %s", sock.fileno(), msg
                                )
            except Exception as excpt:
                LOGGER.warning("Error while processing data on socket %d: %s", sock.fileno(), excpt)
                call_hooks("modbus_tcp.TcpServer.on_error", (self, sock, excpt))
                sock.close()
                self._sockets.remove(sock)
