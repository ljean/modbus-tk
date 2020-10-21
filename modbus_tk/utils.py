#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Modbus TestKit: Implementation of Modbus protocol in python

 (C)2009 - Luc Jean - luc.jean@gmail.com
 (C)2009 - Apidev - http://www.apidev.fr

 This is distributed under GNU LGPL license, see license.txt
"""
from __future__ import print_function

import sys
import threading
import logging
import socket
import select
from modbus_tk import LOGGER

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


def threadsafe_function(fcn):
    """decorator making sure that the decorated function is thread safe"""
    lock = threading.RLock()

    def new(*args, **kwargs):
        """Lock and call the decorated function

           Unless kwargs['threadsafe'] == False
        """
        threadsafe = kwargs.pop('threadsafe', True)
        if threadsafe:
            lock.acquire()
        try:
            ret = fcn(*args, **kwargs)
        except Exception as excpt:
            raise excpt
        finally:
            if threadsafe:
                lock.release()
        return ret
    return new


def flush_socket(socks, lim=0):
    """remove the data present on the socket"""
    input_socks = [socks]
    cnt = 0
    while True:
        i_socks = select.select(input_socks, input_socks, input_socks, 0.0)[0]
        if len(i_socks) == 0:
            break
        for sock in i_socks:
            sock.recv(1024)
        if lim > 0:
            cnt += 1
            if cnt >= lim:
                #avoid infinite loop due to loss of connection
                raise Exception("flush_socket: maximum number of iterations reached")


def get_log_buffer(prefix, buff):
    """Format binary data into a string for debug purpose"""
    log = prefix
    for i in buff:
        log += str(ord(i) if PY2 else i) + "-"
    return log[:-1]


class ConsoleHandler(logging.Handler):
    """This class is a logger handler. It prints on the console"""

    def __init__(self):
        """Constructor"""
        logging.Handler.__init__(self)

    def emit(self, record):
        """format and print the record on the console"""
        print(self.format(record))


class LogitHandler(logging.Handler):
    """This class is a logger handler. It send to a udp socket"""

    def __init__(self, dest):
        """Constructor"""
        logging.Handler.__init__(self)
        self._dest = dest
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def emit(self, record):
        """format and send the record over udp"""
        data = self.format(record) + "\r\n"
        if PY3:
            data = to_data(data)
        self._sock.sendto(data, self._dest)


class DummyHandler(logging.Handler):
    """This class is a logger handler. It doesn't do anything"""

    def __init__(self):
        """Constructor"""
        super(DummyHandler, self).__init__()

    def emit(self, record):
        """do nothing with the given record"""
        pass


def create_logger(name="dummy", level=logging.DEBUG, record_format=None):
    """Create a logger according to the given settings"""
    if record_format is None:
        record_format = "%(asctime)s\t%(levelname)s\t%(module)s.%(funcName)s\t%(threadName)s\t%(message)s"

    logger = logging.getLogger("modbus_tk")
    logger.setLevel(level)
    formatter = logging.Formatter(record_format)
    if name == "udp":
        log_handler = LogitHandler(("127.0.0.1", 1975))
    elif name == "console":
        log_handler = ConsoleHandler()
    elif name == "dummy":
        log_handler = DummyHandler()
    else:
        raise Exception("Unknown handler %s" % name)
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)
    return logger


def swap_bytes(word_val):
    """swap lsb and msb of a word"""
    msb = (word_val >> 8) & 0xFF
    lsb = word_val & 0xFF
    return (lsb << 8) + msb


def calculate_crc(data):
    """Calculate the CRC16 of a datagram"""
    CRC16table = (
        0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
        0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
        0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
        0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
        0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
        0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
        0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
        0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
        0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
        0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
        0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
        0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
        0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
        0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
        0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
        0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
        0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
        0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
        0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
        0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
        0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
        0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
        0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
        0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
        0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
        0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
        0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
        0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
        0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
        0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
        0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
        0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040
    )
    crc = 0xFFFF
    if PY2:
        for c in data:
            crc = (crc >> 8) ^ CRC16table[(ord(c) ^ crc) & 0xFF]
    else:
        for c in data:
            crc = (crc >> 8) ^ CRC16table[((c) ^ crc) & 0xFF]
    return swap_bytes(crc)


def calculate_rtu_inter_char(baudrate):
    """calculates the interchar delay from the baudrate"""
    if baudrate <= 19200:
        return 11.0 / baudrate
    else:
        return 0.0005


class WorkerThread(object):
    """
    A thread which is running an almost-ever loop
    It can be stopped by calling the stop function
    """
    def __init__(self, main_fct, args=(), init_fct=None, exit_fct=None):
        """Constructor"""
        self._fcts = [init_fct, main_fct, exit_fct]
        self._args = args
        self._thread = threading.Thread(target=WorkerThread._run, args=(self,))
        self._go = threading.Event()

    def start(self):
        """Start the thread"""
        self._go.set()
        self._thread.start()

    def stop(self):
        """stop the thread"""
        if self._thread.is_alive():
            self._go.clear()
            self._thread.join()

    def _run(self):
        """main function of the thread execute _main_fct until stop is called"""
        #pylint: disable=broad-except
        try:
            if self._fcts[0]:
                self._fcts[0](*self._args)
            while self._go.isSet():
                self._fcts[1](*self._args)
        except Exception as excpt:
            LOGGER.error("error: %s", str(excpt))
        finally:
            if self._fcts[2]:
                self._fcts[2](*self._args)


def to_data(string_data):
    if PY2:
        return string_data
    else:
        return bytearray(string_data, 'ascii')
