modbus-tk: Create Modbus app easily with Python
=================================================

[![Build Status](https://semaphoreci.com/api/v1/ljean/modbus-tk/branches/master/shields_badge.svg)](https://semaphoreci.com/ljean/modbus-tk)

Download / Install
------------------------------------
Current version is 0.5.7 It is available on PyPI https://pypi.python.org/pypi/modbus_tk

License
------------------------------------
This is distributed under GNU LGPL license

Description
------------------------------------
Make possible to write modbus TCP and RTU master and slave.

It can be used for testing purpose : It is shipped with slave simulator and a master with a web-based hmi (ok the hmi need to be improved :).

It can also be used to create any application which need to communicate over modbus. It is a full-stack implementation and is used on "real applications".

Thanks to Python and the incredible set of existing libraries, it can fit a lot of different needs : database logging, HMI, report generation ...

modbus-tk is different from pymodbus which is another implementation of the modbus stack in python.

modbus-tk tries to limit dependencies (even if it requires pyserial for Modbus RTU).

modbus-tk has no link with tkInter. tk stands for 'testkit' or 'toolkit' depending of the way you use it.

Discussion group
------------------------------------
Please join the modbus-tk discussion group to participate : https://groups.google.com/forum/?hl=fr#!forum/modbus-tk

Features
------------------------------------
* Modbus TCP support for writing masters and slaves
* Modbus RTU support for writing masters and slaves (requires pyserial)
* Can be customized with hook mechanism (simulate errors, timeouts...)
* ready-to use simulator with RPC interface
* Defines very easily your own memory blocks
* Set/Get values for any place in a memory block
* logging capability through python logging module
* Web-based HMI (experimental feature which requires bottle)

Feedback
------------------------------------
Feedback is welcomed! Please enter an issue for giving your feedback.

Follow modbus-tk
------------------------------------
Follow on twitter : http://twitter.com/#!/luc_apidev

Company web site : <http://www.apidev.fr/>

Other links
------------------------------------
pymodslave http://sourceforge.net/projects/pymodslave/ : a gui app for simulation purpose built with Qt4 and modbus-tk

modbus-simulator https://github.com/dhoomakethu/kivy-modbus-simu : modbus simulator built with modbus-tk and kivy
