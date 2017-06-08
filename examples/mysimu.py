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

from modbus_tk.simulator import Simulator, LOGGER
from modbus_tk.defines import HOLDING_REGISTERS
from modbus_tk.modbus_tcp import TcpServer

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

        # get the register values for info
        values = slave.get_values("foo", address, len(values))
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
