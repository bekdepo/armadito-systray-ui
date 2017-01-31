# Copyright (C) 2016-2017 Teclib'

# This file is part of Armadito indicator.

# Armadito indicator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Armadito indicator is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Armadito indicator.  If not, see <http://www.gnu.org/licenses/>.

import json
import socket
from gi.repository import GObject as gobject

# TODO
# * close socket and remove watch on error
# * implement mapper
# * implement notification handling

def on_message_received(source, cb_condition, conn):
    if cb_condition == gobject.IO_ERR:
        conn.process_error()
    else:
        conn.process_data()
    return True

class MarshallObject(object):
    pass

def unmarshall(j_obj):
    o = MarshallObject()
    for k, v in j_obj.items():
        if type(v) is str or type(v) is int:
            setattr(o, k, v)
        elif type(v) is dict:
            setattr(o, k, unmarshall(v))
        # must handle the array case
    return o

class Connection(object):
    def __init__(self, sock_path):
        self.sock_path = sock_path
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.sock.settimeout(10)
        self.change_fun = None
        self.connected = False
        self.watch_id = None
        self.timeout_id = None

    def on_change(self, fun):
        self.change_fun = fun

    def connect(self):
        try:
            self.sock.connect(self.sock_path)
#        except socket.timeout as e:
        except OSError as e:
            print(str(e))
            self.process_error()
            return
        self.watch_id = gobject.io_add_watch(self.sock.fileno(), gobject.IO_IN | gobject.IO_ERR, on_message_received, self)
        if self.connected is False:
            self.connected = True
            if self.change_fun is not None:
                self.change_fun(self.connected)

    def process_error(self):
        if self.connected:
            self.connected = False
            self.watch_id = None
            if self.change_fun is not None:
                self.change_fun(self.connected)
        if self.timeout_id is None:
            self.timeout_id = gobject.timeout_add(1000, self.on_timeout)

    def on_timeout(self):
        self.connect()
        if self.connected:
            self.timeout_id = None
            return False
        return True

    def process_data(self):
        buff = self.sock.recv(4096)
        j_buff = buff.decode('utf-8')
        print(j_buff)
        d = json.loads(j_buff)
        jrpc_obj = unmarshall(d)
        self.dispatch(jrpc_obj)
        
    def map(self, m):
        self.mapper = m

    def dispatch(self, jrpc_obj):
        fun = self.mapper[jrpc_obj.method]
        if fun is not None:
            fun(jrpc_obj.params)

    def scan(self):
        p = {'root_path':'/home/fdechelle/Bureau/MalwareStore/EICAR/','send_progress':1}
        d = {'id':1,'params':p,'jsonrpc':'2.0','method':'scan'}
        buff = json.dumps(d).encode('utf-8')
        self.sock.send(buff)