#! /usr/bin/python
# -*- coding: utf-8 -*-

from Actor import Actor, ActorProxy
from MessageQueue import Message
import serial
import struct
import Global
from GwAP import Gw_AP
import datetime
import pickle
import os
import string

def get_serial_by_panid(param):
    for serial_dict in Global.serials:
        t = struct.unpack("<H",serial_dict["panID"])
        if param == t[0]:
            return Global.serial_actor_map[serial_dict["name"]]
    print "could not get serial via panid"
    return None

def noneOP(self,message):
    print("noneOP for cmd %s" %message.getEvent())
    pass

# The function to handle the join req.
# Join_req Payload format: {PanID -2bytes，DevUUID-4bytes, Password-4bytes, Report Interval-2byte, Report data length – 1byte, device type – 1 byte, cap priority – 1byte }
def join_req_OP(self,message):
    print("process the join reqop")
    #cmd_name = message.getEvent()
    dev_data = {}
    cmd_name,serial_port_name, cmd_data = message.getData()
    print cmd_name, serial_port_name
    cmd_payload = cmd_data[4: -2]
    Global.dump_data(cmd_payload)

    #parse the input join_req payload
    print "cmd format", Global.hostcmd_payloads[cmd_name]
    elements = struct.unpack(Global.hostcmd_payloads[cmd_name], cmd_payload)
    dev_data['PanID'] = elements[0]
    dev_data['DevUUID'] =  elements[1]
    dev_data['Password'] = elements[2]
    dev_data['ReportInterval'] = elements[3]
    dev_data['ReportDataLength'] = elements[4]
    dev_data['DeviceType'] = elements[5]
    dev_data['Cap_Priority'] = elements[6]

    print "%04x" %dev_data['PanID'],
    print "%08x" %dev_data['DevUUID'],
    print "%08x" %dev_data['Password'],
    print "%04x" %dev_data['ReportInterval'],
    print "%02x" %dev_data['ReportDataLength'],
    print "%02x" %dev_data['DeviceType'],
    print "%02x" % dev_data['Cap_Priority']

    serial_actor, ap_node = Global.serial_actor_map[serial_port_name]
    if ap_node is None or not isinstance(ap_node, Gw_AP):
        print("get ap_node from serial_actor_map error")
        return
    if serial_actor is None or not isinstance(serial_actor, Actor):
        print("get serial_actor_proxy from serial_actor_map error")
        return

    #get the dev by the UUID, if not exist, then add it;
    dev = ap_node.getdev(dev_data['DevUUID'])
    if dev is None:
        print "dev is not added before, add the dev into the dev list"
        dev_addr = ap_node.get_free_dev_addr()
        tdma_slot = ap_node.get_tdma_slot()
        if dev_addr == 0:
            print("could not get the dev addr for this device: %x" %dev_data['DevUUID'])
            return

        if tdma_slot == -1:
            print("could not get the tdma slot for this device %x" %dev_data['DevUUID'])
            return

        dev_data['NextReportTime'] = tdma_slot
        dev_data['DevAddr'] = dev_addr
        dev_data['Status'] = 0
        dev_data['Channel'] = ap_node.channel
        ap_node.adddev(dev_data['DevUUID'], dev_data)
        dev = ap_node.getdev(dev_data['DevUUID'])
        if dev is None:
            print("add dev failed")
            return

    #send the join resp back to the AP
    # payload for the join resp is:
    # {PanID -2bytes，DevUUID-4bytes, DevAddr-2bytes, Report Interval-2byte, Next-reportime-2byte(s), Channel-1byte, CAP-priority-1 byte,
    # Report data length – 1byte, type – 1 byte }
    #'HOSTAP_JOIN_RESP':'HIHHHBBBB',
    print "%02x" %dev_data['Cap_Priority'], \
        "%04x" %dev_data['ReportInterval'],\
        "%02x" %dev_data['ReportDataLength'], \
        "%02x" %dev_data['DeviceType'], \
        "%04x" %dev['DevAddr']
    resp_payload = struct.pack('<HIHHHBBBB', dev['PanID'], dev['DevUUID'], dev['DevAddr'], dev_data['ReportInterval'], dev['NextReportTime'], dev['Channel'],
                               dev_data['Cap_Priority'],dev_data['ReportDataLength'], dev_data['DeviceType'])
    ap_node.seqno += 1
    if ap_node.seqno > Global.seq_max:
        ap_node.seqno = 0
    cmd = Global.build_hostap_cmd(ap_node.seqno, Global.hostcmds.index('HOSTAP_JOIN_RESP'), resp_payload)
    self.sendMessage(serial_actor, Message(Global.HosttoAP_CMD_EVENT,cmd))
    pass


def config_req_OP(self,message):
    cmd_name,serial_port_name, cmd_data = message.getData()
    print cmd_name, serial_port_name

    #step 1: get the apnode and  serial actor
    serial_actor, ap_node = Global.serial_actor_map[serial_port_name]
    if ap_node is None or not isinstance(ap_node, Gw_AP):
        print("get ap_node from serial_actor_map error")
        return
    if serial_actor is None or not isinstance(serial_actor, Actor):
        print("get serial_actor_proxy from serial_actor_map error")
        return

    #step 2: it is optional to config the AP pan/channel/password/seqno
    # AP config {PanID -2bytes，Channel-1byte，Password-4bytes, Beacon_Start_seqno-2bytes}

    #step 3: get the  dev list  which is loaded in the dev list file; and add all the dev to AP
    #add_dev {PanID -2bytes, DevUUID-4bytes, DevAddr-2bytes, Report Interval-2byte, Next-reportime-2byte(s), Channel-1byte, CAP-priority-1 byte,
    # status – 1byte, Report data length – 1byte, type – 1 byte, }
    dev_list = ap_node.getadddevs()
    for dev_item in dev_list.items():
        dev_data=dev_item[1]
        adddev_payload = struct.pack('<HIHHHBBBBB',dev_data['PanID'],dev_data['DevUUID'],dev_data['DevAddr'],dev_data['ReportInterval'],dev_data['NextReportTime'],
                                      dev_data['Channel'],dev_data['Cap_Priority'],dev_data['ReportDataLength'],dev_data['DeviceType'],dev_data['Status'])
        ap_node.seqno += 1
        if ap_node.seqno > Global.seq_max:
            ap_node.seqno = 0
        cmd = Global.build_hostap_cmd(ap_node.seqno, Global.hostcmds.index('HOSTAP_ADD_DEV'), adddev_payload)
        self.sendMessage(serial_actor, Message(Global.HosttoAP_CMD_EVENT,cmd))

    #step 4: config ap to start the work
    #ap_status_config # {ap-status – 1 byte (0- stop with reset, 1-stop, 2-working)}
    ap_status_config_payload = b'\x02'
    ap_node.seqno += 1
    if ap_node.seqno > Global.seq_max:
        ap_node.seqno = 0
    cmd = Global.build_hostap_cmd(ap_node.seqno, Global.hostcmds.index('HOSTAP_AP_STATUS_CONFIG'), ap_status_config_payload)
    self.sendMessage(serial_actor, Message(Global.HosttoAP_CMD_EVENT, cmd))
    pass

def report_data_OP(self, message, datatype):
    cmd_name, serial_port_name, cmd_data = message.getData()
    print cmd_name, serial_port_name

    #step 1: get the cmd payload
    cmd_payload = cmd_data[4: -2]

    Global.dump_data(cmd_payload)
    #dev_addr, data_len = struct.unpack('<HB', cmd_payload[0:3])

    dev_uuid, data_len = struct.unpack('<IB', cmd_payload[0:5])
    raw_data = cmd_payload[5:]
    print dev_uuid,data_len
    serial_actor, ap_node = Global.serial_actor_map[serial_port_name]
    if ap_node is None or not isinstance(ap_node, Gw_AP):
        print("get ap_node from serial_actor_map error")
        return
    '''
    #save the data {DevAddr – 2 bytes, datalenght -1 byte, data- variable} to dev_list_dir/UUID/date.pkl
    # {'UUID': UUID, 'DevAddr': Devaddr,'time':time, 'datalen': datalen, 'regular_data': data}

    #step 2: get the dev info by the dev_addr
    dev_data = ap_node.getdevbydevaddr(dev_addr)
    if dev_data is None:
        print "the device is not in the dev_list"
        return

    #step 3: change the dir to data_dir/UUID/
    orig_dir = os.getcwd() #save current dir
    #create the dir for this dev to save the data
    print "os.chdir(ap_node.data_dir)", ap_node.data_dir
    if not os.path.isdir(ap_node.data_dir):
        os.mkdir(ap_node.data_dir)
    os.chdir(ap_node.data_dir)
    new_dir = str(dev_data['DevUUID']).decode('utf8').encode('gbk')
    dev_data_dir = os.path.join(os.getcwd(), new_dir)
    if not os.path.isdir(dev_data_dir):
        os.mkdir(dev_data_dir)
    os.chdir(dev_data_dir)

    #step 4: prepare the data to save
    time = datetime.datetime.now()
    data_to_save = {'UUID': dev_data['DevUUID'], 'DevAddr':  dev_data['DevAddr'], 'time': time, 'datalen': data_len, datatype:  raw_data}
    print "UUID",data_to_save['UUID']
    #Global.dump_data(data_to_save['UUID'])
    #step 5: create or open the data_file, and then save the data
    data_file = str(datetime.date.today())[0:10]
    print "data_file: ", data_file
    data_fd = open(data_file.decode('utf8').encode('gbk'), 'ab')
    pickle.dump(data_to_save, data_fd, True)
    data_fd.close()

    #change back to the orig dir
    os.chdir(orig_dir)
    '''
    #support sock send
    default = None

    #sock_actor = Global.device_sock_actor_map.get(struct.pack('>I',dev_data['DevUUID']), default)
    sock_actor = Global.device_sock_actor_map.get(struct.pack('>I',dev_uuid), default)
    if sock_actor is None or not isinstance(sock_actor, Actor):
        print("get sock_actor from device_sock_actor_map error")
        return
    self.sendMessage(sock_actor, Message(Global.HosttoCloud_Data_EVENT, raw_data))

    pass

def urgent_data_OP(self, message):
    report_data_OP(self, message, 'urgent_data')
    pass

def regular_data_OP(self, message):
    report_data_OP(self, message, 'regular_data')
    pass

#this function used to reconfigurate the device
def reconfig_OP(self,message,param = 0):
    print("process the reconfiguration")
    if param == 0:
        cmd_name,serial_port_name,cmd_data = message.getData()
        serial_actor,ap_node = Global.serial_actor_map[serial_port_name];
    else:
        serial_actor,ap_node = get_serial_by_panid(param)
    if ap_node is None or not isinstance(ap_node, Gw_AP):
        print("get ap_node from serial_actor_map error")
        return
    if serial_actor is None or not isinstance(serial_actor, Actor):
        print("get serial_actor_proxy from serial_actor_map error")
        return
    #get the device by DevAddr, if not exit,return directly
    dev_data = ap_node.getdevbydevaddr(Global.dev_reconfig_data['DevAddr'])
    if dev_data is None:
        print "the device is not in the dev_list ,so it cannot be reconfigurated"
        return
    #if device with specified DevAddr is exist,the save the reconfig info. into the dev_list
    ap_node.adddev(dev_data['DevUUID'], Global.dev_reconfig_data)
    dev = ap_node.getdevbydevaddr(Global.dev_reconfig_data['DevAddr'])
    if dev is None:
        print("get the device failed")
        return
    for item in dev:
        print dev[item],
    print
    #send the reconfig. to the AP
    #Payload for the Reconfiguration is :
    #{PanID -2bytes，DevUUID-4bytes, DevAddr-2bytes, Report Interval-2byte,Next-reportime-2byte(s), Channel-1byte, CAP-priority-1 byte,
    #Report data length – 1byte, type – 1 byte
    #'HOSTAP_RECONFIG':HIHHHBBBB
    reconfig_payload = struct.pack('<HIHHHBBBB',dev['PanID'],dev['DevUUID'],dev['DevAddr'],dev['ReportInterval'],
                                   dev['NextReportTime'],dev['Channel'],dev['Cap_Priority'],dev['ReportDataLength'],dev['DeviceType'])
    ap_node.seqno +=  1
    if ap_node.seqno > Global.seq_max:
        ap_node.seqno = 0
    cmd = Global.build_hostap_cmd(ap_node.seqno,Global.hostcmds.index('HOSTAP_RECONFIG'),reconfig_payload)
    self.sendMessage(serial_actor,Message(Global.HosttoAP_CMD_EVENT,cmd))
    pass

def downlink_cmd_OP(self,message,param = 0):
    if param == 0:
        cmd_name,serial_port_name,cmd_data = message.getData()
        print cmd_name, serial_port_name
        if cmd_data is None:
            print "cmd_data is None, no cmd needed to send, return"
            return
        serial_actor,ap_node = Global.serial_actor_map[serial_port_name]
    else:
        serial_actor,ap_node = get_serial_by_panid(param)
        cmd_data = Global.downlink_cmd_info

    if ap_node is None or not isinstance(ap_node, Gw_AP):
        print("get ap_node from serial_actor_map error")
        return

    #get the downlink cmd payload
    cmd_payload = cmd_data[4:-2]
    Global.dump_data(cmd_payload)
    dev_addr  = cmd_payload[0:2]
    data_len  = cmd_payload[2]

    print dev_addr,data_len #print dev_addr and data_len
    raw_data = cmd_payload[3:]
    Global.dump_data(raw_data) #print raw_data

    ap_node.seqno += 1
    print "process the downlink_cmd,now the seq_no is"" %d" %ap_node.seqno
    if ap_node.seqno > Global.seq_max:
        ap_node.seqno = 0
    cmd_payload_s = ''.join(cmd_payload)
    cmd = Global.build_hostap_cmd(ap_node.seqno, Global.hostcmds.index('HOSTAP_DOWNLINK_CMD'), cmd_payload_s)
    self.sendMessage(serial_actor, Message(Global.HosttoAP_CMD_EVENT, cmd))
    pass

def downlink_cmd_resp_OP(self,message):
    report_data_OP(self, message, 'downlink cmd response')
    pass

def ap_config_OP(self,message,param = 0):
    print "process the ap_config cmd"
    if param == 0:
        cmd_name,serial_port_name,cmd_data = message.getData()
        print cmd_name, serial_port_name
        serial_actor,ap_node = Global.serial_actor_map[serial_port_name]
    else:
        serial_actor,ap_node = get_serial_by_panid(param)

    local_ap_config_cmd = Global.ap_config_cmd[4:-2]
    cmd_payload = struct.unpack('<HB4BH',local_ap_config_cmd)
    print cmd_payload

    ap_config_cmd_payload = local_ap_config_cmd
    ap_node.seqno += 1
    if ap_node.seqno > Global.seq_max:
        ap_node.seqno = 0
    cmd = Global.build_hostap_cmd(ap_node.seqno, Global.hostcmds.index('HOSTAP_AP_CONFIG'), ap_config_cmd_payload)
    self.sendMessage(serial_actor, Message(Global.HosttoAP_CMD_EVENT, cmd))
    pass

#this funcion used to send ap_query command
def ap_query_OP(self,message,param = 0):
    if param == 0:
        cmd_name, serial_port_name, cmd_data = message.getData()
        print cmd_name, serial_port_name
        serial_actor, ap_node = Global.serial_actor_map[serial_port_name]
    else:
        serial_actor, ap_node = get_serial_by_panid(param)

    ap_node.seqno += 1
    if ap_node.seqno > Global.seq_max:
        ap_node.seqno = 0
    cmd = Global.build_hostap_cmd(ap_node.seqno, Global.hostcmds.index('HOSTAP_AP_QUERY'), "")# no payload,so pass the NULL string.and None does not work
    self.sendMessage(serial_actor, Message(Global.HosttoAP_CMD_EVENT, cmd))
    pass

# this function used to handle ap_query_response
def ap_query_resp_OP(self,message):
    cmd_name, serial_port_name, cmd_data = message.getData()
    print cmd_name, serial_port_name
    serial_actor, ap_node = Global.serial_actor_map[serial_port_name]
    cmd_payload = cmd_data[4:-2]
    ap_panid = ''.join(cmd_payload[0:2])
    print "the status of AP_NODE is",Global.ap_status[ord(cmd_payload[9])]
    pass

#this function used to add devices when AP first start or restart
def add_dev_OP(self,message,param = 0):
    print("process the add_dev")
    if param == 0:
        cmd_name, serial_port_name, cmd_data = message.getData()
        print cmd_name, serial_port_name
        serial_actor, ap_node = Global.serial_actor_map[serial_port_name]
    else:
        serial_actor, ap_node = get_serial_by_panid(param)

    dev_list = ap_node.getadddevs()# get all devices stored in file
    for dev_item in dev_list.items():
        dev_data = dev_item[1]
        if dev_data is None:
            print "no device available"
            return
            # {PanID -2bytes, DevUUID-4bytes, DevAddr-2bytes, Report Interval-2byte,Next-reportime-2byte(s), Channel-1byte, CAP-priority-1 byte,
            # Report data length – 1byte, type – 1 byte, status – 1byte,} 9
            #'HOSTAP_ADD_DEV':"<HIHHHBBBBB",
        add_dev_payload = struct.pack('<HIHHHBBBBB',dev_data['PanID'],dev_data['DevUUID'],dev_data['DevAddr'],dev_data['ReportInterval'],dev_data['NextReportTime'],
                                      dev_data['Channel'],dev_data['Cap_Priority'],dev_data['ReportDataLength'],dev_data['DeviceType'],dev_data['Status'])
        ap_node.seqno += 1
        if ap_node.seqno > Global.seq_max:
            ap_node.seqno = 0
        cmd = Global.build_hostap_cmd(ap_node.seqno, Global.hostcmds.index('HOSTAP_ADD_DEV'), add_dev_payload)
        self.sendMessage(serial_actor, Message(Global.HosttoAP_CMD_EVENT, cmd))
    return

#this function used to change the status of sepcified Device
def status_config_OP(self,message,end_type ,param = 0):
    print("process the status_config")
    if param == 0:
        cmd_name, serial_port_name, cmd_data = message.getData()
        print cmd_name, serial_port_name
        serial_actor, ap_node = Global.serial_actor_map[serial_port_name]
    else:
        serial_actor, ap_node = get_serial_by_panid(param)
    local_status_config_cmd = Global.status_config_cmd[end_type]
    ap_node.seqno += 1
    if ap_node.seqno > Global.seq_max:
        ap_node.seqno = 0
    cmd = Global.build_hostap_cmd(ap_node.seqno, Global.hostcmds.index(end_type), local_status_config_cmd)
    self.sendMessage(serial_actor, Message(Global.HosttoAP_CMD_EVENT, cmd))
    return

def dev_status_config_OP(self,message,param = 0):
    status_config_OP(self,message,"HOSTAP_DEV_STATUS_CONFIG",param)
    return

def ap_status_config_OP(self,message,param = 0):
    status_config_OP(self,message,"HOSTAP_AP_STATUS_CONFIG",param)
    return

def dev_query_OP(self,message,dev_addr,param = 0):
    print("process the dev_query")
    if param == 0:
        cmd_name, serial_port_name, cmd_data = message.getData()
        print cmd_name, serial_port_name
        serial_actor, ap_node = Global.serial_actor_map[serial_port_name]
    else:
        serial_actor, ap_node = get_serial_by_panid(param)
    ap_node.seqno += 1
    if ap_node.seqno > Global.seq_max:
        ap_node.seqno = 0
    cmd = Global.build_hostap_cmd(ap_node.seqno, Global.hostcmds.index("HOSTAP_DEV_QUERY"), dev_addr)
    self.sendMessage(serial_actor, Message(Global.HosttoAP_CMD_EVENT, cmd))
    return

def dev_query_resp_OP(self, message, param = 0):
    print("process the dev_query_response")
    cmd_name, serial_port_name, cmd_data = message.getData()
    print cmd_name, serial_port_name
    cmd_payload = cmd_data[4: -2]
    Global.dump_data(cmd_payload)

    #parse the input Device Query Response payload
    # {PanID -2bytes, DevUUID-4bytes, DevAddr-2bytes, Report Interval-2byte,Next-reportime-2byte(s), Channel-1byte, CAP-priority-1 byte,
    # Report data length – 1byte,  type – 1 byte, status – online/offline – 1 byte, }
    dev_data = {}
    t  = ('PanID', 'DevUUID', 'DevAddr', 'ReportInterval', 'NextReportTime', 'Channel', 'Cap_Priority', 'ReportDataLength', 'DeviceType', 'Status')
    print "device config cmd format",Global.hostcmd_payloads[cmd_name]
    elements = struct.unpack(Global.hostcmd_payloads[cmd_name],cmd_payload)
    i = 0
    for key in t:
        dev_data[key] = elements[i]
        print "dev_data[%s] = " %key , "%x" % dev_data[key]
        i += 1
    print
    return

def dev_status_report_OP(self, message):
    print("process the dev_status_report")
    cmd_name, serial_port_name, cmd_data = message.getData()
    print cmd_name, serial_port_name
    cmd_payload = cmd_data[4: -2]
    Global.dump_data(cmd_payload)
    dev_addr,dev_status = struct.unpack("<HB",cmd_payload)
    print "the status of device with its addr:%d"%dev_addr,"is %s" %Global.dev_status[dev_status]
    return

def cmd_ack_OP(self,message):
    print "*"*20,"cmd ack","*"*20
    pass

hostcmd_ops = {
    'HOSTAP_JOIN_REQ':join_req_OP,###
    'HOSTAP_JOIN_RESP':noneOP,
    'HOSTAP_RECONFIG':reconfig_OP,
    'HOSTAP_DOWNLINK_CMD':downlink_cmd_OP,
    'HOSTAP_DOWNLINK_CMD_RESP':downlink_cmd_resp_OP,
    'HOSTAP_AP_CONFIG':ap_config_OP,
    'HOSTAP_AP_QUERY':ap_query_OP,
    'HOSTAP_AP_QUERY_RESP':ap_query_resp_OP,
    'HOSTAP_CONFIG_REQ':config_req_OP,###
    'HOSTAP_ADD_DEV':add_dev_OP,
    'HOSTAP_DEV_STATUS_CONFIG':dev_status_config_OP,
    'HOSTAP_AP_STATUS_CONFIG':ap_status_config_OP,
    'HOSTAP_DEV_QUERY':dev_query_OP,
    'HOSTAP_DEV_QUERY_RESP':dev_query_resp_OP,
    'HOSTAP_DEV_STATUS_REPORT':dev_status_report_OP,
    'HOSTAP_REG_DATA':regular_data_OP,###
    'HOSTAP_URGENT_DATA':urgent_data_OP,###
    'HOSTAP_URGENT_DATA_RESP':noneOP,
    'HOSTAP_CMD_ACK':cmd_ack_OP,
    'HOSTAP_CMD_ENUM_MAX':noneOP
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

        uuid_num=''
        for i in uuid:
            uuid_num +=str(ord(i)) # i 是一个字符，要将其转为整数，然后使用str转换为string
        '''
        dev = ap_node.getdev(int(uuid_num))
        print dev
        if dev is not None:
        '''
        ap_node.seqno += 1
        if ap_node.seqno > Global.seq_max:
            ap_node.seqno = 0
        #cmd_payload = struct.pack('<IB', dev['DevUUID'],len(data)) + data

        while not Global.data_queue.empty():
            qlen = Global.data_queue.qsize()
            mlist = list()
            mlist_len = 0
            print "*%d*" %qlen
            if qlen != 0 and qlen <= 113:
                while mlist_len < qlen:  #当Q的数据长度小于等于113，取实际的长度
                    ch = Global.data_queue.get()
                    #print "*%d*" % Global.data_queue.qsize(),
                    mlist.append(ch)
                    mlist_len += 1
            elif qlen > 113:
                while mlist_len < 113: #当Q的数据长度大于113，则取 113个字节
                    ch = Global.data_queue.get_nowait()
                    #print "*%d*" %Global.data_queue.qsize(),
                    print ch,
                    mlist.append(ch)
                    mlist_len += 1
            else:
                break
            print "\n"
            data_t = ''.join(mlist)
            cmd_payload = struct.pack('<IB', int(uuid_num), len(data_t)) + data_t
            cmd = Global.build_hostap_cmd(ap_node.seqno, Global.hostcmds.index('HOSTAP_DOWNLINK_CMD'), cmd_payload)
            self.sendMessage(serial_actor, Message(Global.HosttoAP_CMD_EVENT, cmd))
        print "no data in Global.data_queue"
        return
    pass

class Gw_Server(Actor):
    def __init__(self, name = 'Gw_server'):
        super(Gw_Server, self).__init__(name)
        pass

    def handleMessage(self, message):
        #handler meassage and send message if needed
        #serial_id, data = message.getData()
        # self.sendMessage(serial_actor_map(serial_id), Message("GW_DATA", data))
        event_name = message.getEvent()
        print event_name
        if event_name == Global.APtoHOST_CMD_EVENT:
            cmdname, serial_id, data = message.getData()
            hostcmd_ops.get(cmdname)(self, message)
        else:
            if event_name == Global.CloudtoHost_Data_EVENT:
                uuid = message.getData()
                Global.dump_data(uuid)
                SendSockDataToAP(self, uuid, None)
        pass