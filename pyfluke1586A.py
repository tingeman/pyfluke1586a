#!/usr/bin/env python
# Python 3.X

# conda install -n instruments pyserial
# conda install -c conda-forge ntplib

__version__ = '2020.07'

import sys
import math
import serial
import serial.tools.list_ports
import time
import pdb
import logging
import ntplib, socket
import datetime as dt
from pathlib import Path

TimeOutLimitSecsFluke1586A = 0.5       # max time (in seconds) to wait for response from Fluke unit
TimeBetweenCommandsSecs = 0.25   # min time (in seconds) between commands to Fluke

# Commands sent to Fluke1586A
Fluke1586A_RS232_out_commands = {
    'SYST:DATE':   {'format': '{0:4d},{1:02d},{2:02d}'},          # "DATE YYYY,MM,DD"
    'SYST:TIME':   {'format': '{0:02d},{1:02d},{2:02d}'},         # "TIME hh,mm,ss" 
    }
    
# Responses received from Fluke1586A
Fluke1586A_RS232_in_commands = {
    '*idn?':      {'converter': None}, # Standard instrument identification string
    'SYST:DATE?': {'converter': [int, int, int]}, #
    'SYST:TIME?': {'converter': [int, int, int]}, #
    }
    
Fluke1586A_RS232_commands = {}
Fluke1586A_RS232_commands.update(Fluke1586A_RS232_out_commands)
Fluke1586A_RS232_commands.update(Fluke1586A_RS232_in_commands)
    

def get_internet_time_offset():
    """Get internet time and calculate system time offset in seconds."""
    c = ntplib.NTPClient()
    response = c.request('europe.pool.ntp.org', version=3)
    return response.offset
    
    
class Fluke1586A(object):
    def __init__(self, com_port, nickname='', baudrate=9600, bytesize=serial.EIGHTBITS,
                 stopbits=serial.STOPBITS_ONE, parity=serial.PARITY_NONE,
                 dsrdtr=False, rtscts=False, xonxoff=False,
                 timeout=TimeOutLimitSecsFluke1586A,
                 nChannels=2, debug=False):
        self.debug = debug
        self.com_port = com_port
        self.nickname = nickname
        try:
            self.serial = serial.serial_for_url(com_port, baudrate,
                    bytesize=bytesize, stopbits=stopbits, parity=parity,
                    dsrdtr=dsrdtr, rtscts=rtscts, xonxoff=xonxoff,
                    timeout=timeout)
        except AttributeError:
            # happens when the installed pyserial is older than 2.5. use the
            # Serial class directly then.
            self.serial = serial.Serial(com_port, baudrate,
                    bytesize=bytesize, stopbits=stopbits, parity=parity,
                    dsrdtr=dsrdtr, rtscts=rtscts, xonxoff=xonxoff,
                    timeout=timeout)
        
        self.serial.set_buffer_size(rx_size = 1024*1024)
                    
    def __del__(self):
        self.close()
        
    def close(self):
        try:
            self.serial.close()
            logging.info('Serial port {0} closed ({1})'.format(self.com_port, self.nickname))
        except:
            logging.info('Failed to close serial port {0}! ({1})'.format(self.com_port, self.nickname))

    def initialize(self):
        resp = dict()
        cmd = dict()

        resp['id'],cmd['id'] = self.get_version()
        resp['F_date'],cmd['F_date'] = self.get_date()
        
        t1 = dt.datetime.now()
        resp['F_time'],cmd['F_time'] = self.get_time()
        t2 = dt.datetime.now()
        resp['PC_time'] = str(t1+(t2-t1)/2)
        
        return resp
    
    def send_message(self, command, arguments=None, get_response=True):
        # Updated for Fluke1586A
        CmdString = command
        if arguments is not None:
            #raise NotImplementedError('Sending arguments to Fluke1586A is not handled at the moment')
            try:
                CmdString += ' '+Fluke1586A_RS232_out_commands[command]['format'].format(*arguments)
            except:
                CmdString += ' '+Fluke1586A_RS232_out_commands[command]['format'].format(arguments)
            #get_response = False
            
        CmdString += '\r'  # ASCII 13 carriage return
        # First flush any unread input
        self.serial.flushInput()

        # Now write the command
        self.serial.write('\r'.encode())
        self.serial.write(CmdString.encode())

        if self.debug:
            print("Command:  " + CmdString)
        
        reply = None
        
        if get_response:
            reply = self.get_response()

            if self.debug:
                print("Response: " + reply)
        else:
            pass
            #time.sleep(0.25)
            
        return reply, CmdString

    def get_response(self, timeout=TimeOutLimitSecsFluke1586A, terminated=True):
        d = self.serial.getSettingsDict()
        d['timeout'] = timeout
        self.serial.applySettingsDict(d)

        resp = self.serial.read(1)  # this will block execution until reply or timeout

        tstart= time.time()
        timeout = time.time() + 0.5
        pend = ''
        while True:
            if self.serial.inWaiting() > 0:
                resp += self.serial.read(self.serial.inWaiting())
                timeout = time.time() + 0.5
            if len(resp)>0 and terminated and resp[-1]==13:
                break
            if time.time() > timeout:
                break
            if time.time()-tstart > 3:
                tstart = time.time()
                print('*', end='', flush=True)
                pend = '\n'
                
        print('', end=pend)
        return resp.strip()

    def get_identification(self):
        cmd = '*idn?'
        resp,cmd = self.send_message(cmd)
        logging.info('get_status: {0}   ({1}@{2}:{3})'.format(resp, self.nickname, self.com_port, cmd))
        return resp, cmd

    def get_version(self):
        cmd = 'SYST:VERS?'
        resp,cmd = self.send_message(cmd)
        logging.info('get_version: {0}   ({1}@{2}:{3})'.format(resp, self.nickname, self.com_port, cmd))
        return resp, cmd

    def get_date(self):
        cmd = 'SYST:DATE?'
        resp,cmd = self.send_message(cmd)
        logging.info('get_date: {0}   ({1}@{2}:{3})'.format(resp, self.nickname, self.com_port, cmd))
        return resp, cmd
        
    def get_time(self):
        cmd = 'SYST:TIME?'
        resp,cmd = self.send_message(cmd)
        logging.info('get_time: {0}   ({1}@{2}:{3})'.format(resp, self.nickname, self.com_port, cmd))
        return resp, cmd

    def set_date(self):
        cmd = 'SYST:DATE'
        t1 = dt.date.today()
        arguments = [t1.year, t1.month, t1.day]
        resp,cmd = self.send_message(cmd, arguments)
        logging.info('set_date: {0}   ({1}@{2}:{3})'.format(resp, self.nickname, self.com_port, cmd))
        return resp, cmd
        
    def set_time(self):
        cmd = 'SYST:TIME'
        t1 = dt.datetime.now()
        arguments = [t1.hour, t1.minute, math.ceil(t1.second+t1.microsecond/1e6)]   # Ceil is used to round seconds up, under assumption that there will be a small delay in transmission.
        resp,cmd = self.send_message(cmd, arguments)
        logging.info('set_time: {0}   ({1}@{2}:{3})'.format(resp, self.nickname, self.com_port, cmd))
        return resp, cmd
        
    def get_offset(self):
        #fserial = self.get_serial()
        fdate, cmd = self.get_date()
        
        t1 = dt.datetime.now()
        ftime, cmd = self.get_time()
        t2 = dt.datetime.now()
        com_delay = (t2-t1)
        pc_datetime = t1+com_delay/2
        
        fdate = [int(s) for s in fdate.decode().split(',')]
        ftime = [int(s) for s in ftime.decode().split(',')]
        
        f_datetime = dt.datetime(*fdate, *ftime)
        
        print('Current PC date & time:           {0}'.format(pc_datetime.strftime(r'%Y-%m-%d %H:%M:%S')))
        print('Current instrument date & time:   {0}'.format(f_datetime.strftime(r'%Y-%m-%d %H:%M:%S')))
        offset = f_datetime-pc_datetime
        print('Instrument offset:                {0:.1f} s'.format(offset.total_seconds()))
        print('Total comm delay:                 {0:.2f} s'.format(com_delay.total_seconds()))
        
        
        return offset
        
    def sync_datetime(self):
        self.get_offset()
        self.set_date()
        self.set_time()
        print('')
        print('Instrument date and time set to match PC date and time.')
        print('')
        self.get_offset()
    
    def get_values(self, slot, id):
        if not isinstance(slot, int):
            raise ValueError('The data slot must be an integer value!')
        self.send_message('LOG:AUT:LAB {0:d}'.format(slot), get_response=False)
        resp, cmd = self.send_message('LOG:AUT:VAL? {0}'.format(id), get_response=False)
        resp = self.get_response(terminated=False)
        return resp
        
    
    def download_data(self, slot, fname=None):
        raise NotImplementedError('Data download is not yet implemented for 1586A, use USB export...!')
        if not isinstance(slot, int):
            raise ValueError('The data slot must be an integer value!')
        self.send_message('LOG:AUT:LAB {0:d}'.format(slot))
        resp, cmd = self.send_message('LOG:AUT:POIN?')
        print('Retrieving {0:d} data points from Autolog slot {1:d}.'.format(int(resp),slot))
        resp, cmd = self.send_message('LOG:AUT:PRIN {0:d}'.format(slot), get_response=False)
        resp = self.get_response(terminated=False)
        
        resp = resp.decode().split('\r')
        
        if fname is not None:
            p = Path(fname)
            
        
            with p.open(mode='w') as fh:
                for line in resp:
                    fh.write(line+'\n')
                    
            # save channel 1 data separately
            with p.with_name(p.stem+'_ch1'+p.suffix).open(mode='w') as fh:
                for line in resp:
                    if ',1,' in line:
                        fh.write(line+'\n')
        
            # save channel 2 data separately        
            with p.with_name(p.stem+'_ch2'+p.suffix).open(mode='w') as fh:
                for line in resp:
                    if ',2,' in line:
                        fh.write(line+'\n')
                    
        return resp
        

def check_Fluke_time(com='COM1'):
    # make sure we start afresh with logging...
    # Remove all handlers associated with the root logger object.
    for handler in logging.root.handlers[:]:
        handler.close()
        logging.root.removeHandler(handler)
    
    logging.basicConfig(format='%(asctime)s %(message)s', 
                        datefmt='%m/%d/%Y %H:%M:%S',
                        filename='Fluke1586A_commands_{0}.log'.format(time.strftime("%Y%m%d_%H%M%S", time.gmtime())),
                        filemode='w',
                        level=logging.DEBUG)

    myFluke = Fluke1586A(com)                        
    print('Initialized fluke...')
    
    try:
        resp = myFluke.initialize()
    
    finally:
        myFluke.close()

    for key,val in resp.items():
        print('{0}:  {1}', format(key,val))


myFluke = None

def list_com_ports():
    ports = serial.tools.list_ports.comports()
    for id, port in enumerate(ports):
        print('{0})  {1}:\t{2}'.format(id, port.device, port.description))
    print('')
    return ports

def select_com():
    global myFluke
    print('List of available COM ports:')
    print('')
    ports = list_com_ports()
    try:
        choice = int(input('Choose COM port: '))
    except ValueError:
        print('Invalid input!')
    if choice <= len(ports):
        try:
            myFluke.close()
        except:
            pass
        myFluke = Fluke1586A( ports[choice].device)
        return ports[choice].device
    else:
        print('Invalid input!')
        return None
    
    
        
def identify():
    resp, cmd = myFluke.get_identification()
    print('Instrument identification: {0}'.format(resp.decode()))

def check_PC_offset():
    try:
        offset = get_internet_time_offset()
    except socket.gaierror:
        print('Could not reach internet time server!')
        return
        
    if offset>=0:
        direction='behind'
    else:
        direction='ahead of'
    print('')
    print('PC time is {0:.2f} sec {1} internet time'.format(abs(offset), direction))
    
def check_fluke_offset():
    myFluke.get_offset()
    
def sync_fluke_time():
    myFluke.sync_datetime()
    
def download_data(): 
    raise NotImplementedError('Data download is not yet implemented for 1586A, use USB export...!')
    data = {}
    
    print('')
    print('Retrieving information from instrument...')
    
    for slot in range(1,11):
        myFluke.send_message('LOG:AUT:LAB {0:d}'.format(slot), get_response=False)
        resp, cmd = myFluke.send_message('LOG:AUT:POIN?')
        vals = resp.decode().strip() 
        if int(vals)>0:
            resp = myFluke.get_values(slot, 1)
            resp = resp.decode().split('\r')
            data[slot] = '{0:>2d}) DATA_{0:02d}:  {1} measurements   ({2})'.format(slot, int(vals), resp[0])
        else:
            data[slot] = '{0:>2d}) DATA_{0:02d}:  {1} measurements'.format(slot, int(vals))
        
        
        print('*', end='', flush=True)
    print('')
    print('')
        
    while True:
        for slot in range(1,11):
            print(data[slot])
        print('')
        print(' 0) EXIT')
        print('')
        
        try:
            choice = int(input('Data slot to download: '))
        except ValueError:
            print('Invalid input!')
            continue
        
        if choice == 0:
            return
        
        fname = 'DATA_{0:02d}_{1:%Y%m%d-%H%M%S}.dat'.format(choice, dt.datetime.now())
        myFluke.download_data(choice, fname)
        print('')
        print('Data saved to file: {0}'.format(fname))
        print('')
        print('')
        
def clear_data():        
    print('THIS FUNCTION IS NOT YET IMPLEMENTED!')

class LoopBreak(Exception):
    pass  

def break_loop():
    raise LoopBreak

options = {0: {'action': break_loop,         'title': 'Exit',                                 'line_after': True},
           1: {'action': select_com,         'title': 'Select COM port',                      'line_after': False},
           2: {'action': identify,           'title': 'Identify instrument',                  'line_after': False},
           3: {'action': check_PC_offset,    'title': 'Check PC offset with Internet time',   'line_after': False},
           4: {'action': check_fluke_offset, 'title': 'Check instrument offset with pc time', 'line_after': False},
           5: {'action': sync_fluke_time,    'title': 'Synchronize instrument time with pc',  'line_after': True},
           #6: {'action': download_data,      'title': 'Download Autolog data from Instrument','line_after': False},
           #7: {'action': clear_data,         'title': 'Clear Autolog data memory',            'line_after': False},
           }
           

if __name__=='__main__':
    try:
        myFluke.close()
    except:
        pass
        
    try:
        myFluke = Fluke1586A('COM3')
    except serial.SerialException:
        #list_com_ports()
        #print('Could not open COM port! Aborting...')
        #sys.exit()
        select_com()
    
    while True:
        print('')
        print('')
        check_PC_offset()
        print('Instrument COM port: {0}'.format(myFluke.com_port))
        resp, cmd = myFluke.get_identification()
        resp = resp.decode().strip()
        if len(resp)>0:
            print('Instrument identification: {0}'.format(resp))
        else:
            print('NO RESPONSE FROM INSTRUMENT ON PORT {0}'.format(myFluke.com_port))
        print('')
        print('')
        print('Menu options:')
        print('')
        for opt, vals in options.items():
            print('{0:2d}: {1}'.format(opt, vals['title']))
            if vals['line_after']:
                print('---------------------------------------------')
        print('')
        
        try:
            choice = int(input('Chosen option: '))
        except ValueError:
            print('Invalid input!')
            continue
        
        action = options.get(choice)['action']
        try:
            action()
        except LoopBreak:
            break
        except serial.SerialException:
            print('COULD NOT COMMUNICATE WITH INSTRUMENT!')
        #except:
        #    print('Unknown error, check connections and settings and try again!')
    
        print('')
        input('Press any key to continue...')
    
    myFluke.close()
            