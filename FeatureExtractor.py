#Check if cython code has been compiled
import os
import subprocess
import sys
from collections import OrderedDict
import json

use_extrapolation=False #experimental correlation code
if use_extrapolation:
    print("Importing AfterImage Cython Library")
    if not os.path.isfile("AfterImage.c"): #has not yet been compiled, so try to do so...
        cmd = "python setup.py build_ext --inplace"
        subprocess.call(cmd,shell=True)
#Import dependencies
import netStat as ns
import csv
import numpy as np
print("Importing Scapy Library")
from scapy.all import *
import os.path
import platform
import subprocess

#Extracts Kitsune features from given pcap file one packet at a time using "get_next_vector()"
# If wireshark is installed (tshark) it is used to parse (it's faster), otherwise, scapy is used (much slower).
# If wireshark is used then a tsv file (parsed version of the pcap) will be made -which you can use as your input next time
class FE:
    def __init__(self,file_path,limit=np.inf):
        self.path = file_path
        self.limit = limit
        self.parse_type = None #unknown
        self.curPacketIndx = 0
        self.tsvin = None #used for parsing TSV file
        self.scapyin = None #used for parsing pcap with scapy

        ### Prep pcap ##
        self.__prep__()

        ### Prep Feature extractor (AfterImage) ###
        maxHost = 100000000000
        maxSess = 100000000000
        self.nstat = ns.netStat(np.nan, maxHost, maxSess)

    def _get_tshark_path(self):
        if platform.system() == 'Windows':
            return 'C:\Program Files\Wireshark\\tshark.exe'
        else:
            system_path = os.environ['PATH']
            for path in system_path.split(os.pathsep):
                filename = os.path.join(path, 'tshark')
                if os.path.isfile(filename):
                    return filename
        return ''

    def __prep__(self):
        ### Find file: ###
        if not os.path.isfile(self.path):  # file does not exist
            print("File: " + self.path + " does not exist")
            raise Exception()

        ### check file type ###
        type = self.path.split('.')[-1]

        self._tshark = self._get_tshark_path()
        ##If file is TSV (pre-parsed by wireshark script)
        if type == "tsv":
            self.parse_type = "tsv"

        ##If file is pcap
        elif type == "pcap" or type == 'pcapng':
            # Try parsing via tshark dll of wireshark (faster)
            if os.path.isfile(self._tshark):
                self.pcap2tsv_with_tshark()  # creates local tsv file
                self.path += ".tsv"
                self.parse_type = "tsv"
            else: # Otherwise, parse with scapy (slower)
                print("tshark not found. Trying scapy...")
                self.parse_type = "scapy"
        else:
            print("File: " + self.path + " is not a tsv or pcap file")
            raise Exception()

        ### open readers ##
        if self.parse_type == "tsv":
            maxInt = sys.maxsize
            decrement = True
            while decrement:
                # decrease the maxInt value by factor 10
                # as long as the OverflowError occurs.
                decrement = False
                try:
                    csv.field_size_limit(maxInt)
                except OverflowError:
                    maxInt = int(maxInt / 10)
                    decrement = True

            print("counting lines in file...")
            num_lines = sum(1 for line in open(self.path))
            print("There are " + str(num_lines) + " Packets.")
            self.limit = min(self.limit, num_lines-1)
            self.tsvinf = open(self.path, 'rt', encoding="utf8")
            self.tsvin = csv.reader(self.tsvinf, delimiter='\t')
            row = self.tsvin.__next__() #move iterator past header

        else: # scapy
            print("Reading PCAP file via Scapy...")
            self.scapyin = rdpcap(self.path)
            self.limit = len(self.scapyin)
            print("Loaded " + str(len(self.scapyin)) + " Packets.")

    def get_next_vector(self):
        if self.curPacketIndx == self.limit:
            if self.parse_type == 'tsv':
                self.tsvinf.close()
            return []

        ### Parse next packet ###
        if self.parse_type == "tsv":
            row = self.tsvin.__next__()
            IPtype = np.nan
            timestamp = row[0]
            framelen = row[1]
            srcIP = ''
            dstIP = ''
            if row[4] != '':  # IPv4
                srcIP = row[4]
                dstIP = row[5]
                IPtype = 0
            elif row[17] != '':  # ipv6
                srcIP = row[17]
                dstIP = row[18]
                IPtype = 1
            srcproto = row[6] + row[8]  # UDP or TCP port: the concatenation of the two port strings will will results in an OR "[tcp|udp]"
            dstproto = row[7] + row[9]  # UDP or TCP port
            srcMAC = row[2]
            dstMAC = row[3]
            if srcproto == '':  # it's a L2/L1 level protocol
                if row[12] != '':  # is ARP
                    srcproto = 'arp'
                    dstproto = 'arp'
                    srcIP = row[14]  # src IP (ARP)
                    dstIP = row[16]  # dst IP (ARP)
                    IPtype = 0
                elif row[10] != '':  # is ICMP
                    srcproto = 'icmp'
                    dstproto = 'icmp'
                    IPtype = 0
                elif srcIP + srcproto + dstIP + dstproto == '':  # some other protocol
                    srcIP = row[2]  # src MAC
                    dstIP = row[3]  # dst MAC
                    # to solve Configuration Test Protocol bug
                    if srcIP == dstIP:
                        dstIP = dstIP+"ctp"                    
            # if self.curPacketIndx == 45 :
            #     print ('srcproto', srcproto, srcIP, dstIP)
            if srcproto == '' :
                srcproto = 'null'
            if dstproto == '' :
                dstproto = 'null'

        elif self.parse_type == "scapy":
            packet = self.scapyin[self.curPacketIndx]
            IPtype = np.nan
            timestamp = packet.time
            framelen = len(packet)
            if packet.haslayer(IP):  # IPv4
                srcIP = packet[IP].src
                dstIP = packet[IP].dst
                IPtype = 0
            elif packet.haslayer(IPv6):  # ipv6
                srcIP = packet[IPv6].src
                dstIP = packet[IPv6].dst
                IPtype = 1
            else:
                srcIP = ''
                dstIP = ''

            if packet.haslayer(TCP):
                srcproto = str(packet[TCP].sport)
                dstproto = str(packet[TCP].dport)
            elif packet.haslayer(UDP):
                srcproto = str(packet[UDP].sport)
                dstproto = str(packet[UDP].dport)
            else:
                srcproto = ''
                dstproto = ''

            srcMAC = packet.src
            dstMAC = packet.dst
            if srcproto == '':  # it's a L2/L1 level protocol
                if packet.haslayer(ARP):  # is ARP
                    srcproto = 'arp'
                    dstproto = 'arp'
                    srcIP = packet[ARP].psrc  # src IP (ARP)
                    dstIP = packet[ARP].pdst  # dst IP (ARP)
                    IPtype = 0
                elif packet.haslayer(ICMP):  # is ICMP
                    srcproto = 'icmp'
                    dstproto = 'icmp'
                    IPtype = 0
                elif srcIP + srcproto + dstIP + dstproto == '':  # some other protocol
                    srcIP = packet.src  # src MAC
                    dstIP = packet.dst  # dst MAC
                    # to solve Configuration Test Protocol bug
                    if packet.src == packet.dst:
                        dstIP = packet.dst+"ctp"  # dst MAC
            if srcproto == '' :
                srcproto = 'null'
            if dstproto == '' :
                dstproto = 'null'

        else:
            return []

        self.curPacketIndx = self.curPacketIndx + 1
        #print(timestamp)

        #print (' >>>> counter',self.curPacketIndx)
        # if self.curPacketIndx > np.Inf :
        if self.curPacketIndx > self.limit :
            print ("SHOULD NOT EXIT HERE...")
            self.evaluate_stats()
            self.export_flow_time_values()
            sys.exit()
            
        return self.nstat.updateGetStats(IPtype, srcMAC, dstMAC, srcIP, srcproto, dstIP, dstproto,
                                                int(framelen),
                                                float(timestamp),self.curPacketIndx)


        ### Extract Features
        # try:
        #     return self.nstat.updateGetStats(IPtype, srcMAC, dstMAC, srcIP, srcproto, dstIP, dstproto,
        #                                          int(framelen),
        #                                          float(timestamp))
        # except Exception as e:
        #     print(e)
        #     return []


    def evaluate_stats_dict(self, dictionary) :
        """
        evaluates some statistics on the flows 

        CAVEAT : IT USES A TRICK BASED ON THE PRESENCE OF '_'
        TO CLASSIFY ORIGIN ONLY OR ORIGIN DESTINATION
        TODO IT DOES NOT WORK FOR MAC IP
        evaluates the number of flows and the histogram 
        of the number of packets for each flow
        """

        flow_counter = 0
        flow_counter_other = 0
        packet_counter = 0
        packet_counter_other = 0
        histogram = dict()
        histogram_other = dict()

        sorted_list = []
        sorted_list_other = []


        for key, value in dictionary.items() :
            if value.time_value != [] :
                samples = len (value.time_value)
                if (key.count('_') == 1) :
                    #in this case there is only the source
                    flow_counter += 1
                    packet_counter += samples
                    if samples in histogram :
                        histogram[samples] += 1
                    else :
                        histogram[samples] = 1
                    sorted_list.append((samples,key))
                else :
                    #it is source/dest or conversation
                    flow_counter_other += 1
                    packet_counter_other += samples
                    if samples in histogram_other :
                        histogram_other[samples] += 1
                    else :
                        histogram_other[samples] = 1
                    sorted_list_other.append((samples,key))
                
                #print (key, value.time_value)
        print ('num of flows origin only',flow_counter)
        print ('num of packets',packet_counter)
        print (histogram)
        # dict1 = OrderedDict(sorted(histogram.items()))
        # print(dict1)
        sorted_list = sorted(sorted_list)
        sorted_list.reverse()
        print(sorted_list)

        print ('num of flows origin destinaton',flow_counter_other)
        print ('num of packets',packet_counter_other)
        print (histogram_other)
        # dict1 = OrderedDict(sorted(histogram_other.items()))
        # print(dict1)
        sorted_list_other = sorted(sorted_list_other)
        sorted_list_other.reverse()
        print(sorted_list_other)

        return histogram, sorted_list, histogram_other, sorted_list_other



    def export_flow_time_values_dict(self, dictionary, out_dict) :

        flow_counter = 0
        packet_counter = 0
        histogram = dict()

        for key, value in dictionary.items() :
            if value.time_value != [] :
                flow_counter += 1
                samples = len (value.time_value)
                packet_counter += samples
                if samples in histogram :
                    histogram[samples] += 1
                else :
                    histogram[samples] = 1
                out_dict[key]=value.time_value
                #print (key, value.time_value)



    def export_flow_time_values(self) :
        """
        export time values series for all flows

        it assumes that the time_value array is added to
        HT attribute of nstat.HT_H and of nstat.HT_Hp
        """
        out_dict = dict()
        self.export_flow_time_values_dict(self.nstat.HT_H.HT,out_dict)
        self.export_flow_time_values_dict(self.nstat.HT_Hp.HT,out_dict)
        json_string = json.dumps(out_dict, indent=2)
        with open('json_data.json', 'w') as outfile:
            outfile.write(json_string)


    def evaluate_stats(self) :
        histo_source, list_source, histo_sourcedest, list_sourcedest = self.evaluate_stats_dict(self.nstat.HT_H.HT)
        histo_null, list_null, histo_conv, list_conv = self.evaluate_stats_dict(self.nstat.HT_Hp.HT)
        #TODO FIX STATS FOR MAC IP
        #histo_mi, list_mi, histo_sdmi, list_sdmi = self.evaluate_stats_dict(self.nstat.HT_MI.HT)
        self.evaluate_stats_dict(self.nstat.HT_jit.HT)


        my_stats = dict()
        my_stats ['source'] = {'histo' : histo_source, 'list' : list_source}
        my_stats ['sourcedest'] = {'histo' : histo_sourcedest, 'list' : list_sourcedest}
        my_stats ['conversation'] = {'histo' : histo_conv, 'list' : list_conv}
        json_string = json.dumps(my_stats, indent=2)
        with open('json_stats.json', 'w') as outfile:
            outfile.write(json_string)

    def pcap2tsv_with_tshark(self):
        print('Parsing with tshark...')
        fields = "-e frame.time_epoch -e frame.len -e eth.src -e eth.dst -e ip.src -e ip.dst -e tcp.srcport -e tcp.dstport -e udp.srcport -e udp.dstport -e icmp.type -e icmp.code -e arp.opcode -e arp.src.hw_mac -e arp.src.proto_ipv4 -e arp.dst.hw_mac -e arp.dst.proto_ipv4 -e ipv6.src -e ipv6.dst"
        cmd =  '"' + self._tshark + '" -r '+ self.path +' -T fields '+ fields +' -E header=y -E occurrence=f > '+self.path+".tsv"
        subprocess.call(cmd,shell=True)
        print("tshark parsing complete. File saved as: "+self.path +".tsv")

    def get_num_features(self):
        return len(self.nstat.getNetStatHeaders())
