# Modbus Server Basic Example #

The `TcpServer` class implements a TCP server listening for modbus requests, dispatching it to the corresponding slave and sending back the response.

It provides a set of apis for adding slaves, blocks of data and getting and setting the values

```
import modbus_tk
import modbus_tk.modbus_tcp as modbus_tcp
import threading
import modbus_tk.defines as mdef

logger = modbus_tk.utils.create_logger(name="console", record_format="%(message)s")

server = modbus_tcp.TcpServer()

#creates a slave with id 0
slave1 = server.add_slave(1)
#add 2 blocks of holding registers
slave1.add_block("a", mdef.HOLDING_REGISTERS, 0, 100)#address 0, length 100
slave1.add_block("b", mdef.HOLDING_REGISTERS, 200, 20)#address 200, length 20

#creates another slave with id 5
slave5 = server.add_slave(5)
slave5.add_block("c", mdef.COILS, 0, 100)
slave5.add_block("d", mdef.HOLDING_REGISTERS, 0, 100)

#set the values of registers at address 0
slave1.set_values("a", 0, range(100))        

server.start()

        
```