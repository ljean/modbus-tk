#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Modbus TestKit: Implementation of Modbus protocol in python

 (C)2009 - Luc Jean - luc.jean@gmail.com
 (C)2009 - Apidev - http://www.apidev.fr

 This is distributed under GNU LGPL license, see license.txt
"""

from __future__ import with_statement
import threading

_LOCK = threading.RLock()
_HOOKS = {}


def install_hook(name, fct):
    """
    Install one of the following hook

    modbus_rtu.RtuMaster.before_open((master,))
    modbus_rtu.RtuMaster.after_close((master,)
    modbus_rtu.RtuMaster.before_send((master, request)) returns modified request or None
    modbus_rtu.RtuMaster.after_recv((master, response)) returns modified response or None

    modbus_rtu.RtuServer.before_close((server, ))
    modbus_rtu.RtuServer.after_close((server, ))
    modbus_rtu.RtuServer.before_open((server, ))
    modbus_rtu.RtuServer.after_open(((server, ))
    modbus_rtu.RtuServer.after_read((server, request)) returns modified request or None
    modbus_rtu.RtuServer.before_write((server, response))  returns modified response or None
    modbus_rtu.RtuServer.after_write((server, response))
    modbus_rtu.RtuServer.on_error((server, excpt))

    modbus_tcp.TcpMaster.before_connect((master, ))
    modbus_tcp.TcpMaster.after_connect((master, ))
    modbus_tcp.TcpMaster.before_close((master, ))
    modbus_tcp.TcpMaster.after_close((master, ))
    modbus_tcp.TcpMaster.before_send((master, request))
    modbus_tcp.TcpServer.after_send((master, request))
    modbus_tcp.TcpMaster.after_recv((master, response))


    modbus_tcp.TcpServer.on_connect((server, client, address))
    modbus_tcp.TcpServer.on_disconnect((server, sock))
    modbus_tcp.TcpServer.after_recv((server, sock, request)) returns modified request or None
    modbus_tcp.TcpServer.before_send((server, sock, response)) returns modified response or None
    modbus_tcp.TcpServer.on_error((server, sock, excpt))

    modbus.Master.before_send((master, request)) returns modified request or None
    modbus.Master.after_send((master))
    modbus.Master.after_recv((master, response)) returns modified response or None

    modbus.Slave.handle_request((slave, request_pdu)) returns modified response or None
    modbus.Slave.handle_write_multiple_coils_request((slave, request_pdu))
    modbus.Slave.handle_write_multiple_registers_request((slave, request_pdu)) returns modified response or None
    modbus.Slave.handle_write_single_register_request((slave, request_pdu)) returns modified response or None
    modbus.Slave.handle_write_single_coil_request((slave, request_pdu)) returns modified response or None
    modbus.Slave.handle_read_input_registers_request((slave, request_pdu)) returns modified response or None
    modbus.Slave.handle_read_holding_registers_request((slave, request_pdu)) returns modified response or None
    modbus.Slave.handle_read_discrete_inputs_request((slave, request_pdu)) returns modified response or None
    modbus.Slave.handle_read_coils_request((slave, request_pdu)) returns modified response or None

    modbus.Slave.on_handle_broadcast((slave, response_pdu)) returns modified response or None
    modbus.Slave.on_exception((slave, function_code, excpt))


    modbus.Databank.on_error((db, excpt, request_pdu))

    modbus.ModbusBlock.setitem((self, slice, value))

    modbus.Server.before_handle_request((server, request)) returns modified request or None
    modbus.Server.after_handle_request((server, response)) returns modified response or None
    """
    with _LOCK:
        try:
            _HOOKS[name].append(fct)
        except KeyError:
            _HOOKS[name] = [fct]


def uninstall_hook(name, fct=None):
    """remove the function from the hooks"""
    with _LOCK:
        if fct:
            _HOOKS[name].remove(fct)
        else:
            del _HOOKS[name][:]


def call_hooks(name, args):
    """call the function associated with the hook and pass the given args"""
    with _LOCK:
        try:
            for fct in _HOOKS[name]:
                retval = fct(args)
                if retval is not None:
                    return retval
        except KeyError:
            pass
        return None

