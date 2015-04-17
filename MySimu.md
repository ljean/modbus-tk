# Introduction #
This example shows how to make its own modbus simulator with custom command

# Details #

```
#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
    def __init__(self):
        Simulator.__init__(self)
        self.add_command("cv", self.change_value)
        slave = self.server.add_slave(1)
        slave.add_block("foo", HOLDING_REGISTERS, 0, 100)
        
    def change_value(self, args):
        """Custom command : cv """
        address = int(args[1])
        values = []
        for val in args[2:]:
            values.append(int(val))
        
        # a custom rule : check the value is inside a defined range
        if address==0 and values[0]>30:
            try:
                values[1] = 1
            except:
                values.append(1)
        
        slave = self.server.get_slave(1)
        slave.set_values("foo", address, values)
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


```