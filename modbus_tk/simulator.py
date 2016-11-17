#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Modbus TestKit: Implementation of Modbus protocol in python

 (C)2009 - Luc Jean - luc.jean@gmail.com
 (C)2009 - Apidev - http://www.apidev.fr

 This is distributed under GNU LGPL license, see license.txt

 The modbus_tk simulator is a console application which is running a server with TCP and RTU communication
 It is possible to interact with the server from the command line or from a RPC (Remote Process Call)
"""
from __future__ import print_function

import ctypes
import os
import sys
import select
import serial
import threading
import time

import modbus_tk
from modbus_tk import hooks
from modbus_tk import modbus
from modbus_tk import modbus_tcp
from modbus_tk import modbus_rtu

if modbus_tk.utils.PY2:
    import Queue as queue
    import SocketServer
else:
    import queue
    import socketserver as SocketServer


# add logging capability
LOGGER = modbus_tk.utils.create_logger(name="console", record_format="%(message)s")

# The communication between the server and the user interfaces (console or rpc) are done through queues

# command received from the interfaces
INPUT_QUEUE = queue.Queue()

# response to be sent back by the interfaces
OUTPUT_QUEUE = queue.Queue()


class CompositeServer(modbus.Server):
    """make possible to have several servers sharing the same databank"""

    def __init__(self, list_of_server_classes, list_of_server_args, databank=None):
        """Constructor"""
        super(CompositeServer, self).__init__(databank)
        self._servers = [
            the_class(*the_args, **{"databank": self.get_db()})
            for the_class, the_args in zip(list_of_server_classes, list_of_server_args)
            if issubclass(the_class, modbus.Server)
        ]

    def set_verbose(self, verbose):
        """if verbose is true the sent and received packets will be logged"""
        for srv in self._servers:
            srv.set_verbose(verbose)

    def _make_thread(self):
        """should initialize the main thread of the server. You don't need it here"""
        pass

    def _make_query(self):
        """Returns an instance of a Query subclass implementing the MAC layer protocol"""
        raise NotImplementedError()

    def start(self):
        """Start the server. It will handle request"""
        for srv in self._servers:
            srv.start()

    def stop(self):
        """stop the server. It doesn't handle request anymore"""
        for srv in self._servers:
            srv.stop()


class RpcHandler(SocketServer.BaseRequestHandler):
    """An instance of this class is created every time an RPC call is received by the server"""

    def handle(self):
        """This function is called automatically by the SocketServer"""
        # self.request is the TCP socket connected to the client
        # read the incoming command
        request = self.request.recv(1024).strip()
        # write to the queue waiting to be processed by the server
        INPUT_QUEUE.put(request)
        # wait for the server answer in the output queue
        response = OUTPUT_QUEUE.get(timeout=5.0)
        # send back the answer
        self.request.send(response)


class RpcInterface(threading.Thread):
    """Manage RPC call over TCP/IP thanks to the SocketServer module"""

    def __init__(self):
        """Constructor"""
        super(RpcInterface, self).__init__()
        self.rpc_server = SocketServer.TCPServer(("", 2711), RpcHandler)

    def run(self):
        """run the server and wait that it returns"""
        self.rpc_server.serve_forever(0.5)

    def close(self):
        """force the socket server to exit"""
        try:
            self.rpc_server.shutdown()
            self.join(1.0)
        except Exception:
            LOGGER.warning("An error occurred while closing RPC interface")


class ConsoleInterface(threading.Thread):
    """Manage user actions from the console"""

    def __init__(self):
        """constructor: initialize communication with the console"""
        super(ConsoleInterface, self).__init__()
        self.inq = INPUT_QUEUE
        self.outq = OUTPUT_QUEUE

        if os.name == "nt":
            ctypes.windll.Kernel32.GetStdHandle.restype = ctypes.c_ulong
            self.console_handle = ctypes.windll.Kernel32.GetStdHandle(ctypes.c_ulong(0xfffffff5))
            ctypes.windll.Kernel32.WaitForSingleObject.restype = ctypes.c_ulong

        elif os.name == "posix":
            # select already imported
            pass

        else:
            raise Exception("%s platform is not supported yet" % os.name)

        self._go = threading.Event()
        self._go.set()

    def _check_console_input(self):
        """test if there is something to read on the console"""

        if os.name == "nt":
            if 0 == ctypes.windll.Kernel32.WaitForSingleObject(self.console_handle, 500):
                return True

        elif os.name == "posix":
            (inputready, abcd, efgh) = select.select([sys.stdin], [], [], 0.5)
            if len(inputready) > 0:
                return True

        else:
            raise Exception("%s platform is not supported yet" % os.name)

        return False

    def run(self):
        """read from the console, transfer to the server and write the answer"""
        while self._go.isSet(): #while app is running
            if self._check_console_input(): #if something to read on the console
                cmd = sys.stdin.readline() #read it
                self.inq.put(cmd) #dispatch it tpo the server
                response = self.outq.get(timeout=2.0) #wait for an answer
                sys.stdout.write(response) #write the answer on the console

    def close(self):
        """terminates the thread"""
        self._go.clear()
        self.join(1.0)


class Simulator(object):
    """The main class of the app in charge of running everything"""

    def __init__(self, server=None):
        """Constructor"""
        if server is None:
            self.server = CompositeServer([modbus_rtu.RtuServer, modbus_tcp.TcpServer], [(serial.Serial(0),), ()])
        else:
            self.server = server
        self.rpc = RpcInterface()
        self.console = ConsoleInterface()
        self.inq, self.outq = INPUT_QUEUE, OUTPUT_QUEUE
        self._hooks_fct = {}

        self.cmds = {
            "add_slave": self._do_add_slave,
            "has_slave": self._do_has_slave,
            "remove_slave": self._do_remove_slave,
            "remove_all_slaves": self._do_remove_all_slaves,
            "add_block": self._do_add_block,
            "remove_block": self._do_remove_block,
            "remove_all_blocks": self._do_remove_all_blocks,
            "set_values": self._do_set_values,
            "get_values": self._do_get_values,
            "install_hook": self._do_install_hook,
            "uninstall_hook": self._do_uninstall_hook,
            "set_verbose": self._do_set_verbose,
        }

    def add_command(self, name, fct):
        """add a custom command"""
        self.cmds[name] = fct

    def start(self):
        """run the servers"""
        self.server.start()
        self.console.start()
        self.rpc.start()

        LOGGER.info("modbus_tk.simulator is running...")

        self._handle()

    def declare_hook(self, fct_name, fct):
        """declare a hook function by its name. It must be installed by an install hook command"""
        self._hooks_fct[fct_name] = fct

    def _tuple_to_str(self, the_tuple):
        """convert a tuple to a string"""
        ret = ""
        for item in the_tuple:
            ret += (" " + str(item))
        return ret[1:]

    def _do_add_slave(self, args):
        """execute the add_slave command"""
        slave_id = int(args[1])
        self.server.add_slave(slave_id)
        return "{0}".format(slave_id)

    def _do_has_slave(self, args):
        """execute the has_slave command"""
        slave_id = int(args[1])
        try:
            self.server.get_slave(slave_id)
        except Exception:
            return "0"
        return "1"

    def _do_remove_slave(self, args):
        """execute the remove_slave command"""
        slave_id = int(args[1])
        self.server.remove_slave(slave_id)
        return ""

    def _do_remove_all_slaves(self, args):
        """execute the remove_slave command"""
        self.server.remove_all_slaves()
        return ""

    def _do_add_block(self, args):
        """execute the add_block command"""
        slave_id = int(args[1])
        name = args[2]
        block_type = int(args[3])
        starting_address = int(args[4])
        length = int(args[5])
        slave = self.server.get_slave(slave_id)
        slave.add_block(name, block_type, starting_address, length)
        return name

    def _do_remove_block(self, args):
        """execute the remove_block command"""
        slave_id = int(args[1])
        name = args[2]
        slave = self.server.get_slave(slave_id)
        slave.remove_block(name)

    def _do_remove_all_blocks(self, args):
        """execute the remove_all_blocks command"""
        slave_id = int(args[1])
        slave = self.server.get_slave(slave_id)
        slave.remove_all_blocks()

    def _do_set_values(self, args):
        """execute the set_values command"""
        slave_id = int(args[1])
        name = args[2]
        address = int(args[3])
        values = []
        for val in args[4:]:
            values.append(int(val))
        slave = self.server.get_slave(slave_id)
        slave.set_values(name, address, values)
        values = slave.get_values(name, address, len(values))
        return self._tuple_to_str(values)

    def _do_get_values(self, args):
        """execute the get_values command"""
        slave_id = int(args[1])
        name = args[2]
        address = int(args[3])
        length = int(args[4])
        slave = self.server.get_slave(slave_id)
        values = slave.get_values(name, address, length)
        return self._tuple_to_str(values)

    def _do_install_hook(self, args):
        """install a function as a hook"""
        hook_name = args[1]
        fct_name = args[2]
        hooks.install_hook(hook_name, self._hooks_fct[fct_name])

    def _do_uninstall_hook(self, args):
        """
        uninstall a function as a hook.
        If no function is given, uninstall all functions
        """
        hook_name = args[1]
        try:
            hooks.uninstall_hook(hook_name)
        except KeyError as exception:
            LOGGER.error(str(exception))

    def _do_set_verbose(self, args):
        """change the verbosity of the server"""
        verbose = int(args[1])
        self.server.set_verbose(verbose)
        return "%d" % verbose

    def _handle(self):
        """almost-for-ever loop in charge of listening for command and executing it"""
        while True:
            cmd = self.inq.get()
            args = cmd.strip('\r\n').split(' ')
            if cmd.find('quit') == 0:
                self.outq.put('bye-bye\r\n')
                break
            elif args[0] in self.cmds:
                try:
                    answer = self.cmds[args[0]](args)
                    self.outq.put("%s done: %s\r\n" % (args[0], answer))
                except Exception as msg:
                    self.outq.put("%s error: %s\r\n" % (args[0], msg))
            else:
                self.outq.put("error: unknown command %s\r\n" % (args[0]))

    def close(self):
        """close every server"""
        self.console.close()
        self.rpc.close()
        self.server.stop()


def print_me(args):
    """hook function example"""
    request = args[1]
    print("print_me: len = ", len(request))


def run_simulator():
    """run simulator"""
    simulator = Simulator()

    try:
        LOGGER.info("'quit' for closing the server")

        simulator.declare_hook("print_me", print_me)
        simulator.start()

    except Exception as exception:
        print(exception)

    finally:
        simulator.close()
        LOGGER.info("modbus_tk.simulator has stopped!")
        # In python 2.5, the SocketServer shutdown is not working Ok
        # The 2 lines below are an ugly temporary workaround
        time.sleep(1.0)
        sys.exit()


if __name__ == "__main__":
    run_simulator()
