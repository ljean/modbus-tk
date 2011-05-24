#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Modbus TestKit: Implementation of Modbus protocol in python

 (C)2009 - Luc Jean - luc.jean@gmail.com
 (C)2009 - Apidev - http://www.apidev.fr

 This is distributed under GNU LGPL license, see license.txt
"""
from __future__ import with_statement
from bottle import route, run, template, TEMPLATES, send_file, redirect, request
import modbus_tk.modbus_tcp as modbus_tcp
import modbus_tk.modbus_rtu as modbus_rtu
import modbus_tk.modbus as modbus
import sqlite3
import webbrowser

SERIAL = True 

if SERIAL:
    SERIAL_PORTS = {}
    try:
        import serial
    except Exception, msg:
        SERIAL = False
        print "Warning: serial communication is disabled"
DEBUG = False if SERIAL else True #reload mode must not be set with serial com. It would cause an Access Denied 

class Master:
    def __init__(self, protocol, address, id, db):
        if protocol == "tcp":
            try:
                (host, port) = address.split(":")
                self.modbus = modbus_tcp.TcpMaster(str(host), int(port))
            except:
                self.modbus = modbus_tcp.TcpMaster(address) 
            self.modbus.set_timeout(5.0)
        elif protocol == "rtu":
            if SERIAL:
                args = unicode(address).split(',')
                kwargs = {} 
                for a in args:
                    key, val = a.split(':')
                    if key=='port':
                        try:
                            serial_port = int(val)
                        except:
                            serial_port = val
                    else:
                        kwargs[key] = val
                try:
                    try:
                        s = SERIAL_PORTS[serial_port]
                    except IndexError:
                        SERIAL_PORTS[serial_port] = s = serial.Serial(port=serial_port, **kwargs)
                    self.modbus = modbus_rtu.RtuMaster(s)
                except Exception, msg:
                    raise Exception("Protocol {0} error! {1}".format(protocol, msg))
            else:
                raise Exception("Protocol {0} is disabled!".format(protocol))
        else:
            raise Exception("Protocol {0} is not supported!".format(protocol))
    
        self.id = id
        self._db = db
        self.address = address
        self.protocol = protocol
        
        self.requests = self._db.get_requests(self.id)

    def get_slaves(self):
        return self._db.get_slaves(self.id)
        
    def add_request(self, id, fct, start, length):
        self._db.add_request(self.id, id, fct, start, length)
        self.requests = self._db.get_requests(self.id)
        
    def delete_request(self, id):
        self._db.delete_request(id)
        self.requests = self._db.get_requests(self.id)

class Persistence:
    def __init__(self):
        with self._get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM request;")
            except:
                cursor.execute("""CREATE TABLE master (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                                       protocol TEXT, 
                                                       server_address TEXT);""")
                
                cursor.execute("""CREATE TABLE request (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                                         master_id INTEGER,
                                                         slave INTEGER, 
                                                         function INTEGER,
                                                         address INTEGER,
                                                         length INTEGER,
                                                         FOREIGN KEY(master_id) REFERENCES master(id));""")
                
                cursor.execute("""INSERT INTO master (protocol, server_address) VALUES ('tcp', 'localhost');""")
                

    def _get_db(self):
        return sqlite3.connect("./db/master_webhmi.db")

    def get_data(self, sql_query, args=None):
       with self._get_db() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if args:
                cursor.execute(sql_query, args)
            else:
                cursor.execute(sql_query)
            l = []
            for row in cursor:
                d = {}
                for x in row.keys():
                    d[x] = row[x]
                l.append(d)
            return l
            
    def get_masters(self):
        return self.get_data("SELECT * FROM master;")
            
    def get_requests(self, master_id):
        reqs = self.get_data("SELECT * FROM request where master_id=?;", (master_id,))
        for r in reqs: 
            name = ' - '.join(['{0}: {1}'.format(x.capitalize(), r[x]) for x in r.keys() if x.find('id')<0])
            r['name'] = name
        return reqs

    def get_slaves(self, master_id):
        reqs = self.get_data("SELECT DISTINCT slave FROM request WHERE master_id=?;", (master_id,))
        return reqs
    
    def get_hr_requests_for_slave(self, master_id, slave_id):
        reqs = self.get_data("SELECT * FROM request WHERE master_id=? AND slave=? AND function=3;", (master_id,slave_id))
        return reqs
                
    def add_request(self, master, slave, fct, start, length):
        with self._get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO request (master_id, slave, function, address, length) VALUES (?, ?, ?, ?, ?)", \
                           (master, slave, fct, start, length))
        
    def delete_request(self, id):
        with self._get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM request WHERE id = ?", (id, ))
            
    def add_master(self, protocol, server_address):
        with self._get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO master (protocol, server_address) VALUES (?, ?)", (protocol, server_address))
        return self.get_data("SELECT MAX(id) FROM master;")[0]['MAX(id)']

    def delete_master(self, id):
        with self._get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM master WHERE id=?", (id,))
    
class App:
    def __init__(self):
        self._db = Persistence()
        self._load_masters()

    def _load_masters(self):
        self._masters = {}
        for m in self._db.get_masters():
            id = m['id']
            try:
                self._masters[id] = Master(m['protocol'], m['server_address'], id, self._db)
            except Exception, msg:
                print "WARNING! can't load master {0} - {1}: {2}".format(m['protocol'], m['server_address'], msg)

    def get_masters(self):
        the_keys = self._masters.keys()
        the_keys.sort()
        return [self._masters[k] for k in the_keys]

    def get_master(self, id):
        id = int(id)
        return self._masters[id]
    
    def add_master(self, protocol, server_address):
        id = self._db.add_master(protocol, server_address)
        self._load_masters()
        return id

    def delete_master(self, id):
        self._db.delete_master(id)
        self._load_masters()

APP = App()
        
@route('/media/:filename')
def static_file(filename):
    send_file(filename, root='./media/')

@route("/")
def index():
    redirect("/masters")
    #TEMPLATES.clear()
    #return template('templates/master_index', masters=APP.get_masters())

@route("/masters")
def master_list():
    TEMPLATES.clear()
    return template('templates/masters_list', masters=APP.get_masters())

@route("/master/:id")
def master_detail(id):
    TEMPLATES.clear()
    return template('templates/master_index', master=APP.get_master(id))

@route("/delete-master/:id")
def delete_master(id):
    TEMPLATES.clear()
    APP.delete_master(id)
    return redirect('/masters')


@route("modbus-read/:master_id/:slave_id/:function_code/:start_address/:length")
def show_results(master_id, slave_id, function_code, start_address, length):
    TEMPLATES.clear()
    master = APP.get_master(master_id)
    name = 'Slave {0} - Function {1}'.format(slave_id, function_code)
    friendly_name = 'Slave {0} - Function {1} - Address {2} - Count {3}'.format(slave_id, function_code, start_address, length)
    url = "/modbus-read/{0}/{1}/{2}/{3}/{4}".format(master_id, slave_id, function_code, start_address, length)
    try:
        results = master.modbus.execute(int(slave_id), int(function_code), int(start_address), int(length))
        lines = [i*16 for i in range(int(len(results)%16>0)+len(results)//16)]
        return template('templates/master_results', results=results, start=int(start_address), 
                        lines=lines, name=name, url=url, master=master, friendly_name=friendly_name)
    except modbus.ModbusError, msg:
        return template('templates/modbus_error', msg=msg, name=name, url=url, master=master, friendly_name=friendly_name)

@route("/modbus-read-all-hr/:master_id/:slave_id")
def show_results_all_hr(master_id, slave_id):
    TEMPLATES.clear()
    master = APP.get_master(master_id)
    requests = APP._db.get_hr_requests_for_slave(master_id, slave_id)
    name = 'Slave {0} - Function {1}'.format(slave_id, 3)
    friendly_name = 'Slave {0} - Function {1} - All Registers'.format(slave_id, 3)
    url = "/modbus-read-all-hr/{0}/{1}".format(master_id, slave_id)
    all_results = {}
    try:
        for req in requests:
            i = int(req['address'])
            #print "%s, %s, %s"%(int(slave_id), int(req['address']), int(req['length']))
            results = master.modbus.execute(int(slave_id), int(3), int(req['address']), int(req['length']))
            for result in results:
                all_results[i] = {'result': result, 'register_hex': hex(i)}
                i += 1
        return template('templates/master_results_all_hr', results=all_results, url=url,
                name=name, master=master, friendly_name=friendly_name)
    except modbus.ModbusError, msg:
        return template('templates/modbus_error', msg=msg, name=name, url=url, master=master, friendly_name=friendly_name)


@route('add-request/:master', method='POST')
def add_request(master):
    slave = request.POST['slave']
    function = request.POST['function']
    address = request.POST['address']
    length = request.POST['length']
    APP.get_master(master).add_request(slave, function, address, length)
    return show_results(master, slave, function, address, length)

@route('/delete-request/:master/:id')
def delete_request(master, id):
    APP.get_master(master).delete_request(id)
    return redirect('/master/%s'%(master))

@route('/add-master', method='POST')
def add_master():
    protocol = request.POST['protocol']
    server_address = request.POST['server_address']
    id = APP.add_master(protocol, server_address)
    return master_detail(id)

@route('/modbus-read-json/:master_id/:slave_id/:function_code/:start_address/:length')
def get_json_data(master_id, slave_id, function_code, start_address, length):
    master = APP.get_master(master_id)
    try:
        results = master.modbus.execute(int(slave_id), int(function_code), int(start_address), int(length))
        json_data = {}
        i = 0
        for r in results:
            json_data[str(i)] = r
            i += 1
    except modbus.ModbusError, msg:
        return template('templates/modbus_error', msg=msg, name=name, url=url, master=master, friendly_name=friendly_name)
    return json_data

@route('/modbus-read-json-all-hr/:master_id/:slave_id')
def get_all_json_data(master_id, slave_id):
    master = APP.get_master(master_id)
    requests = APP._db.get_hr_requests_for_slave(master_id, slave_id);
    try:
        json_data = {}
        for req in requests:
            i = int(req['address'])
            results = master.modbus.execute(int(slave_id), int(3), int(req['address']), int(req['length']))
            for result in results:
                json_data[str(i)] = result
                i += 1
    except modbus.ModbusError, msg:
        return template('templates/modbus_error', msg=msg, name=name, url=url, master=master, friendly_name=friendly_name)
    return json_data



webbrowser.open_new_tab('http://localhost:8075/')
run(reloader=DEBUG, port=8075)
