# -*- coding: utf-8 -*-
"""
Created on Sat Apr 22 10:59:35 2017

@author: Samwu
"""
import serial
import string
from PyQt4.QtCore import *
from PyQt4.QtGui  import *

from cmd_rev_decode import *

class ComMonitor(QThread):
    def __init__(self,com,parent=None):
        super(ComMonitor,self).__init__(parent)
        self.working  = True
        self.com      = com
        self.rcmd     = HexDecode()

    def __del__(self):
        self.working=False
        self.wait()

    def run(self):
        while self.working==True:
            if self.com.isOpen() == True:
                try:
                    read_char = self.com.read(1)
                    recv_str  = self.rcmd.r_machine(read_char)
                except serial.SerialException:
                    recv_str = u'{"fun":"Error","description":"serialport lost!"}'
                    self.working = False
                    pass
                if recv_str :
                    self.emit(SIGNAL('r_cmd_message(QString, QString)'),self.com.portstr,recv_str)
                    self.rcmd.init()
