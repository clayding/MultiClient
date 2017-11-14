#! /usr/bin/python
# -*- coding: utf-8 -*-

import Global
import os
import pickle

class Gw_AP():
    channel = 0
    panid = b'\x00\x00'
    seqno = 0
    def __init__(self, apName, channel, password, start_seqno, dev_list_file, data_dir):
        self.name = apName
        self.channel = channel
        self.password = password
        self.start_seqno = start_seqno
        self.dev_list_file = dev_list_file.decode('utf8') #get the dev List file, which store the dev list of this ap
        self.data_dir = data_dir.decode('utf8') #get the data dir, which will be used to store the regular/urgent data
        # self.dev_list = { uuid:devdata, ...} //
        self.dev_list = {}
        # self.free_dev_addrs = [1 ...]
        self.free_dev_addrs = range(1, 1 << 16)
        # self.tdma_slots = [6, 6,...]
        self.tdma_slot_max = Global.MINIMAL_REPORT_INTERVAL / Global.BEACON_INTERVAL
        self.tdma_slots = [Global.TDMA_PER_BEACON for i in range(self.tdma_slot_max)]
        self.tdma_slot_index = 0

        if not os.path.isdir(self.data_dir):
            os.mkdir(self.data_dir)

        if not os.path.isfile(self.dev_list_file):
            print self.dev_list_file, "file doesn't exist"
            return

        #load the dev list from the file
        dev_list_fd = open(self.dev_list_file, 'rb')
        self.dev_list = pickle.load(dev_list_fd)
        dev_list_fd.close()

        for dev_item in self.dev_list.items():
            dev_data = dev_item[1]
            tdma_slot = dev_data['NextReportTime']
            self.free_dev_addrs.remove(dev_data['DevAddr'])
            self.tdma_slots[tdma_slot / self.tdma_slot_max] = self.tdma_slots[tdma_slot / self.tdma_slot_max] - 1

    #function to get the free dev addr
    def get_free_dev_addr(self):
        if len(self.free_dev_addrs) == 0:
            return 0  # no available dev addr
        dev_addr = self.free_dev_addrs[0]
        # del self.free_dev_addrs[0]
        return dev_addr

    #function to return the dev_addr
    def put_free_dev_addr(self, dev_addr):
        self.free_dev_addrs.append(dev_addr)
        pass

    #function to get the tdma slot
    def get_tdma_slot(self):
        for i in range(self.tdma_slot_index, self.tdma_slot_max):
            if self.tdma_slots[i] > 0:
                # self.tdms_slots[i] = self.tdms_slots[i] -1
                return i
        for i in range(0, self.tdma_slot_index):
            if self.tdma_slots[i] > 0:
                # self.tdms_slots[i] = self.tdms_slots[i] -1
                return i
        return -1  # no available slot

    #function to return the tdma_slot
    def put_tdma_slot(self, tdma_slot):
        self.tdma_slots[tdma_slot / self.tdma_slot_max] = self.tdma_slots[tdma_slot / self.tdma_slot_max] + 1

    #function to add the dev to dev_list, normally called by join_req op
    # {PanID -2bytes, DevUUID-4bytes, DevAddr-2bytes, Report Interval-2byte,Next-reportime-2byte(s), Channel-1byte, CAP-priority-1 byte,
    # status – 1byte, Report data length – 1byte, type – 1 byte,Password-4bytes }
    def adddev(self, uuid, dev_data):

        flag = 0
        if dev_data['DevUUID'] in self.dev_list:
            print("dev duplicate")
            pass

        if dev_data['DevAddr'] not in self.free_dev_addrs:
            print("Devaddr duplicate")
            flag = 1
            pass

        if self.tdma_slots[dev_data['NextReportTime'] / self.tdma_slot_max] <= 0:
            print("TDMA slot not available/n")
            pass

        self.dev_list[dev_data['DevUUID']] = dev_data
        if flag != 1:
            self.free_dev_addrs.remove(dev_data['DevAddr'])
        self.tdma_slots[dev_data['NextReportTime'] / self.tdma_slot_max] = self.tdma_slots[dev_data['NextReportTime'] / self.tdma_slot_max] - 1
        self.tdma_slot_index = self.tdma_slot_index - 1

        #save the new dev_list to the file
        print "add dev, dump to dev_list_file:", self.dev_list_file
        output = open(self.dev_list_file, 'wb')
        pickle.dump(self.dev_list, output)
        output.close()

        pass

    #function to del the dev
    def deldev(self, uuid):
        self.put_free_dev_addr(self.dev_list[uuid]['DevAddr'])
        self.put_tdma_slot(self.dev_list[uuid]['DevAddr'])
        del self.dev_list[uuid]

        #save the new dev_list to the file
        output = open('self.dev_list_file', 'wb')
        pickle.dump(self.dev_list, output)
        output.close()
        pass

    #get the dev by uuid; return none if the dev not exist
    def getdev(self, uuid):
        if uuid not in self.dev_list:
            return None
        else:
            return self.dev_list[uuid]

    #get all the devcies
    def getadddevs(self):
        return self.dev_list;

    #get the dev by dev_addr
    def getdevbydevaddr(self, dev_addr):
        if dev_addr not in self.free_dev_addrs:
            for dev_item in self.dev_list.items():
                dev_data = dev_item[1]
                if dev_addr == dev_data['DevAddr']:
                    return dev_data

        return None