#! /usr/bin/python
# -*- coding: utf-8 -*-

from Actor import Actor
from MessageQueue import Message
import serial
import struct
import Global
import thread
import socket
import time
from GwSerial import SerialThread
from GwClient import Gw_Client
from GwAP import Gw_AP
from GwSock import Gw_Sock

def start_socket(port, dev_sock_actor):
    ip_port = ('192.168.100.142', port)
    if Global.NET_PROTOCOL == 'TCP':
        sock_client = socket.socket()
        #sock_client.bind(ip_port)  #将client端也绑定固定的port
    else:
        sock_client = socket.socket(type=socket.SOCK_DGRAM) #SOCK_DGRAM 2
    dst_port=(Global.gw_server_ip,port)
    while True:
        if Global.NET_PROTOCOL == 'TCP':
            try:
                sock_client.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
                sock_client.connect(dst_port)
                # 等待链接,阻塞，直到渠道链接 conn打开一个新的对象 专门给当前链接的客户端 addr是ip地址
            except socket.error as e:
                print 'Fail to setup socket connection %s:%s,try once again' %dst_port
                time.sleep(1)
                continue

            #sock_client.sendto("123455", Global.gw_server_ip)
        sock_client.setblocking(False)
        dev_sock_actor.set_sock_conn(sock_client)
        print "set %s connection" %Global.NET_PROTOCOL
        break

class GW_MAIN(Actor):
    def __init__(self):
        super(GW_MAIN, self).__init__('GW_Main')
        Global.gw_Client = Gw_Client.start()
        gw_client_proxy = Global.gw_Client.proxy()
        for serial_item in Global.serials:  #serial_item['name'] 和ap_node serial_thread的绑定，并且和gw_client_proxy关联
            ap_node = Gw_AP(serial_item["name"], serial_item["channel"], serial_item["password"],
                            serial_item["start_seqno"], serial_item["dev_list_file"], serial_item["data_dir"])
            try:
                serial_thread = SerialThread.start(serial_item["name"])
            except Exception as err:
                print "Error:%s" % err
                return
            serial_thread_proxy = serial_thread.proxy()
            Global.serial_actor_map[serial_item["name"]] = (serial_thread, ap_node)
            serial_thread_proxy.connect(gw_client_proxy)
            gw_client_proxy.connect(serial_thread_proxy)

        for device_item in Global.device_sockets: #uuid 和 dev_sock的绑定，并且和gw_client_proxy关联
            dev_sock = Gw_Sock.start(device_item["name"], device_item["UUID"], device_item["socket_port"])
            dev_sock_proxy = dev_sock.proxy()
            Global.device_sock_actor_map[device_item["UUID"]] = dev_sock
            dev_sock_proxy.connect(gw_client_proxy)
            gw_client_proxy.connect(dev_sock_proxy)
            thread.start_new_thread(start_socket, (device_item["socket_port"],dev_sock,))#开启新的线程，并执行start_socket,同时传入参数port和dev_sock_actor
        pass

if __name__ == '__main__':
    GW_MAIN.start().proxy()
