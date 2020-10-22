#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Modbus TestKit: Implementation of Modbus protocol in python

 (C)2009 - Luc Jean - luc.jean@gmail.com
 (C)2009 - Apidev - http://www.apidev.fr

 This is distributed under GNU LGPL license, see license.txt

 History:
 2010/01/08 - RD: Update master.execute(..) to calculate lengths automatically based on requested command
"""

from __future__ import with_statement

import struct
import threading

from modbus_tk import LOGGER
from modbus_tk import defines
from modbus_tk.exceptions import(
    ModbusError, ModbusFunctionNotSupportedError, DuplicatedKeyError, MissingKeyError, InvalidModbusBlockError,
    InvalidArgumentError, OverlapModbusBlockError, OutOfModbusBlockError, ModbusInvalidResponseError,
    ModbusInvalidRequestError
)
from modbus_tk.hooks import call_hooks
from modbus_tk.utils import threadsafe_function, get_log_buffer

# modbus_tk is using the python logging mechanism
# you can define this logger in your app in order to see its prints logs


class Query(object):
    """
    Interface to be implemented in subclass for every specific modbus MAC layer
    """

    def __init__(self):
        """Constructor"""
        pass

    def build_request(self, pdu, slave):
        """
        Get the modbus application protocol request pdu and slave id
        Encapsulate with MAC layer information
        Returns a string
        """
        raise NotImplementedError()

    def parse_response(self, response):
        """
        Get the full response and extract the modbus application protocol
        response pdu
        Returns a string
        """
        raise NotImplementedError()

    def parse_request(self, request):
        """
        Get the full request and extract the modbus application protocol
        request pdu
        Returns a string and the slave id
        """
        raise NotImplementedError()

    def build_response(self, response_pdu):
        """
        Get the modbus application protocol response pdu and encapsulate with
        MAC layer information
        Returns a string
        """
        raise NotImplementedError()


class Master(object):
    """
    This class implements the Modbus Application protocol for a master
    To be subclassed with a class implementing the MAC layer
    """

    def __init__(self, timeout_in_sec, hooks=None):
        """Constructor: can define a timeout"""
        self._timeout = timeout_in_sec
        self._verbose = False
        self._is_opened = False

    def __del__(self):
        """Destructor: close the connection"""
        self.close()

    def set_verbose(self, verbose):
        """print some more log prints for debug purpose"""
        self._verbose = verbose

    def open(self):
        """open the communication with the slave"""
        if not self._is_opened:
            self._do_open()
            self._is_opened = True

    def close(self):
        """close the communication with the slave"""
        if self._is_opened:
            ret = self._do_close()
            if ret:
                self._is_opened = False

    def _do_open(self):
        """Open the MAC layer"""
        raise NotImplementedError()

    def _do_close(self):
        """Close the MAC layer"""
        raise NotImplementedError()

    def _send(self, buf):
        """Send data to a slave on the MAC layer"""
        raise NotImplementedError()

    def _recv(self, expected_length):
        """
        Receive data from a slave on the MAC layer
        if expected_length is >=0 then consider that the response is done when this
        number of bytes is received
        """
        raise NotImplementedError()

    def _make_query(self):
        """
        Returns an instance of a Query subclass implementing
        the MAC layer protocol
        """
        raise NotImplementedError()

    @threadsafe_function
    def execute(
        self, slave, function_code, starting_address, quantity_of_x=0, output_value=0, data_format="", expected_length=-1, write_starting_address_FC23=0):
        """
        Execute a modbus query and returns the data part of the answer as a tuple
        The returned tuple depends on the query function code. see modbus protocol
        specification for details
        data_format makes possible to extract the data like defined in the
        struct python module documentation
        """

        pdu = ""
        is_read_function = False
        nb_of_digits = 0

        # open the connection if it is not already done
        self.open()

        # Build the modbus pdu and the format of the expected data.
        # It depends of function code. see modbus specifications for details.
        if function_code == defines.READ_COILS or function_code == defines.READ_DISCRETE_INPUTS:
            is_read_function = True
            pdu = struct.pack(">BHH", function_code, starting_address, quantity_of_x)
            byte_count = quantity_of_x // 8
            if (quantity_of_x % 8) > 0:
                byte_count += 1
            nb_of_digits = quantity_of_x
            if not data_format:
                data_format = ">" + (byte_count * "B")
            if expected_length < 0:
                # No length was specified and calculated length can be used:
                # slave + func + bytcodeLen + bytecode + crc1 + crc2
                expected_length = byte_count + 5

        elif function_code == defines.READ_INPUT_REGISTERS or function_code == defines.READ_HOLDING_REGISTERS:
            is_read_function = True
            pdu = struct.pack(">BHH", function_code, starting_address, quantity_of_x)
            if not data_format:
                data_format = ">" + (quantity_of_x * "H")
            if expected_length < 0:
                # No length was specified and calculated length can be used:
                # slave + func + bytcodeLen + bytecode x 2 + crc1 + crc2
                expected_length = 2 * quantity_of_x + 5

        elif (function_code == defines.WRITE_SINGLE_COIL) or (function_code == defines.WRITE_SINGLE_REGISTER):
            if function_code == defines.WRITE_SINGLE_COIL:
                if output_value != 0:
                    output_value = 0xff00
                fmt = ">BHH"
            else:
                fmt = ">BH"+("H" if output_value >= 0 else "h")
            pdu = struct.pack(fmt, function_code, starting_address, output_value)
            if not data_format:
                data_format = ">HH"
            if expected_length < 0:
                # No length was specified and calculated length can be used:
                # slave + func + adress1 + adress2 + value1+value2 + crc1 + crc2
                expected_length = 8

        elif function_code == defines.WRITE_MULTIPLE_COILS:
            byte_count = len(output_value) // 8
            if (len(output_value) % 8) > 0:
                byte_count += 1
            pdu = struct.pack(">BHHB", function_code, starting_address, len(output_value), byte_count)
            i, byte_value = 0, 0
            for j in output_value:
                if j > 0:
                    byte_value += pow(2, i)
                if i == 7:
                    pdu += struct.pack(">B", byte_value)
                    i, byte_value = 0, 0
                else:
                    i += 1
            if i > 0:
                pdu += struct.pack(">B", byte_value)
            if not data_format:
                data_format = ">HH"
            if expected_length < 0:
                # No length was specified and calculated length can be used:
                # slave + func + adress1 + adress2 + outputQuant1 + outputQuant2 + crc1 + crc2
                expected_length = 8

        elif function_code == defines.WRITE_MULTIPLE_REGISTERS:
            if output_value and data_format:
                byte_count =  struct.calcsize(data_format)
            else:
                byte_count = 2 * len(output_value)
            pdu = struct.pack(">BHHB", function_code, starting_address, byte_count // 2, byte_count)
            if output_value and data_format:
                pdu += struct.pack(data_format, *output_value)
            else:
                for j in output_value:
                    fmt = "H" if j >= 0 else "h"
                    pdu += struct.pack(">" + fmt, j)
            # data_format is now used to process response which is always 2 registers:
            #   1) data address of first register, 2) number of registers written
            data_format = ">HH"
            if expected_length < 0:
                # No length was specified and calculated length can be used:
                # slave + func + adress1 + adress2 + outputQuant1 + outputQuant2 + crc1 + crc2
                expected_length = 8

        elif function_code == defines.READ_EXCEPTION_STATUS:
            pdu = struct.pack(">B", function_code)
            data_format = ">B"
            if expected_length < 0:
                # No length was specified and calculated length can be used:
                expected_length = 5

        elif function_code == defines.DIAGNOSTIC:
            # SubFuncCode  are in starting_address
            pdu = struct.pack(">BH", function_code, starting_address)
            if len(output_value) > 0:
                for j in output_value:
                    # copy data in pdu
                    pdu += struct.pack(">B", j)
                if not data_format:
                    data_format = ">" + (len(output_value) * "B")
                if expected_length < 0:
                    # No length was specified and calculated length can be used:
                    # slave + func + SubFunc1 + SubFunc2 + Data + crc1 + crc2
                    expected_length = len(output_value) + 6

        elif function_code == defines.READ_WRITE_MULTIPLE_REGISTERS:
            is_read_function = True
            byte_count = 2 * len(output_value)
            pdu = struct.pack(
                ">BHHHHB",
                function_code, starting_address, quantity_of_x, write_starting_address_FC23,
                len(output_value), byte_count
            )
            for j in output_value:
                fmt = "H" if j >= 0 else "h"
                # copy data in pdu
                pdu += struct.pack(">"+fmt, j)
            if not data_format:
                data_format = ">" + (quantity_of_x * "H")
            if expected_length < 0:
                # No lenght was specified and calculated length can be used:
                # slave + func + bytcodeLen + bytecode x 2 + crc1 + crc2
                expected_length = 2 * quantity_of_x + 5
        else:
            raise ModbusFunctionNotSupportedError("The {0} function code is not supported. ".format(function_code))

        # instantiate a query which implements the MAC (TCP or RTU) part of the protocol
        query = self._make_query()

        # add the mac part of the protocol to the request
        request = query.build_request(pdu, slave)

        # send the request to the slave
        retval = call_hooks("modbus.Master.before_send", (self, request))
        if retval is not None:
            request = retval
        if self._verbose:
            LOGGER.debug(get_log_buffer("-> ", request))
        self._send(request)

        call_hooks("modbus.Master.after_send", (self, ))

        if slave != 0:
            # receive the data from the slave
            response = self._recv(expected_length)
            retval = call_hooks("modbus.Master.after_recv", (self, response))
            if retval is not None:
                response = retval
            if self._verbose:
                LOGGER.debug(get_log_buffer("<- ", response))

            # extract the pdu part of the response
            response_pdu = query.parse_response(response)

            # analyze the received data
            (return_code, byte_2) = struct.unpack(">BB", response_pdu[0:2])

            if return_code > 0x80:
                # the slave has returned an error
                exception_code = byte_2
                raise ModbusError(exception_code)
            else:
                if is_read_function:
                    # get the values returned by the reading function
                    byte_count = byte_2
                    data = response_pdu[2:]
                    if byte_count != len(data):
                        # the byte count in the pdu is invalid
                        raise ModbusInvalidResponseError(
                            "Byte count is {0} while actual number of bytes is {1}. ".format(byte_count, len(data))
                        )
                else:
                    # returns what is returned by the slave after a writing function
                    data = response_pdu[1:]

                # returns the data as a tuple according to the data_format
                # (calculated based on the function or user-defined)
                result = struct.unpack(data_format, data)
                if nb_of_digits > 0:
                    digits = []
                    for byte_val in result:
                        for i in range(8):
                            if len(digits) >= nb_of_digits:
                                break
                            digits.append(byte_val % 2)
                            byte_val = byte_val >> 1
                    result = tuple(digits)
                return result

    def set_timeout(self, timeout_in_sec):
        """Defines a timeout on the MAC layer"""
        self._timeout = timeout_in_sec

    def get_timeout(self):
        """Gets the current value of the MAC layer timeout"""
        return self._timeout


class ModbusBlock(object):
    """This class represents the values for a range of addresses"""

    def __init__(self, starting_address, size, name=''):
        """
        Contructor: defines the address range and creates the array of values
        """
        self.starting_address = starting_address
        self._data = [0] * size
        self.size = len(self._data)

    def is_in(self, starting_address, size):
        """
        Returns true if a block with the given address and size
        would overlap this block
        """
        if starting_address > self.starting_address:
            return (self.starting_address + self.size) > starting_address
        elif starting_address < self.starting_address:
            return (starting_address + size) > self.starting_address
        return True

    def __getitem__(self, item):
        """"""
        return self._data.__getitem__(item)

    def __setitem__(self, item, value):
        """"""
        call_hooks("modbus.ModbusBlock.setitem", (self, item, value))
        return self._data.__setitem__(item, value)


class Slave(object):
    """
    This class define a modbus slave which is in charge of making the action
    asked by a modbus query
    """

    def __init__(self, slave_id, unsigned=True, memory=None):
        """Constructor"""
        self._id = slave_id

        # treat every value written to/read from register as an unsigned value
        self.unsigned = unsigned

        # the map registring all blocks of the slave
        self._blocks = {}
        # a shortcut to find blocks per type
        if memory is None:
            self._memory = {
                defines.COILS: [],
                defines.DISCRETE_INPUTS: [],
                defines.HOLDING_REGISTERS: [],
                defines.ANALOG_INPUTS: [],
            }
        else:
            self._memory = memory
        # a lock for mutual access to the _blocks and _memory maps
        self._data_lock = threading.RLock()
        # map modbus function code to a function:
        self._fn_code_map = {
            defines.READ_COILS: self._read_coils,
            defines.READ_DISCRETE_INPUTS: self._read_discrete_inputs,
            defines.READ_INPUT_REGISTERS: self._read_input_registers,
            defines.READ_HOLDING_REGISTERS: self._read_holding_registers,
            defines.WRITE_SINGLE_COIL: self._write_single_coil,
            defines.WRITE_SINGLE_REGISTER: self._write_single_register,
            defines.WRITE_MULTIPLE_COILS: self._write_multiple_coils,
            defines.WRITE_MULTIPLE_REGISTERS: self._write_multiple_registers,
        }

    def _get_block_and_offset(self, block_type, address, length):
        """returns the block and offset corresponding to the given address"""
        for block in self._memory[block_type]:
            if address >= block.starting_address:
                offset = address - block.starting_address
                if block.size >= offset + length:
                    return block, offset
        raise ModbusError(defines.ILLEGAL_DATA_ADDRESS)

    def _read_digital(self, block_type, request_pdu):
        """read the value of coils and discrete inputs"""
        (starting_address, quantity_of_x) = struct.unpack(">HH", request_pdu[1:5])

        if (quantity_of_x <= 0) or (quantity_of_x > 2000):
            # maximum allowed size is 2000 bits in one reading
            raise ModbusError(defines.ILLEGAL_DATA_VALUE)

        block, offset = self._get_block_and_offset(block_type, starting_address, quantity_of_x)

        values = block[offset:offset+quantity_of_x]

        # pack bits in bytes
        byte_count = quantity_of_x // 8
        if (quantity_of_x % 8) > 0:
            byte_count += 1

        # write the response header
        response = struct.pack(">B", byte_count)

        i, byte_value = 0, 0
        for coil in values:
            if coil:
                byte_value += (1 << i)
            if i >= 7:
                # write the values of 8 bits in a byte
                response += struct.pack(">B", byte_value)
                # reset the counters
                i, byte_value = 0, 0
            else:
                i += 1

        # if there is remaining bits: add one more byte with their values
        if i > 0:
            fmt = "B" if self.unsigned else "b"
            response += struct.pack(">"+fmt, byte_value)
        return response

    def _read_coils(self, request_pdu):
        """handle read coils modbus function"""
        call_hooks("modbus.Slave.handle_read_coils_request", (self, request_pdu))
        return self._read_digital(defines.COILS, request_pdu)

    def _read_discrete_inputs(self, request_pdu):
        """handle read discrete inputs modbus function"""
        call_hooks("modbus.Slave.handle_read_discrete_inputs_request", (self, request_pdu))
        return self._read_digital(defines.DISCRETE_INPUTS, request_pdu)

    def _read_registers(self, block_type, request_pdu):
        """read the value of holding and input registers"""
        (starting_address, quantity_of_x) = struct.unpack(">HH", request_pdu[1:5])

        if (quantity_of_x <= 0) or (quantity_of_x > 125):
            # maximum allowed size is 125 registers in one reading
            LOGGER.debug("quantity_of_x is %d", quantity_of_x)
            raise ModbusError(defines.ILLEGAL_DATA_VALUE)

        # look for the block corresponding to the request
        block, offset = self._get_block_and_offset(block_type, starting_address, quantity_of_x)

        # get the values
        values = block[offset:offset+quantity_of_x]

        # write the response header
        response = struct.pack(">B", 2 * quantity_of_x)
        # add the values of every register on 2 bytes
        for reg in values:
            fmt = "H" if self.unsigned else "h"
            response += struct.pack(">"+fmt, reg)
        return response

    def _read_holding_registers(self, request_pdu):
        """handle read coils modbus function"""
        call_hooks("modbus.Slave.handle_read_holding_registers_request", (self, request_pdu))
        return self._read_registers(defines.HOLDING_REGISTERS, request_pdu)

    def _read_input_registers(self, request_pdu):
        """handle read coils modbus function"""
        call_hooks("modbus.Slave.handle_read_input_registers_request", (self, request_pdu))
        return self._read_registers(defines.ANALOG_INPUTS, request_pdu)

    def _write_multiple_registers(self, request_pdu):
        """execute modbus function 16"""
        call_hooks("modbus.Slave.handle_write_multiple_registers_request", (self, request_pdu))
        # get the starting address and the number of items from the request pdu
        (starting_address, quantity_of_x, byte_count) = struct.unpack(">HHB", request_pdu[1:6])

        if (quantity_of_x <= 0) or (quantity_of_x > 123) or (byte_count != (quantity_of_x * 2)):
            # maximum allowed size is 123 registers in one reading
            raise ModbusError(defines.ILLEGAL_DATA_VALUE)

        # look for the block corresponding to the request
        block, offset = self._get_block_and_offset(defines.HOLDING_REGISTERS, starting_address, quantity_of_x)

        count = 0
        for i in range(quantity_of_x):
            count += 1
            fmt = "H" if self.unsigned else "h"
            block[offset+i] = struct.unpack(">"+fmt, request_pdu[6+2*i:8+2*i])[0]

        return struct.pack(">HH", starting_address, count)

    def _write_multiple_coils(self, request_pdu):
        """execute modbus function 15"""
        call_hooks("modbus.Slave.handle_write_multiple_coils_request", (self, request_pdu))
        # get the starting address and the number of items from the request pdu
        (starting_address, quantity_of_x, byte_count) = struct.unpack(">HHB", request_pdu[1:6])

        expected_byte_count = quantity_of_x // 8
        if (quantity_of_x % 8) > 0:
            expected_byte_count += 1

        if (quantity_of_x <= 0) or (quantity_of_x > 1968) or (byte_count != expected_byte_count):
            # maximum allowed size is 1968 coils
            raise ModbusError(defines.ILLEGAL_DATA_VALUE)

        # look for the block corresponding to the request
        block, offset = self._get_block_and_offset(defines.COILS, starting_address, quantity_of_x)

        count = 0
        for i in range(byte_count):
            if count >= quantity_of_x:
                break
            fmt = "B" if self.unsigned else "b"
            (byte_value, ) = struct.unpack(">"+fmt, request_pdu[6+i:7+i])
            for j in range(8):
                if count >= quantity_of_x:
                    break

                if byte_value & (1 << j):
                    block[offset+i*8+j] = 1
                else:
                    block[offset+i*8+j] = 0

                count += 1
        return struct.pack(">HH", starting_address, count)

    def _write_single_register(self, request_pdu):
        """execute modbus function 6"""
        call_hooks("modbus.Slave.handle_write_single_register_request", (self, request_pdu))

        fmt = "H" if self.unsigned else "h"
        (data_address, value) = struct.unpack(">H"+fmt, request_pdu[1:5])
        block, offset = self._get_block_and_offset(defines.HOLDING_REGISTERS, data_address, 1)
        block[offset] = value
        # returns echo of the command
        return request_pdu[1:]

    def _write_single_coil(self, request_pdu):
        """execute modbus function 5"""

        call_hooks("modbus.Slave.handle_write_single_coil_request", (self, request_pdu))
        (data_address, value) = struct.unpack(">HH", request_pdu[1:5])
        block, offset = self._get_block_and_offset(defines.COILS, data_address, 1)
        if value == 0:
            block[offset] = 0
        elif value == 0xff00:
            block[offset] = 1
        else:
            raise ModbusError(defines.ILLEGAL_DATA_VALUE)
        # returns echo of the command
        return request_pdu[1:]

    def handle_request(self, request_pdu, broadcast=False):
        """
        parse the request pdu, makes the corresponding action
        and returns the response pdu
        """
        # thread-safe
        with self._data_lock:
            try:
                retval = call_hooks("modbus.Slave.handle_request", (self, request_pdu))
                if retval is not None:
                    return retval

                # get the function code
                (function_code, ) = struct.unpack(">B", request_pdu[0:1])

                # check if the function code is valid. If not returns error response
                if function_code not in self._fn_code_map:
                    raise ModbusError(defines.ILLEGAL_FUNCTION)

                # if read query is broadcasted raises an error
                cant_be_broadcasted = (
                    defines.READ_COILS,
                    defines.READ_DISCRETE_INPUTS,
                    defines.READ_INPUT_REGISTERS,
                    defines.READ_HOLDING_REGISTERS
                )
                if broadcast and (function_code in cant_be_broadcasted):
                    raise ModbusInvalidRequestError("Function %d can not be broadcasted" % function_code)

                # execute the corresponding function
                response_pdu = self._fn_code_map[function_code](request_pdu)
                if response_pdu:
                    if broadcast:
                        call_hooks("modbus.Slave.on_handle_broadcast", (self, response_pdu))
                        LOGGER.debug("broadcast: %s", get_log_buffer("!!", response_pdu))
                        return ""
                    else:
                        return struct.pack(">B", function_code) + response_pdu
                raise Exception("No response for function %d" % function_code)

            except ModbusError as excpt:
                LOGGER.debug(str(excpt))
                call_hooks("modbus.Slave.on_exception", (self, function_code, excpt))
                return struct.pack(">BB", function_code+128, excpt.get_exception_code())

    def add_block(self, block_name, block_type, starting_address, size):
        """Add a new block identified by its name"""
        # thread-safe
        with self._data_lock:
            if size <= 0:
                raise InvalidArgumentError("size must be a positive number")

            if starting_address < 0:
                raise InvalidArgumentError("starting address must be zero or positive number")

            if block_name in self._blocks:
                raise DuplicatedKeyError("Block {0} already exists. ".format(block_name))

            if block_type not in self._memory:
                raise InvalidModbusBlockError("Invalid block type {0}".format(block_type))

            # check that the new block doesn't overlap an existing block
            # it means that only 1 block per type must correspond to a given address
            # for example: it must not have 2 holding registers at address 100
            index = 0
            for i in range(len(self._memory[block_type])):
                block = self._memory[block_type][i]
                if block.is_in(starting_address, size):
                    raise OverlapModbusBlockError(
                        "Overlap block at {0} size {1}".format(block.starting_address, block.size)
                    )
                if block.starting_address > starting_address:
                    index = i
                    break

            # if the block is ok: register it
            self._blocks[block_name] = (block_type, starting_address)
            # add it in the 'per type' shortcut
            self._memory[block_type].insert(index, ModbusBlock(starting_address, size, block_name))

    def remove_block(self, block_name):
        """
        Remove the block with the given name.
        Raise an exception if not found
        """
        # thread safe
        with self._data_lock:
            block = self._get_block(block_name)

            # the block has been found: remove it from the shortcut
            block_type = self._blocks.pop(block_name)[0]
            self._memory[block_type].remove(block)

    def remove_all_blocks(self):
        """
        Remove all the blocks
        """
        # thread safe
        with self._data_lock:
            self._blocks.clear()
            for key in self._memory:
                self._memory[key] = []

    def _get_block(self, block_name):
        """Find a block by its name and raise and exception if not found"""
        if block_name not in self._blocks:
            raise MissingKeyError("block {0} not found".format(block_name))
        (block_type, starting_address) = self._blocks[block_name]
        for block in self._memory[block_type]:
            if block.starting_address == starting_address:
                return block
        raise Exception("Bug?: the block {0} is not registered properly in memory".format(block_name))

    def set_values(self, block_name, address, values):
        """
        Set the values of the items at the given address
        If values is a list or a tuple, the value of every item is written
        If values is a number, only one value is written
        """
        # thread safe
        with self._data_lock:
            block = self._get_block(block_name)

            # the block has been found
            # check that it doesn't write out of the block
            offset = address-block.starting_address

            size = 1
            if isinstance(values, list) or isinstance(values, tuple):
                size = len(values)

            if (offset < 0) or ((offset + size) > block.size):
                raise OutOfModbusBlockError(
                    "address {0} size {1} is out of block {2}".format(address, size, block_name)
                )

            # if Ok: write the values
            if isinstance(values, list) or isinstance(values, tuple):
                block[offset:offset+len(values)] = values
            else:
                block[offset] = values

    def get_values(self, block_name, address, size=1):
        """
        return the values of n items at the given address of the given block
        """
        # thread safe
        with self._data_lock:
            block = self._get_block(block_name)

            # the block has been found
            # check that it doesn't write out of the block
            offset = address - block.starting_address

            if (offset < 0) or ((offset + size) > block.size):
                raise OutOfModbusBlockError(
                    "address {0} size {1} is out of block {2}".format(address, size, block_name)
                )

            # returns the values
            if size == 1:
                return tuple([block[offset], ])
            else:
                return tuple(block[offset:offset+size])


class Databank(object):
    """A databank is a shared place containing the data of all slaves"""

    def __init__(self, error_on_missing_slave=True):
        """Constructor"""
        # the map of slaves by ids
        self._slaves = {}
        # protect access to the map of slaves
        self._lock = threading.RLock()
        self.error_on_missing_slave = error_on_missing_slave

    def add_slave(self, slave_id, unsigned=True, memory=None):
        """Add a new slave with the given id"""
        with self._lock:
            if (slave_id <= 0) or (slave_id > 255):
                raise Exception("Invalid slave id {0}".format(slave_id))
            if slave_id not in self._slaves:
                self._slaves[slave_id] = Slave(slave_id, unsigned, memory)
                return self._slaves[slave_id]
            else:
                raise DuplicatedKeyError("Slave {0} already exists".format(slave_id))

    def get_slave(self, slave_id):
        """Get the slave with the given id"""
        with self._lock:
            if slave_id in self._slaves:
                return self._slaves[slave_id]
            else:
                raise MissingKeyError("Slave {0} doesn't exist".format(slave_id))

    def remove_slave(self, slave_id):
        """Remove the slave with the given id"""
        with self._lock:
            if slave_id in self._slaves:
                self._slaves.pop(slave_id)
            else:
                raise MissingKeyError("Slave {0} already exists".format(slave_id))

    def remove_all_slaves(self):
        """clean the list of slaves"""
        with self._lock:
            self._slaves.clear()

    def handle_request(self, query, request):
        """
        when a request is received, handle it and returns the response pdu
        """
        request_pdu = ""
        try:
            # extract the pdu and the slave id
            (slave_id, request_pdu) = query.parse_request(request)

            # get the slave and let him executes the action
            if slave_id == 0:
                # broadcast
                for key in self._slaves:
                    self._slaves[key].handle_request(request_pdu, broadcast=True)
                return
            else:
                try:
                    slave = self.get_slave(slave_id)
                except MissingKeyError:
                    if self.error_on_missing_slave:
                        raise
                    else:
                        return ""

                response_pdu = slave.handle_request(request_pdu)
                # make the full response
                response = query.build_response(response_pdu)
                return response
        except ModbusInvalidRequestError as excpt:
            # Request is invalid, do not send any response
            LOGGER.error("invalid request: " + str(excpt))
            return ""
        except MissingKeyError as excpt:
            # No slave with this ID in server, do not send any response
            LOGGER.error("handle request failed: " + str(excpt))
            return ""
        except Exception as excpt:
            call_hooks("modbus.Databank.on_error", (self, excpt, request_pdu))
            LOGGER.error("handle request failed: " + str(excpt))

        # If the request was not handled correctly, return a server error response
        func_code = 1
        if len(request_pdu) > 0:
            (func_code, ) = struct.unpack(">B", request_pdu[0:1])

        return struct.pack(">BB", func_code + 0x80, defines.SLAVE_DEVICE_FAILURE)


class Server(object):
    """
    This class owns several slaves and defines an interface
    to be implemented for a TCP or RTU server
    """

    def __init__(self, databank=None):
        """Constructor"""
        # never use a mutable type as default argument
        self._databank = databank if databank else Databank()
        self._verbose = False
        self._thread = None
        self._go = None
        self._make_thread()

    def _do_init(self):
        """executed before the server starts: to be overridden"""
        pass

    def _do_exit(self):
        """executed after the server stops: to be overridden"""
        pass

    def _do_run(self):
        """main function of the server: to be overridden"""
        pass

    def _make_thread(self):
        """create the main thread of the server"""
        self._thread = threading.Thread(target=Server._run_server, args=(self,))
        self._go = threading.Event()

    def set_verbose(self, verbose):
        """if verbose is true the sent and received packets will be logged"""
        self._verbose = verbose

    def get_db(self):
        """returns the databank"""
        return self._databank

    def add_slave(self, slave_id, unsigned=True, memory=None):
        """add slave to the server"""
        return self._databank.add_slave(slave_id, unsigned, memory)

    def get_slave(self, slave_id):
        """get the slave with the given id"""
        return self._databank.get_slave(slave_id)

    def remove_slave(self, slave_id):
        """remove the slave with the given id"""
        self._databank.remove_slave(slave_id)

    def remove_all_slaves(self):
        """remove the slave with the given id"""
        self._databank.remove_all_slaves()

    def _make_query(self):
        """
        Returns an instance of a Query subclass implementing
        the MAC layer protocol
        """
        raise NotImplementedError()

    def start(self):
        """Start the server. It will handle request"""
        self._go.set()
        self._thread.start()

    def stop(self):
        """stop the server. It doesn't handle request anymore"""
        if self._thread.is_alive():
            self._go.clear()
            self._thread.join()

    def _run_server(self):
        """main function of the main thread"""
        try:
            self._do_init()
            while self._go.isSet():
                self._do_run()
            LOGGER.info("%s has stopped", self.__class__)
            self._do_exit()
        except Exception as excpt:
            LOGGER.error("server error: %s", str(excpt))
        # make possible to rerun in future
        self._make_thread()

    def _handle(self, request):
        """handle a received sentence"""

        if self._verbose:
            LOGGER.debug(get_log_buffer("-->", request))

        # gets a query for analyzing the request
        query = self._make_query()

        retval = call_hooks("modbus.Server.before_handle_request", (self, request))
        if retval:
            request = retval

        response = self._databank.handle_request(query, request)
        retval = call_hooks("modbus.Server.after_handle_request", (self, response))
        if retval:
            response = retval

        if response and self._verbose:
            LOGGER.debug(get_log_buffer("<--", response))
        return response
