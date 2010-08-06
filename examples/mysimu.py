#!/usr/bin/env python
# -*- coding: utf_8 -*-
"""
 Modbus TestKit: example of a custom simulator

 (C)2009 - Luc Jean - luc.jean@gmail.com
 (C)2009 - Apidev - http://www.apidev.fr

 This is distributed under GNU LGPL license, see license.txt

"""
from modbus_tk.utils import create_logger
from modbus_tk.simulator import Simulator, LOGGER
from modbus_tk.defines import *
        
class MySimulator(Simulator):
    """A custom simulator"""
    def __init__(self):
        """Constructor"""
        Simulator.__init__(self)
        # add a new command: cv will make possible to change a value 
        self.add_command("cv", self.change_value)
        
        # create a slave and block
        slave = self.server.add_slave(1)
        slave.add_block("foo", HOLDING_REGISTERS, 0, 100)
        
    def change_value(self, args):
        """change the value of some registers"""
        address = int(args[1])
        
        #get the list of values and cast it to integers
        values = []
        for val in args[2:]:
            values.append(int(val))
        
        #custom rules: if the value of reg0 is greater than 30 then reg1 is set to 1
        if address==0 and values[0]>30:
            try:
                values[1] = 1
            except:
                values.append(1)
        
        #operates on slave 1 and block foo
        slave = self.server.get_slave(1)
        slave.set_values("foo", address, values)
        
        #get the register values for info
        values = slave.get_values("foo", address, len(values))
        return self._tuple_to_str(values)

if __name__ == "__main__":
    simu = MySimulator()
    
    try:
        LOGGER.info("'quit' for closing the server")
        simu.start()
        
    except Exception, excpt:
        print excpt
            
    finally:
        simu.close()

