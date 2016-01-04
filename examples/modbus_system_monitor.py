#!/usr/bin/env python
# -*- coding: utf_8 -*-
"""
 Modbus TestKit: Implementation of Modbus protocol in python

 (C)2009 - Luc Jean - luc.jean@gmail.com
 (C)2009 - Apidev - http://www.apidev.fr

 This is distributed under GNU LGPL license, see license.txt

 This example shows how to create a modbus server in charge of monitoring
 cpu consumption the machine

"""

from __future__ import print_function

import time

from modbus_tk import defines
from modbus_tk.modbus import LOGGER
from modbus_tk.modbus_tcp import TcpServer
from modbus_tk.simulator import Simulator
from modbus_tk.simulator_rpc_client import SimulatorRpcClient
from modbus_tk.utils import WorkerThread


class SystemDataCollector(object):
    """The class in charge of getting the CPU load"""
    def __init__(self, refresh_rate_in_sec):
        """Constructor"""
        self._simu = SimulatorRpcClient()
        self._max_count = refresh_rate_in_sec * 10
        self._count = self._max_count-1

    def collect(self):
        """get the CPU load thanks to WMI"""
        try:
            self._count += 1
            if self._count >= self._max_count:
                self._count = 0
                #WMI get the load percentage of the machine
                from win32com.client import GetObject
                wmi = GetObject('winmgmts:')
                cpu = wmi.InstancesOf('Win32_Processor')
                for (_cpu, i) in zip(cpu, range(10)):
                    value = _cpu.Properties_('LoadPercentage').Value
                    cpu_usage = int(str(value)) if value else 0

                    #execute a RPC command for changing the value
                    self._simu.set_values(1, "Cpu", i, (cpu_usage, ))
        except Exception as excpt:
            LOGGER.debug("SystemDataCollector error: %s", str(excpt))
        time.sleep(0.1)


def main():
    """main"""
    #create the object for getting CPU data
    data_collector = SystemDataCollector(5)
    #create the thread in charge of calling the data collector
    system_monitor = WorkerThread(data_collector.collect)

    #create the modbus TCP simulator and one slave
    #and one block of analog inputs
    simu = Simulator(TcpServer())
    slave = simu.server.add_slave(1)
    slave.add_block("Cpu", defines.ANALOG_INPUTS, 0, 10)

    try:
        LOGGER.info("'quit' for closing the server")

        #start the data collect
        system_monitor.start()

        #start the simulator! will block until quit command is received
        simu.start()

    except Exception as excpt:
        print(excpt)

    finally:
        #close the simulator
        simu.close()
        #stop the data collect
        system_monitor.stop()

if __name__ == "__main__":
    main()
