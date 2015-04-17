# Modbus Master basic example #

This is a very basic example explaining how to use the modbus master.

The main (only) thing to do is to call the execute method with the following arguments:

### Read functions ###
Arguments are:
  * slave\_id : identifier of the slave. from 1 to 247.
  * function code : all supported function codes are listed in the defines.py
  * starting address
  * number of items (registers or coils...)

The return value of the function is a tuple containing the n values at the given address

### Write functions ###
Arguments are:
  * slave\_id : identifier of the slave. from 1 to 247. 0 for broadcast message
  * function code : all supported function codes are listed in the defines.py
  * starting address
  * output\_value : an integer or an iterable wontaining the values

The return value is a tuple with the info sent back by the modbus slave : starting address and number of registers written


```
import modbus_tk
import modbus_tk.defines as cst
import modbus_tk.modbus_tcp as modbus_tcp

if __name__ == "__main__":
    try:
        #Connect to the slave
        master = modbus_tcp.TcpMaster()

        print master.execute(1, cst.READ_HOLDING_REGISTERS, 100, 3)
        
        master.execute(1, cst.WRITE_MULTIPLE_REGISTERS, 100, output_value=xrange(12))
        
    except modbus_tk.modbus.ModbusError, e:
        print "Modbus error ", e.get_exception_code()

    except Exception, e2:
        print "Error ", str(e2)

```

# Notes #
  * The connection settings are defined in the constructor of the `TcpMaster` class. By default the values are: `host="127.0.0.1", port=502, timeout_in_sec=5.0`

  * The connection to the server is done automatically on the 1st execute call. It is possible to open and close the connection explicitely by calling the corresponding function.

  * The Modbus error exception is raised when the slave returns an error. It is possible to get the exception code with the get\_exception\_code method