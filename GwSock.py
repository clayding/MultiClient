from Actor import Actor
from MessageQueue import Message
import serial
import struct
import Global
import socket
import errno
import time

class Gw_Sock(Actor):
    def __init__(self, name, uuid, port):
        super(Gw_Sock, self).__init__(name)
        self._sock_port = port
        self._device_uuid = uuid
        self._device_name = name
        self._conn = None

    def set_sock_conn(self, conn):
        if self._conn is not None:
            self._conn.close()
        self._conn = conn

    def send_data(self, data):
        print "To Server %s Port %s, Send_data:" % (Global.gw_server_ip,self._sock_port),
        Global.dump_data(data)
        if Global.debug == 0:
            if self._conn is not None:
                if Global.NET_PROTOCOL == 'TCP':
                    try:
                        self._conn.send(data)
                    except socket.error as err:
                        if err.errno == errno.WSAECONNRESET:
                            self._conn.close()
                            print err, 'Reconnect to %s:%s' % (Global.gw_server_ip,self._sock_port)
                            sock_client = socket.socket()
                            while True:
                                try:
                                    sock_client.connect((Global.gw_server_ip,self._sock_port))
                                except socket.error as e:
                                    print 'Fail to setup socket reconnection %s:%s,try once again' % (Global.gw_server_ip,self._sock_port)
                                    time.sleep(1)
                                    continue
                                sock_client.setblocking(False)
                                self.set_sock_conn(sock_client)
                                print "set %s connection" % Global.NET_PROTOCOL
                                break
                else:
                    dst_port = (Global.gw_server_ip, self._sock_port)
                    self._conn.sendto(data,dst_port)
        else:
            Global.dump_data(data)
        pass

    def handleMessage(self, message):
        # passcmd
        self.send_data(message.getData())
        pass

    def act(self):
        try:
            #return
            if self._conn is not None:
                #max cmd payload - 54
                data = self._conn.recv(127)
                if data == '':
                    self._conn.close()
                    self._conn =  None
                    pass
                m_list = list(data)
                for item in m_list:
                    Global.data_queue.put(item)
                print 'Recved from %s to uuid %d ################################'  %(self._sock_port, self._device_uuid)
                #self.sendMessage(Global.gw_server,Message(Global.CloudtoHost_Data_EVENT, (self._device_uuid, data)))
                self.sendMessage(Global.gw_Client, Message(Global.CloudtoHost_Data_EVENT, (self._device_uuid)))
        except Exception as ex:
            #print("read sock %s failed" %self._sock_port)
            return
        pass