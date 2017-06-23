#!/usr/bin/env python
# -*- coding: utf_8 -*-
"""
 Modbus TestKit: example of a custom simulator

 (C)2009 - Luc Jean - luc.jean@gmail.com
 (C)2009 - Apidev - http://www.apidev.fr

 This is distributed under GNU LGPL license, see license.txt

"""
from __future__ import print_function

import sys
import struct

from modbus_tk.simulator import Simulator, LOGGER
from modbus_tk.defines import HOLDING_REGISTERS
from modbus_tk.modbus_tcp import TcpServer
from modbus_tk.utils import PY2

try:
    import serial
    from modbus_tk.modbus_rtu import RtuServer
except ImportError:
    pass


class MySimulator(Simulator):
    """A custom simulator"""

    def __init__(self, *args, **kwargs):
        """Constructor"""
        Simulator.__init__(self, *args, **kwargs)
        # add a new command: cv will make possible to change a value
        self.add_command("cv", self.change_value)
        self.add_command("set_pi", self.set_pi)

        # create a slave and block
        slave = self.server.add_slave(1)
        slave.add_block("foo", HOLDING_REGISTERS, 0, 100)

    def change_value(self, args):
        """change the value of some registers"""
        address = int(args[1])

        # get the list of values and cast it to integers
        values = []
        for val in args[2:]:
            values.append(int(val))

        # custom rules: if the value of reg0 is greater than 30 then reg1 is set to 1
        if address == 0 and values[0] > 30:
            try:
                values[1] = 1
            except IndexError:
                values.append(1)

        # operates on slave 1 and block foo
        slave = self.server.get_slave(1)
        slave.set_values("foo", address, values)
        return self._tuple_to_str(values)

    def set_pi(self, args):
        """change the value of some registers"""
        address = int(args[1])

        # operates on slave 1 and block foo
        slave = self.server.get_slave(1)

        if PY2:
            pi_bytes = [ord(a_byte) for a_byte in struct.pack("f", 3.14)]
        else:
            pi_bytes = [int(a_byte) for a_byte in struct.pack("f", 3.14)]

        pi_register1 = pi_bytes[0] * 256 + pi_bytes[1]
        pi_register2 = pi_bytes[2] * 256 + pi_bytes[3]

        slave.set_values("foo", address, [pi_register1, pi_register2])

        values = slave.get_values("foo", address, 2)
        return self._tuple_to_str(values)


def main():
    """main"""

    #Connect to the slave
    if 'rtu' in sys.argv:
        server = RtuServer(serial.Serial(port=sys.argv[-1]))
    else:
        server = TcpServer(error_on_missing_slave=True)

    simu = MySimulator(server)

    try:
        LOGGER.info("'quit' for closing the server")
        simu.start()

    except Exception as excpt:
        print(excpt)

    finally:
        simu.close()


if __name__ == "__main__":
    help_text = """
    Usage:
    python mysimu.py  -> Run in TCP mode
    python mysimu.py rtu /dev/ptyp5 -> Run in RTU mode and open the port given as last argument
    """
    if '-h' in sys.argv:
        print(help_text)
    else:
        main()
