# This script is used to create the threshold data
from __future__ import division
from jdcal import gcal2jd
import os
from itertools import dropwhile


def get2attr(obj, attr1, attr2, opt_arg=None):
# utility function for calling getattr twice. Used in some loops.    
    if opt_arg is not None:
        return getattr(getattr(obj, attr1), attr2)(opt_arg)
    if opt_arg is None:
        return getattr(getattr(obj, attr1), attr2)

# From here, this code has already been written by Thomas McCauley
class TMCCount:
    # extracts data from columns in 2 - 9 in each data line
    def __init__(self, word):
        self.word = word
        self.bin_word = format(int(word, 16), '08b')
        # bit 7: 1 = write new event begins in this line (true for Rising Edge 1 only)
        #        0 = event continues on this line
        # bit 6: not used, always 0
        # bit 5: indicates if this edge is valid and should be recorded
        # bit 0-4: binary representation Rise/Fall edge time, number of counts since clock tick (in units of 1.25 ns)

        self.edge_count = self.bin_word[3:]  # number of counts

        if self.bin_word[2] == '1':
            # picks out bit 5
            self.edge_valid = True
        else:
            self.edge_valid = False

        self.bit_7 = self.bin_word[0]
        # picks out bit 7


class DAQStatus:
    # warns of possible errors in this particular line, encoded in binary, column 15 of data line
    def __init__(self, word):
        self.word = word
        self.bin_word = format(int(word, 16), '04b')

        self.bit_0 = self.bin_word[3]
        self.bit_1 = self.bin_word[2]
        self.bit_2 = self.bin_word[1]
        self.bit_3 = self.bin_word[0]
        # For all bits, 0 is OK, 1 is warning
        # bit 0: 1PPS interrupt pending
        # bit 1: trigger interrupt pending
        # bit 2: GPS data possibly corrupted
        # bit 3: PPS rate not within 25 clock ticks

        if (int(self.bit_0) + int(self.bit_1) + int(self.bit_2) + int(self.bit_3)) > 0:
            self.is_ok = False
        else:
            self.is_ok = True


class DAQLine:
    # class used to categorize data in each data line
    def __init__(self, words):
        self.words = words

        self.re_1 = TMCCount(words[1])  # rising edge 1
        self.fe_1 = TMCCount(words[2])  # falling edge 1

        self.re_2 = TMCCount(words[3])  # rising edge 2
        self.fe_2 = TMCCount(words[4])  # falling edge 2

        self.re_3 = TMCCount(words[5])  # rising edge 3
        self.fe_3 = TMCCount(words[6])  # falling edge 3

        self.re_4 = TMCCount(words[7])  # rising edge 4
        self.fe_4 = TMCCount(words[8])  # falling edge 4
        # this indicate when the voltage in each channel dropped below the threshold and then came back up

        self.clock_count = words[0]  # Local time according to DAQ system
        self.pps = words[9]          # Time of last DAQ clock/GPS clock re-sync
        self.utc_time = words[10]    # UTC time from GPS (ddmmyy)
        self.utc_date = words[11]    # UTC date from GPS (hhmmss.ddd)

        if words[12] == 'A':         # indicates if the GPS data was well received
            self.gps_valid = True
        elif words[12] == 'V':
            self.gps_valid = False

        self.n_gps = int(words[13])             # number of GPS satellites in view
        self.daq_status = DAQStatus(words[14])  # any warnings about DAQ line
        self.time_delay = words[15]             # time delay between PPS and GPS update in milliseconds

# End code written by Thomas McCauley

# Example of event
# 687C4047 80 00 2B 00 00 00 00 00 67037CB8 000322.027 180516 A 03 0 +0053
# 687C4047 00 00 00 00 3A 00 00 00 67037CB8 000322.027 180516 A 03 0 +0053
# 687C4048 00 00 00 28 00 00 00 00 67037CB8 000322.027 180516 A 03 0 +0053
# 687C4048 00 00 00 00 00 36 00 00 67037CB8 000322.027 180516 A 03 0 +0053


class Event:
    # class for constructing threshold data from a list of DAQ lines
    def __init__(self, event_lines):
        event_daq_lines = []
        # convert event entries into DAQLine type
        for line in event_lines:
            daq_line = line.split()
            event_daq_lines.append(DAQLine(daq_line))

        # compute event time with error
        t_1pps = event_daq_lines[0].utc_time
        t_1pps = float(t_1pps[0:2])*3600 + float(t_1pps[2:4])*60 + float(t_1pps[4:])
        t_1pps = round(t_1pps + (int(event_daq_lines[0].time_delay)/1000))  # clock time to nearest second

        # determine clock frequency. Default is 25 MHz, may drift if pps refresh is out of sync with clock
        freq = int(event_daq_lines[-1].pps, 16) - int(event_daq_lines[0].pps, 16)
        if freq < 0:
            freq += int('FFFFFFFF', 16)
        if freq == 0:
            freq = 25000000   # Will likely be changed to accomodate different versions of the DAQ


        self.t_abs = t_1pps  # absolute time of the event since midnight in seconds
        self.re1_count = []
        self.fe1_count = []
        self.re2_count = []   # These will contain all paired rising and falling times
        self.fe2_count = []         # for the event in ns since the event start
        self.re3_count = []
        self.fe3_count = []
        self.re4_count = []
        self.fe4_count = []
        self.utc_day = event_daq_lines[0].utc_date

        edge_counts = ['re1_count', 'fe1_count', 're2_count', 'fe2_count', 're3_count', 'fe3_count', 're4_count', 'fe4_count']
        edge_list = ['re_1', 'fe_1', 're_2', 'fe_2', 're_3', 'fe_3', 're_4', 'fe_4']
        # load all edge times into the proper places
        for daq in event_daq_lines:
            t_clk = 1e9*(int(daq.clock_count, 16) - int(daq.pps, 16))/freq
            # the clock ticks are added here, in contrast with the examples
            # in the DAQ manual. Since it varies, it made more sense to put
            # it here.
            
            for i in range(8):
                if get2attr(daq, edge_list[i], 'edge_valid'):
                    edge_time = 1.25*int(get2attr(daq, edge_list[i], 'edge_count'), 2) + t_clk
                    get2attr(self, edge_counts[i], 'append', edge_time)

        # inspect the edge times and toss out 'orphaned' triggers
        for i in range(0, 8, 2):
            len_re = len(getattr(self, edge_counts[i]))
            len_fe = len(getattr(self, edge_counts[i+1]))
            if len_re == len_fe:
                continue
            elif len_re > len_fe:
                get2attr(self, edge_counts[i], 'pop', -1)
            elif len_re < len_fe:
                get2attr(self, edge_counts[i+1], 'pop', -1)


def event_finder(data):
    # iterates through a list of data and identifies events. Collects them and returns list of events, each of which is
    # a list of data lines within single event
    count = 0
    single_event = []  # will hold all lines in identified event
    all_events = []    # to be loaded with each event when it is filled

    index = 0          # holds place in data list

    single_event = []
    flag = False
    while index < len(data):
        check = data[index][9:11]
        check_bin = format(int(check, 16), '08b')   # refer to TMC_Count class, indicates start of new event

        if check_bin[0] == '1' and flag is False:   # event found, begin writing
            single_event.append(data[index])
            index += 1
            flag = True
        elif check_bin[0] == '0' and flag is True:  # No new event, writing triggered so continue writing
            single_event.append(data[index])
            index += 1
        elif check_bin[0] == '1' and flag is True:  # New event detected, stop writing this one, load all_events
            all_events.append(single_event)
            single_event = []
            flag = False
        count+=1
        if count%1000==0:
            print count
        # As there likely will not be an event in the last line, this ensures
        # we get the last one
    if single_event != []:
        all_events.append(single_event)

    return all_events


def process_events(event_block, sat_num):
    # takes in list of raw data as strings, processes them, and returns a list of strings to be printed in the output file
    event = Event(event_block)
    print_out = []
    
    # get the julian day
    day = int(event.utc_day[0:2])
    month = int(event.utc_day[2:4])
    year = int('20' + event.utc_day[4:])
    julian_start = str(sum(gcal2jd(year, month, day)) + event.t_abs/86400)
    [jul_day, jul_frac] = julian_start.split('.')    
    
    jul_frac = '.' + jul_frac
    edge_counts = [['re1_count', '1'], 'fe1_count', ['re2_count', '2'], 'fe2_count', ['re3_count', '3'], 'fe3_count', ['re4_count', '4'], 'fe4_count']
    # somewhat cluttered construction, but I have it here to make sure the printed
    # channel number is correctly matched
    
    switch = jul_day # added to stop the start day from changing
    
    # generate text for all happenings in the event
    for i in range(0, 8, 2):
        out_line = ''
        jul_day = int(switch)
        for j in range(len(getattr(event, edge_counts[i][0]))):
            out_line = sat_num + '.{}  '.format(edge_counts[i][1])
            
            t_rise_list = getattr(event, edge_counts[i][0])
            t_rise = t_rise_list[j]/1e9
            t_fall_list = getattr(event, edge_counts[i+1])
            t_fall = t_fall_list[j]/1e9
            
            t_over_thresh = (t_fall - t_rise)*1e9  # Time over threshold
            
            t_rise = t_rise/86400 + float(jul_frac)  
            t_fall = t_fall/86400 + float(jul_frac)
       # Due to a bug in newer versions of the DAQ software, times are off
       # by exactly one second. I will likely implement this whenever
       # I add in the wire delays.
       #   t_rise -= 1/86400
       #   t_fall -= 1/86400
            
            # If the fractional day exceeds 1, we need to adjust accordingly
            if t_rise > 1 or t_fall > 1 or (t_rise and t_fall) > 1:
                jul_day += 1
            if t_rise > 1:
                t_rise -= 1
            if t_fall > 1:
                t_fall -= 1

            out_line += str(jul_day) + '  '
            out_line += '{0:.16f}  '.format(t_rise)
            out_line += '{0:.16f} '.format(t_fall)
            out_line += ' {0:.2f}\n'.format(t_over_thresh)
        print_out.append(out_line)
    return print_out


def MainThreshold(file_name, file_path=os.getcwd()):
    # Main Function, returns a path to created file.
    # Saved in current working directory by default or specify.
    data = open(file_name, 'r')
    data_lines = [line for line in data.readlines()]
    all_events = event_finder(data_lines)
    data.close()
    sat_num = file_name[0:4]
    
    proc_data = []
    for block in all_events:
        proc_data += process_events(block, sat_num)
    proc_data.sort(key=lambda x: x.split()[1:3]) # sorts by Julian day, then rise time
    if file_path != os.getcwd():
        full_path = os.path.join(file_path, file_name+'.thresh')
    else:
        full_path = file_name + '.thresh'
    outfile = open(full_path, 'w')
    outfile.write('#ID.CHANNEL, Julian Day, RISING EDGE(sec), FALLING EDGE(sec), TIME OVER THRESHOLD (nanosec)\n')
    outfile.close()
    outfile = open(full_path, 'a')
    for line in proc_data:
        outfile.write(line)

    return full_path


# helper function for identifying comments while sorting
def is_comment(s):
    return s.startswith('#')
    
def splitChannels(in_file, chans, path=os.getcwd()):
# function for splitting up the threshold data. Chans is a list of channels to be
# returned. If you do
    with open(in_file, 'r') as thresh:
        thresh_data = [line for line in dropwhile(is_comment, thresh)]
    
    file_name = in_file[len(in_file)-23:]   
    thresh_data.sort()
    # script will also write a sorted threshold file as it may be of use    
    sorted_thresh_path = os.path.join(path, '/data/threshold/'+file_name+'.sort')
    thresh_sort = open(sorted_thresh_path,'w')    
        
    
    header = '#ID.CHANNEL, Julian Day, RISING EDGE(sec), FALLING EDGE(sec), TIME OVER THRESHOLD (nanosec)\n'
    thresh_dict = {}
    files_printed = []    
    # create appropriate files    
    for chan in chans:
        if path != os.getcwd():
            full_path = os.path.join(path, 'data/threshold/'+file_name+'.'+chan)
        else:
            full_path = 'data/threshold/'+file_name+'.'+chan
        
        thresh_dict['chan' + chan] = [open(full_path,'w'), chan]
        thresh_dict['chan' + chan][0].write(header)
        files_printed.append(chan)
    
    for line in thresh_data:
        if line[5] in files_printed:
            thresh_dict['chan'+line[5]][0].write(line)
        thresh_sort.write(line)
    
    for f in thresh_dict:
        thresh_dict[f][0].close()
    
    thresh_sort.close()    
    
    return thresh_dict


def AllThresholdFiles(file_name, chans = [] , path=os.getcwd()):
    # function to get main file, sorted and split threshold files
    chain_path = MainThreshold(file_name, path)
    thresh_dict = splitChannels(chain_path, path, chans)

    return chain_path - file_name - '.thresh'



path = MainThreshold('6119.2016.0625.0')
