#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Modbus TestKit: Implementation of Modbus protocol in python

 (C)2009 - Luc Jean - luc.jean@gmail.com
 (C)2009 - Apidev - http://www.apidev.fr

 This is distributed under GNU LGPL license, see license.txt
"""
from __future__ import print_function

import socket
import modbus_tk.defines


class SimulatorRpcClient(object):
    """Make possible to send command to the modbus_tk.Simulator thanks to Remote Process Call"""

    def __init__(self, host="127.0.0.1", port=2711, timeout=0.5):
        """Constructor"""
        self.host = host
        self.port = port
        self.timeout = timeout

    def _rpc_call(self, query):
        """send a rpc call and return the result"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.host, self.port))
        sock.send(query)
        response = sock.recv(1024)
        sock.close()
        return self._response_to_values(response.strip("\r\n"), query.split(" ")[0])

    def _response_to_values(self, response, command):
        """extract the return value from the response"""
        prefix = command + " done: "
        if response.find(prefix) == 0:
            return response[len(prefix):]
        else:
            raise Exception(response)

    def add_slave(self, slave_id):
        """add a new slave with the given id"""
        query = "add_slave %d" % (slave_id)
        return self._rpc_call(query)

    def remove_slave(self, slave_id):
        """add a new slave with the given id"""
        query = "remove_slave %d" % (slave_id)
        return self._rpc_call(query)

    def remove_all_slaves(self):
        """add a new slave with the given id"""
        query = "remove_all_slaves"
        self._rpc_call(query)

    def has_slave(self, slave_id):
        """add a new slave with the given id"""
        query = "has_slave %d" % (slave_id)
        if "1" == self._rpc_call(query):
            return True
        return False

    def add_block(self, slave_id, block_name, block_type, starting_address, length):
        """add a new modbus block into the slave"""
        query = "add_block %d %s %d %d %d" % (slave_id, block_name, block_type, starting_address, length)
        return self._rpc_call(query)

    def remove_block(self, slave_id, block_name):
        """remove the modbus block with the given name and slave"""
        query = "remove_block %d %s" % (slave_id, block_name)
        self._rpc_call(query)

    def remove_all_blocks(self, slave_id):
        """remove the modbus block with the given name and slave"""
        query = "remove_all_blocks %d" % (slave_id)
        self._rpc_call(query)

    def set_values(self, slave_id, block_name, address, values):
        """set the values of registers"""
        query = "set_values %d %s %d" % (slave_id, block_name, address)
        for val in values:
            query += (" " + str(val))
        return self._rpc_call(query)

    def get_values(self, slave_id, block_name, address, length):
        """get the values of some registers"""
        query = "get_values %d %s %d %d" % (slave_id, block_name, address, length)
        ret_values = self._rpc_call(query)
        return tuple([int(val) for val in ret_values.split(' ')])

    def install_hook(self, hook_name, fct_name):
        """add a hook"""
        query = "install_hook %s %s" % (hook_name, fct_name)
        self._rpc_call(query)

    def uninstall_hook(self, hook_name, fct_name=""):
        """remove a hook"""
        query = "uninstall_hook %s %s" % (hook_name, fct_name)
        self._rpc_call(query)


if __name__ == "__main__":
    modbus_simu = SimulatorRpcClient()
    modbus_simu.remove_all_slaves()
    print(modbus_simu.add_slave(12))
    print(modbus_simu.add_block(12, "toto", modbus_tk.defines.COILS, 0, 100))
    print(modbus_simu.set_values(12, "toto", 0, [5, 8, 7, 6, 41]))
    print(modbus_simu.get_values(12, "toto", 0, 5))
    print(modbus_simu.set_values(12, "toto", 2, [9]))
    print(modbus_simu.get_values(12, "toto", 0, 5))
    print(modbus_simu.has_slave(12))
    print(modbus_simu.add_block(12, "titi", modbus_tk.defines.COILS, 100, 100))
    print(modbus_simu.remove_block(12, "titi"))
    print(modbus_simu.add_slave(25))
    print(modbus_simu.has_slave(25))
    print(modbus_simu.add_slave(28))
    modbus_simu.remove_slave(25)
    print(modbus_simu.has_slave(25))
    print(modbus_simu.has_slave(28))
    modbus_simu.remove_all_blocks(12)
    modbus_simu.remove_all_slaves()
    print(modbus_simu.has_slave(28))
    print(modbus_simu.has_slave(12))
    modbus_simu.install_hook("modbus.Server.before_handle_request", "print_me")
