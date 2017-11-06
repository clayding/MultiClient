#! /usr/bin/python
# -*- coding: utf-8 -*-

from Actor import Actor, ActorProxy
from MessageQueue import Message
from GwAP import Gw_AP

import serial
import struct
import Global
import pickle
import os
import string


def report_data_OP(self, message, datatype):
    cmd_name, serial_port_name, cmd_data = message.getData()
    print cmd_name, serial_port_name

    #step 1 get the payload
    cmd_payload = cmd_data[4:-2]

    Global.dump_data(cmd_payload)
    dev_uuid, data_len = struct.unpack('IB',cmd_payload[:5])

    raw_data = cmd_payload[5:]
    print "uuid %d,Raw_data" %dev_uuid,
    Global.dump_data(raw_data)
    uuid_range=((dev_uuid-1)/400 +1) *400

    print 'uuid_range %d' %uuid_range

    serial_actor, ap_node = Global.serial_actor_map[serial_port_name]

    if ap_node is None or not isinstance(ap_node, Gw_AP):
        print("get ap_node from serial_actor_map error")
        return
    # support sock send
    default = None
    #sock_actor = Global.device_sock_actor_map.get(struct.pack('>I', dev_uuid), default)
    sock_actor = Global.device_sock_actor_map.get(uuid_range, default)
    if sock_actor is None or not isinstance(sock_actor, Actor):
        print("get sock_actor from device_sock_actor_map error")
        return
    self.sendMessage(sock_actor, Message(Global.HosttoCloud_Data_EVENT, raw_data))
    pass

def handle_regular_data(self,message):
    report_data_OP(self,message,'regular_data')
    pass

hostcmd_ops = {

    'HOSTAP_REG_DATA':handle_regular_data,###
    'HOSTAP_URGENT_DATA':None,###
}


def SendSockDataToAP(self, uuid, data):
    for serial_actor_item in Global.serial_actor_map.items():
        serial_actor, ap_node = serial_actor_item[1]
        if ap_node is None or not isinstance(ap_node, Gw_AP):
            print("get ap_node from serial_actor_map error")
            return
        if serial_actor is None or not isinstance(serial_actor, Actor):
            print("get serial_actor_proxy from serial_actor_map error")
            return

        '''uuid_num = ''
        for i in uuid:
            uuid_num += str(ord(i))  # i 是一个字符，要将其转为整数，然后使用str转换为string '''
        '''
        dev = ap_node.getdev(int(uuid_num))
        print dev
        if dev is not None:
        '''
        ap_node.seqno += 1
        if ap_node.seqno > Global.seq_max:
            ap_node.seqno = 0
        # cmd_payload = struct.pack('<IB', dev['DevUUID'],len(data)) + data

        while not Global.data_queue.empty():
            qlen = Global.data_queue.qsize()
            mlist = list()
            mlist_len = 0
            print "Raw data lenght :%d" %qlen
            if qlen != 0 and qlen <= 113:
                while mlist_len < qlen:  # 当Q的数据长度小于等于113，取实际的长度
                    ch = Global.data_queue.get()
                    # print "*%d*" % Global.data_queue.qsize(),
                    mlist.append(ch)
                    mlist_len += 1
            elif qlen > 113:
                while mlist_len < 113:  # 当Q的数据长度大于113，则取 113个字节
                    ch = Global.data_queue.get_nowait()
                    # print "*%d*" %Global.data_queue.qsize(),
                    print ch,
                    mlist.append(ch)
                    mlist_len += 1
            else:
                break
            data_t = ''.join(mlist)
            #cmd_payload = struct.pack('<IB', int(uuid_num), len(data_t)) + data_t
            cmd_payload = struct.pack('<IB', uuid, len(data_t)) + data_t
            cmd = Global.build_hostap_cmd(ap_node.seqno, Global.hostcmds.index('HOSTAP_DOWNLINK_CMD'), cmd_payload)
            self.sendMessage(serial_actor, Message(Global.HosttoAP_CMD_EVENT, cmd))
        print "no data in Global.data_queue"
        return
    pass

class Gw_Client(Actor):
    def __init__(self,name = 'Gw_client'):
        super(Gw_Client, self).__init__(name)
        pass

    def handleMessage(self, message):
        event_name = message.getEvent()
        print event_name

        if event_name == Global.APtoHOST_CMD_EVENT:
            cmdname, serial_id,data = message.getData()
            hostcmd_ops.get(cmdname)(self,message)
        else:
            if event_name == Global.CloudtoHost_Data_EVENT:
                uuid = message.getData()
                SendSockDataToAP(self,uuid,None)
        pass

