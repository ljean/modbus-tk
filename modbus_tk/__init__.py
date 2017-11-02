#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Modbus TestKit: Implementation of Modbus protocol in python

 (C)2009 - Luc Jean - luc.jean@gmail.com
 (C)2009 - Apidev - http://www.apidev.fr

 This is distributed under GNU LGPL license, see license.txt

 Make possible to write modbus TCP and RTU master and slave for testing purpose
 Modbus TestKit is different from pymodbus which is another implementation of
 the modbus stack in python

contributors:
----------------------------------
* OrangeTux
* denisstogl
* MELabs
* idahogray
* riaan.doorduin
* tor.sjowall
* smachin1000
* GadgetSteve 
* dhoomakethu
* zerox1212
* ffreckle
* Matthew West

Please let us know if your name is missing!

"""

VERSION = '0.5.8'

import logging
LOGGER = logging.getLogger("modbus_tk")
