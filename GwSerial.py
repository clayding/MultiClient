#! /usr/bin/python
# -*- coding: utf-8 -*-

from Actor import Actor
from MessageQueue import Message
import serial
import struct
import Global
import GwServer

virtual_inputs = [b'\x7f\x7f\x00\x0f' + b'\x00\x01\x02\x03\x04' + b'\x00\x00'] #regular_data
                  #[b'\x7f\x7f\x00\x00' + b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x10\x11\x12\x13\x14' + b'\x00\x00']#join req
                  #[b'\x7f\x7f\x08\x00' + b'\x00\x00']#AP_Config_req
                  #[b'\x7f\x7f\x10\x00' + b'\x00\x01\x02\x03\x04' + b'\x00\x00'] #urgent_data
                  #[b'\x7f\x7f\x0f\x00' + b'\x00\x01\x02\x03\x04' + b'\x00\x00'] #regular_data

class SerialThread(Actor):
    def __init__(self, serial_port):
        super(SerialThread, self).__init__(serial_port)
        self._serialport = serial_port
        self._serialdata = ""
        if Global.debug != 0:
            self.virtual_inputs_index = 0

        # self._gw_server_actor = actor
        try:
            if Global.debug == 0:
                self._serialfd = serial.Serial(serial_port, baudrate=9600,bytesize=8,parity='E',stopbits=1,timeout=0.003)
                print("SerialThread init %s" %serial_port)
        except Exception as ex:
            print("open serial %s failed" %serial_port)
            raise

    def write_data(self, data):
        print("To serial_id  %s, write_data done*************************" %self._serialport)

        if Global.debug == 0:
            self._serialfd.write(data)
        else:
            Global.dump_data(data)
        pass

    def handleMessage(self, message):
        # passcmd
        self.write_data(message.getData())
        pass

    def parseSerialData(self):
        ##handle the serial data
        # #send the cmd to the gw as message
        data_len = len(self._serialdata)
        if data_len > 0:
            Global.dump_data(self._serialdata)
            #print str(self._serialdata)
        else:
            return
        start_pos = self._serialdata.find(b'\x7f\x7f')
        if start_pos == -1:
            if self._serialdata[-1] == b'\x7f':
                self._serialdata = b'\x7f'
                return
            self._serialdata = ''
            return

        #print start_pos
        self._serialdata = self._serialdata[start_pos: ]

        data_len = len(self._serialdata)
        print "Input data lenght:", data_len ,
        if data_len < Global.HOSTAP_CMD_MINIMUM_SIZE:
            return

        cmd_id = ord(self._serialdata[3]) #ord()将字符转换为ascii码
        print "Cmd_id:%d >>>>>>>>>>>>>>>>>" %cmd_id,
        if cmd_id >= len(Global.hostcmds):
            print("cmd_id is %d, not supported" %cmd_id)
            self._serialdata = self._serialdata[1:]
            return

        cmd_name = Global.hostcmds[cmd_id]
        payload_len = 0
        #print cmd_name, Global.hostcmd_payloads[cmd_name]
        if Global.hostcmd_payloads[cmd_name] == 255:
            if data_len < Global.HOSTAP_CMD_MINIMUM_SIZE + 2 + 2:
                print("need more input data")
                return
            payload_len = ord(self._serialdata[Global.HOSTAP_CMD_MINIMUM_SIZE]) + 3
        else:
            if Global.hostcmd_payloads[cmd_name] == 0:
                payload_len = 0
            else:
                payload_len = struct.calcsize(Global.hostcmd_payloads[cmd_name])

        print  'Payload_len:%d' % payload_len,

        if data_len - Global.HOSTAP_CMD_MINIMUM_SIZE < payload_len:
            print data_len, Global.HOSTAP_CMD_MINIMUM_SIZE, payload_len
            print("need more input data")
            return

        cmd_data = self._serialdata[0: payload_len + Global.HOSTAP_CMD_MINIMUM_SIZE +1 ]
        Global.dump_data(cmd_data)
        #check fcs here

        self.sendMessage(Global.gw_Client, Message(Global.APtoHOST_CMD_EVENT, (cmd_name, self._serialport, cmd_data)))
        self._serialdata = self._serialdata[payload_len + Global.HOSTAP_CMD_MINIMUM_SIZE: ]

        return


    def act(self):
        #print("serial_id is %s, read_data" %self._serialport)
        # read serial data; pass serial data and send the message to gw_server if needed
        count = 0
        if Global.debug == 0:
            s = self._serialfd.read(1)
        else:
            if self.virtual_inputs_index < len(virtual_inputs) and count < len(virtual_inputs[self.virtual_inputs_index]):
                s = virtual_inputs[self.virtual_inputs_index][count]
            else:
                s = None
                return
        while (s):
            #print "%02x" %ord(s)
            self._serialdata += s

            count += 1
            if count > 128:
                print("continue read 128 byte already, break for message handle")
                break

            if Global.debug == 0:
                s = self._serialfd.read(1)
            else:
                if count < len(virtual_inputs[self.virtual_inputs_index]):
                    s = virtual_inputs[self.virtual_inputs_index][count]
                else:
                    s = None

        self.parseSerialData()

        if Global.debug != 0:
            self.virtual_inputs_index += 1
        pass