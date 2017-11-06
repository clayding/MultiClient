#! /usr/bin/python
# -*- coding: utf-8 -*-

#serials = ["ttyUSB0", "ttyUSB1"]
from MessageQueue import Message, Event
from Queue import Queue
from crc16xmodem import crc
import struct

debug = 0

NET_PROTOCOL = 'TCP'  #TCP or UDP,通过这个变量可控制使用TCP还是UDP进行通讯

data_queue = Queue(maxsize = 1024)
serials = [
    #{'name':"/dev/ttyUSB0", 'panID': b'\x00\x00', 'channel': 1, 'password':b'\x00\x00\x00\x00', 'start_seqno': 0, 'dev_list_file': "dev_list_file0", 'data_dir': "data_dir0"},
    #{'name':"/dev/ttyUSB1", 'panID': b'\x00\x00', 'channel': 1, 'password':b'\x00\x00\x00\x00', 'start_seqno': 0, 'dev_list_file': "dev_list_file1", 'data_dir': "data_dir1"},
    {'name':"COM9", 'panID': b'\x01\x00', 'channel': 1, 'password':b'\x00\x00\x00\x00', 'start_seqno': 0, 'dev_list_file': "dev_list_file1", 'data_dir': "data_dir1"}
]
# {PanID -2bytes, DevUUID-4bytes, DevAddr-2bytes, Report Interval-2byte,Next-reportime-2byte(s), Channel-1byte, CAP-priority-1 byte,
# Report data length – 1byte, type – 1 byte }
dev_reconfig_data = {'PanID':1,'DevUUID':1,'DevAddr':1,'ReportInterval':2,'NextReportTime':0,'Channel': 1,'Cap_Priority':1,
                     'ReportDataLength':0,'DeviceType':0,'Status':0}
# downlink_cmd
downlink_cmd_info = [b'\x7f', b'\x7f', b'\x00', b'\x0f', b'\x01', b'\x00', b'\x05', b'\x11', b'\x12', b'\x13',b'\x14', b'\x15', b'\x00', b'\x00']

#ap_config_cmd
#{PanID -2bytes，Channel-1byte，Password-4bytes, Beacon_Start_seqno-2bytes}
ap_config_cmd = b'\x7f\x7f\x00\x0f' + b'\x01\x00' +b'\x01' + b'\x00\x00\x00\x00' + b'\x01\x00'+ b'\x00\x00'

#dev_status_config and ap_status_config
#{DevAddr-2bytes, status– 1 byte (0-offline, 1-online, 2 –del)}
#{ap-status – 1 byte (0- stop with reset, 1-stop, 2-working)}
status_config_cmd ={ 'HOSTAP_DEV_STATUS_CONFIG': b'\x7f\x7f\x00\x0f' + b'\x01\x00' + b'\x01'+ b'\x00\x00',
                     'HOSTAP_AP_STATUS_CONFIG' : b'\x7f\x7f\x00\x0f' + b'\x01'+ b'\x00\x00'}

'''###############################################################
            端口号     id分配
            5001      0001-0400
            5002      0401-0800
##################################################################'''

id_edge=400 #id的分割，每400对应一个server端的端口号

device_sockets = [
    #{'name': "device1", 'UUID': b'\x00\x00\x00\x01', 'socket_port': 10001},
    #{'name': "device2", 'UUID': b'\x00\x00\x00\x02', 'socket_port': 10002},
    {'name': "device1", 'UUID': id_edge, 'socket_port': 5001}, #socket_port目前是server的port
    {'name': "device2", 'UUID': id_edge*2, 'socket_port': 5002},
    #{'name': "device3", 'UUID': b'\x00\x00\x00\x03', 'socket_port': 10003},
    #{'name': "device4", 'UUID': b'\x00\x00\x00\x04', 'socket_port': 10004},
]

device_sock_actor_map = {}
serial_actor_map = {}
HOSTAP_CMD_MINIMUM_SIZE = 8
MINIMAL_REPORT_INTERVAL = 300 #5mins
BEACON_INTERVAL = 2
TDMA_PER_BEACON = 6
gw_server_ip ='192.168.100.142'
gw_Client = ''
seq_max = 255
ap_status = {0:"idle",1:"working"}
dev_status = {0:"offline",1:"online"}

hostcmds = ['HOSTAP_JOIN_REQ',
            'HOSTAP_JOIN_RESP',
           'HOSTAP_RECONFIG',
           'HOSTAP_DOWNLINK_CMD',
           'HOSTAP_DOWNLINK_CMD_RESP',
           'HOSTAP_AP_CONFIG',
           'HOSTAP_AP_QUERY',
           'HOSTAP_AP_QUERY_RESP',
           'HOSTAP_CONFIG_REQ',
           'HOSTAP_ADD_DEV',
           'HOSTAP_DEV_STATUS_CONFIG',
           'HOSTAP_AP_STATUS_CONFIG',
           'HOSTAP_DEV_QUERY',
           'HOSTAP_DEV_QUERY_RESP',
           'HOSTAP_DEV_STATUS_REPORT',
           'HOSTAP_REG_DATA',
           'HOSTAP_URGENT_DATA',
           'HOSTAP_URGENT_DATA_RESP',
           'HOSTAP_CMD_ACK']
           #'HOSTAP_CMD_ENUM_MAX']

hostcmd_payloads = {
            #{PanID -2bytes，DevUUID-4bytes, Password-4bytes, Report Interval-2byte, Report data length – 1byte, device type – 1 byte, cap priority – 1byte }
            'HOSTAP_JOIN_REQ': '<HIIHBBB',
            #{PanID -2bytes，DevUUID-4bytes, DevAddr-2bytes, Report Interval-2byte, Next-reportime-2byte(s), Channel-1byte, CAP-priority-1 byte,
            # Report data length – 1byte, type – 1 byte }
           'HOSTAP_JOIN_RESP':'<HIHHHBBBB',
            #{PanID -2bytes，DevUUID-4bytes, DevAddr-2bytes, Report Interval-2byte,Next-reportime-2byte(s), Channel-1byte, CAP-priority-1 byte,
            # Report data length – 1byte, type – 1 byte }
           'HOSTAP_RECONFIG':'<HIHHHBBBB',
            #{uuid-4bytes, length – 1 byte, DownlinkData - variable}
           'HOSTAP_DOWNLINK_CMD': 255,
            #{Devaddr-2bytes, length – 1 byte, DownlinkDataResp - variable}
           'HOSTAP_DOWNLINK_CMD_RESP': 255,
            #{PanID -2bytes，Channel-1byte，Password-4bytes, Beacon_Start_seqno-2bytes}  5
           'HOSTAP_AP_CONFIG':'<HB4BH',
            #none 6
           'HOSTAP_AP_QUERY': 0,
            #{PanID -2bytes，Channel-1byte，Password-4bytes, Beacon_Start_seqno-2bytes, status – 1 byte} 7
           'HOSTAP_AP_QUERY_RESP':'<HB4BHB',
            #none 8
           'HOSTAP_CONFIG_REQ': 0,
            #{PanID -2bytes, DevUUID-4bytes, DevAddr-2bytes, Report Interval-2byte,Next-reportime-2byte(s), Channel-1byte, CAP-priority-1 byte,
            # Report data length – 1byte, type – 1 byte, status – 1byte,} 9
           'HOSTAP_ADD_DEV':"<HIHHHBBBBB",
            #{DevAddr-2bytes, status– 1 byte (0-offline, 1-online, 2 –del)} 10
           'HOSTAP_DEV_STATUS_CONFIG':'<HB',
            #{ap-status – 1 byte (0- stop with reset, 1-stop, 2-working)} 11
           'HOSTAP_AP_STATUS_CONFIG':'<B',
            #{DevAddr-2bytes} 12
           'HOSTAP_DEV_QUERY':'<H',
            #{PanID -2bytes, DevUUID-4bytes, DevAddr-2bytes, Report Interval-2byte, Next-reportime-2byte(s), Channel-1byte, CAP-priority-1 byte,
            #Report data length – 1byte,  type – 1 byte, status – online/offline – 1 byte, } 13
           'HOSTAP_DEV_QUERY_RESP':'<HIHHHBBBBB',
            #{DevAddr-2bytes, status– 1 byte (0-offline, 1-online)} 14
           'HOSTAP_DEV_STATUS_REPORT':'<HB',
            #{DevAddr – 2 bytes, datalenght -1 byte, data- variable} 15
           'HOSTAP_REG_DATA': 255,
            #{DevAddr – 2 bytes, datalenght -1 byte, data- variable} 16
           'HOSTAP_URGENT_DATA': 255,
            #{DevAddr – 2 bytes, sleep-time – 2 bytes} 17
           'HOSTAP_URGENT_DATA_RESP':'<HH',
            #{cmdid -  1 byte, status – 1 byte (1 success, 0 fail)}
           'HOSTAP_CMD_ACK':'<BB'
}

def build_hostap_cmd(seqno, cmdid, cmd_payload):
    cmd_data = b'\x7f\x7f'  + chr(seqno) + chr(cmdid) + cmd_payload
    #crc = b'\x00\x00'
    crc_t =crc(cmd_data)
    mcrc = struct.pack("<H",crc_t)
    cmd_data += mcrc
    data_len = len(cmd_data)
    print "Total data lenght: %d >>>>>>>>" %data_len ,
    i = 0
    while i < data_len:
        print "%02x" % ord(cmd_data[i]),
        i += 1
    print
    return cmd_data

def dump_data(data):
    data_len = len(data)
    i = 0
    while i < data_len:
        print  "%02x" % ord(data[i]),
        i += 1
    print

class APtoHOST_CMD_EVENT(Event): pass
class HosttoAP_CMD_EVENT(Event): pass
class CloudtoHost_Data_EVENT(Event): pass
class HosttoCloud_Data_EVENT(Event): pass
