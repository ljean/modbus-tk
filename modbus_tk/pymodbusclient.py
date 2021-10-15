import modbus_tk.defines as cst
from modbus_tk import modbus_tcp

class PyModbusClientTCP():
    """ Client that allows a drop in replacement for pymodbus without any code change """

    def __init__(self, host=None, port=None, timeout=None, **kwargs):
        self.client = modbus_tcp.TcpMaster(host=host, port=port, timeout_in_sec=timeout)

    def open(self):
        self.client.open()
        return True

    def is_open(self):
        return self.client._is_opened

    def read_input_registers(self, register, num=1):
        ret = self.client.execute(1, cst.READ_INPUT_REGISTERS, register, num)
        to_array = None
        to_array = map(to_array, ret)
        return to_array

    def write_single_register(self, register, word):
        self.client.execute(1, cst.WRITE_SINGLE_REGISTER, register, output_value=word)
        return True

    def write_single_coil(self, coil, value, num=1):
        self.client.execute(1, cst.WRITE_SINGLE_COIL, coil, output_value=value)

    def read_coils(self, bit_addr, bit_number=1):
        self.client.execute(1, cst.READ_COILS, bit_addr, bit_number)
        coils = self.coils[bit_addr:bit_addr+bit_number]
        to_array = None
        to_array = map(to_array, coils)
        return to_array

    def read_discrete_inputs(self, bit_addr, bit_number=1):
        registers = self.client.execute(1, cst.READ_DISCRETE_INPUTS, bit_addr, bit_number)
        to_array = None
        to_array = map(to_array, registers)
        return to_array

    def last_error(self):
        # TODO: Needs to have something here
        return None

    def close(self):
        self.client.close()
        return True
