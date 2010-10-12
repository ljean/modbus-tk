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

_lock = threading.RLock()
_hooks = {}
                     
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
    modbus_rtu.RtuServer.on_error((server, excpt))
    
    modbus_tcp.TcpMaster.before_connect((master, ))  
    modbus_tcp.TcpMaster.after_connect((master, ))      
    modbus_tcp.TcpMaster.before_close((master, ))  
    modbus_tcp.TcpMaster.after_close((master, ))  
    modbus_tcp.TcpMaster.before_send((master, request))  
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
    modbus.Slave.on_handle_broadcast((slave, response_pdu)) returns modified response or None  
    modbus.Slave.on_exception((slave, function_code, excpt))  
    
    modbus.Databank.on_error((db, excpt, request_pdu))
    
    modbus.ModbusBlock.setitem((self, slice, value))  
    
    modbus.Server.before_handle_request((server, request)) returns modified request or None
    modbus.Server.after_handle_request((server, response)) returns modified response or None
    """ 
    with _lock:
        try:
            _hooks[name].append(fct)
        except KeyError:
            _hooks[name] = [fct]

def uninstall_hook(name, fct=None):
    """remove the function from the hooks"""
    with _lock:
        if fct:
            _hooks[name].remove(fct)
        else:
            del _hooks[name][:]
    
def call_hooks(name, args):
    """call the function associated with the hook and pass the given args"""
    with _lock:
        try:
            for fct in _hooks[name]:
                retval = fct(args)
                if retval <> None:
                    return retval
        except KeyError:
            pass
        return None

