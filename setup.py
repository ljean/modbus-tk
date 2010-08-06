#!/usr/bin/env python
# -*- coding: utf_8 -*-
"""
 Modbus TestKit: Implementation of Modbus protocol in python

 (C)2009 - Luc Jean - luc.jean@gmail.com
 (C)2009 - Apidev - http://www.apidev.fr

 This is distributed under GNU LGPL license, see license.txt
"""

from setuptools import setup
import sys, os

version = '0.4'

setup(name = 'modbus_tk',
    version = version,
    description = "Implementation of modbus protocol in python",
    long_description='''
    Modbus Test Kit provides implementation of slave and master for Modbus TCP and RTU 
    The main goal is to be used as testing tools.
    ''',
    classifiers = [
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Communications',
        'Topic :: Software Development'
    ],
    keywords = 'modbus, serial, tcp',
    author = 'Luc Jean',
    author_email = 'luc.jean@gmail.com',
    maintainer = 'Luc Jean',
    maintainer_email = 'luc.jean@gmail.com',
    url='http://code.google.com/p/modbus-tk/',
    license = 'LGPL',
    packages=['modbus_tk'],
    platforms = ["Linux","Mac OS X","Win"],
    )
