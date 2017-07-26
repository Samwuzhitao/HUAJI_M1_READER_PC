# -*- coding: utf-8 -*-
"""
Created on Sat Apr 22 10:59:35 2017

@author: john
"""
import serial
import string
import time
import os
import sys
import logging
import json
import xlrd
import xlwt
from PyQt4.QtCore import *
from PyQt4.QtGui  import *
import ConfigParser
from cmd_rev_decode import *
from com_monitor    import *
from led            import *

ser           = 0
input_count   = 0
LOGTIMEFORMAT = '%Y%m%d%H'
log_time      = time.strftime( LOGTIMEFORMAT,time.localtime(time.time()))
log_name      = "log-%s.txt" % log_time
CONF_FONT_SIZE = 10

logging.basicConfig ( # 配置日志输出的方式及格式
    level = logging.DEBUG,
    filename = log_name,
    filemode = 'a',
    format = u'[%(asctime)s] %(message)s',
)

TAG_IDLE       = 0
TAG_SHOW       = 1
TAG_SET        = 2
TAG_CHECK      = 3
TAG_CLEAR      = 4

class rfid_debug(QWidget):
    def __init__(self,parent=None):
        super(rfid_debug,self).__init__(parent)
        self.com_monitor  = None
        self.ser          = None
        self.send_cmd     = None
        self.tag_status   = TAG_IDLE
        self.send_cmd_max = 0
        self.phone_dict   = {}
        self.addr_dict    = {u'爸爸':u'38',u'妈妈':u'39',u'爷爷':u'3A',
                             u'奶奶':u'3C',u'哥哥':u'3D',u'姐姐':u'3E'}
        self.sync_fg_dict = {}
        self.current_name = None

        self.setWindowTitle(u"话机 RFID 标签参数配置")

        self.connect_label = QLabel(u"连接状态:")
        self.led1          = LED(30)
        self.e_button      = QPushButton(u"退出")
        self.bind_button   = QPushButton(u"打开设备")
        self.sync_button   = QPushButton(u"同步数据")
        self.clear_button  = QPushButton(u"清空显示")

        e_layout = QHBoxLayout()
        e_layout.addWidget(self.connect_label  )
        e_layout.addWidget(self.led1           )
        e_layout.addWidget(self.bind_button    )
        e_layout.addWidget(self.sync_button    )
        e_layout.addWidget(self.clear_button   )
        e_layout.addWidget(self.e_button       )

        self.family_label=QLabel(u"直系亲属:")
        self.family_combo = QComboBox()
        self.family_combo.addItems([u'爸爸',u'妈妈',u'爷爷',u'奶奶',u'哥哥',u'姐姐'])
        self.f_phone_label=QLabel(u"电话:")
        self.f_phone_edit = QLineEdit(u'15871492247')
        self.f_phone_edit.setMaxLength(11)
        self.f_phone_button_a = QPushButton(u"添加")
        self.f_phone_button_d = QPushButton(u"移除")

        self.other_label=QLabel(u"其他亲属:")
        self.other_edit = QLineEdit(u'大姑父')
        self.other_edit.setMaxLength(4)
        self.o_phone_label=QLabel(u"电话:")
        self.o_phone_edit = QLineEdit(u'15871492247')
        self.o_phone_edit.setMaxLength(11)
        self.o_phone_button_a = QPushButton(u"添加")
        self.o_phone_button_d = QPushButton(u"移除")

        self.family_combo.setFont(QFont( "Roman times",CONF_FONT_SIZE,QFont.Bold))
        self.f_phone_edit.setFont(QFont( "Roman times",CONF_FONT_SIZE,QFont.Bold))
        self.other_edit.setFont(QFont(   "Roman times",CONF_FONT_SIZE,QFont.Bold))
        self.o_phone_edit.setFont(QFont( "Roman times",CONF_FONT_SIZE,QFont.Bold))

        g_hbox = QGridLayout()

        g_hbox.addWidget(self.family_label     ,1,0)
        g_hbox.addWidget(self.family_combo     ,1,1,1,2)
        g_hbox.addWidget(self.f_phone_label    ,1,3)
        g_hbox.addWidget(self.f_phone_edit     ,1,4)
        g_hbox.addWidget(self.f_phone_button_a ,1,5)
        g_hbox.addWidget(self.f_phone_button_d ,1,6)

        g_hbox.addWidget(self.other_label      ,2,0)
        g_hbox.addWidget(self.other_edit       ,2,1,2,2)
        g_hbox.addWidget(self.o_phone_label    ,2,3)
        g_hbox.addWidget(self.o_phone_edit     ,2,4)
        g_hbox.addWidget(self.o_phone_button_a ,2,5)
        g_hbox.addWidget(self.o_phone_button_d ,2,6)

        self.browser = QTextBrowser()

        box = QVBoxLayout()
        box.addLayout(e_layout)
        box.addLayout(g_hbox)
        box.addWidget(self.browser)

        self.setLayout(box)

        self.e_button.clicked.connect(self.exit)
        self.bind_button.clicked.connect(self.uart_auto_connect)
        self.sync_button.clicked.connect(self.tag_sync_data)
        self.clear_button.clicked.connect(self.clear_show_message)
        self.f_phone_button_a.clicked.connect(self.f_phone_number_add)
        self.o_phone_button_a.clicked.connect(self.o_phone_number_add)
        self.f_phone_button_d.clicked.connect(self.f_phone_number_del)
        self.o_phone_button_d.clicked.connect(self.o_phone_number_del)

        self.resize( 440, 400 )
        self.timer = QTimer()
        self.timer.timeout.connect(self.tag_auto_sync_data)

    def f_phone_number_del(self):
        self.clear_show_message()
        name_str   = unicode(self.family_combo.currentText())
        iphone_str = str(self.f_phone_edit.text())
        dict_len = len(self.phone_dict)
        if dict_len > 0:
            if self.phone_dict.has_key( name_str ) == True:
                self.phone_dict.pop(name_str)
                self.sync_fg_dict.pop(name_str)
        else:
            self.browser.append(u"已经没有号码！")
        self.browser.append(u'=======================当前需要同步的号码如下=======================')
        for item in self.phone_dict:
            self.browser.append(u" * [ %s ] : %s" % (item,self.phone_dict[item]))
        self.browser.append(u'====================================================================')

    def o_phone_number_del(self):
        self.clear_show_message()
        name_str   = unicode(self.other_edit.text())
        iphone_str = str(self.f_phone_edit.text())
        dict_len = len(self.phone_dict)
        if dict_len > 0:
            if self.phone_dict.has_key( name_str ) == True:
                self.phone_dict.pop(name_str)
        else:
            self.browser.append(u"已经没有号码！")
        self.browser.append(u'=======================当前需要同步的号码如下====================')
        for item in self.phone_dict:
            self.browser.append(u" * [ %s ] : %s" % (item,self.phone_dict[item]))
        self.browser.append(u'=================================================================')

    def f_phone_number_add(self):
        self.clear_show_message()
        name_str   = unicode(self.family_combo.currentText())
        iphone_str = str(self.f_phone_edit.text())
        dict_len = len(self.phone_dict)
        if dict_len < 6:
            if self.phone_dict.has_key( name_str ) == False:
                self.phone_dict[name_str]   = iphone_str
                self.sync_fg_dict[name_str] = 0
        else:
            self.browser.append(u"电话数超过限制！")
        self.browser.append(u'=======================当前需要同步的号码如下====================')
        for item in self.phone_dict:
            self.browser.append(u" * [ %s ] : %s" % (item,self.phone_dict[item]))
        self.browser.append(u'=================================================================')

    def o_phone_number_add(self):
        self.clear_show_message()
        name_str   = unicode(self.other_edit.text())
        iphone_str = str(self.f_phone_edit.text())
        dict_len = len(self.phone_dict)
        if dict_len < 6:
            if self.phone_dict.has_key( name_str ) == False:
                self.phone_dict[name_str] = iphone_str
        else:
            self.browser.append(u"电话数超过限制！")
        self.browser.append(u'=======================当前需要同步的号码如下====================')
        for item in self.phone_dict:
            self.browser.append(u" * [ %s ] : %s" % (item,self.phone_dict[item]))
        self.browser.append(u'=================================================================')

    def clear_show_message(self):
        self.browser.clear()

    def uart_send_data(self,Cmd_data):
        cmd = Cmd_data
        cmd = str(cmd.replace(' ',''))
        cmd = cmd.decode("hex")
        if self.com_monitor:
            if self.com_monitor.working == True:
                if self.com_monitor.com.isOpen() == True:
                    sned_str = 'SEND CMD: %s' % Cmd_data
                    print sned_str
                    self.com_monitor.com.write(cmd)
                    logging.debug( u"%s %s" % (self.com_monitor.com.portstr,sned_str) )

    def name_to_hex(self,name):
        data = ""
        for i in name:
            hex_h = ord(i) >> 8
            hex_l = ord(i) & 0xFF
            data += "%02X" % hex_h + "%02X" % hex_l
        print 'name_to_hex : %s ' % data
        return data

    def phone_number_to_hex(self,phone):
        data = ""
        i = 0
        data_len = len( phone )
        for item in phone:
            if i <= data_len - 2:
                hex_h = (string.atoi(phone[i],10)<<4) & 0xF0
                hex_l = (string.atoi(phone[i+1],10) & 0x0F)
                data += "%02X"  % (hex_h | hex_l)
                i = i + 2
        print 'phone_to_hex: %s ' % data
        return data

    def get_cmd_crc(self,crc_str):
        crc = 0
        crc_data = crc_str.replace(' ','')
        print crc_data
        i = 0
        crc_len = len( crc_data )

        for item in crc_data:
            if i <= crc_len-2:
                crc  = crc ^ string.atoi(crc_data[i:i+2], 16)
                # print "c_crc = %02X crc_in = %s" % (self.crc,crc_data[i:i+2])
            i = i + 2
        cal_crc = "%02X" % crc
        return cal_crc

    def get_set_tag_cmd(self,name,phone):
        # print name,phone
        cmd_str  = "10"
        sign_str = "FFFFFFFF"
        len_str  = "11 "
        addr_str = self.addr_dict[name] #"05 "
        data     = self.name_to_hex(name) + '00000000 ' + self.phone_number_to_hex(phone+'0') + '0000 '
        crc_str  = cmd_str + sign_str + len_str + addr_str + ' ' + data
        crc      = self.get_cmd_crc(crc_str)
        cmd      = '5C' + crc_str + crc + 'CA'
        # print cmd
        return cmd

    def tag_auto_sync_data(self):
        # name = u'爸爸'
        if self.current_name == None:
            for item in self.sync_fg_dict:
                if self.sync_fg_dict[item] == 0:
                    self.current_name = item

        if self.current_name == None:
            self.tag_status = TAG_IDLE
            self.browser.append(u"同步所有参数完成")
            self.browser.append(u'=================================================================')
            self.timer.stop()

        else:
            cmd = None
            if self.tag_status == TAG_SHOW or self.tag_status == TAG_CHECK:
                # [3].读数据指令
                # cmd = "5C 11 00 0F 0F 00 01 04 14 CA"
                cmd_str  = "11"
                sign_str = "000F0F00"
                len_str  = "01 "
                addr_str = self.addr_dict[self.current_name] #"05 "
                crc_str  = cmd_str + sign_str + len_str + addr_str + ' '
                crc      = self.get_cmd_crc(crc_str)
                cmd      = '5C' + crc_str + crc + 'CA'

            if self.tag_status == TAG_SET:
                cmd = self.get_set_tag_cmd(self.current_name,self.phone_dict[self.current_name])

            if self.tag_status == TAG_CLEAR:
                # [4].清数据指令
                # cmd = "5C 12 00 0F 0F 00 01 04 17 CA"
                cmd_str  = "12"
                sign_str = "000F0F0F"
                len_str  = "01 "
                addr_str = self.addr_dict[self.current_name] #"05 "
                crc_str  = cmd_str + sign_str + len_str + addr_str + ' '
                crc      = self.get_cmd_crc(crc_str)
                cmd      = '5C' + crc_str + crc + 'CA'

            if cmd:
                self.uart_send_data(cmd)
                self.browser.append(u"[STATUS = %d] CMD: %s" % (self.tag_status,cmd))

    def tag_sync_data(self):
        button_str = self.bind_button.text()

        if button_str == u"关闭设备":
            self.tag_status   = TAG_SHOW
            self.send_cmd_max = 0
            for item in self.sync_fg_dict:
                self.sync_fg_dict[item] = 0

            self.clear_show_message()
            self.browser.append(u'=======================当前需要同步的号码如下====================')
            for item in self.phone_dict:
                self.browser.append(u" * [ %s ] : %s" % (item,self.phone_dict[item]))
            self.browser.append(u'=================================================================')
            self.timer.start(300)
        else:
            self.browser.append(u"请先打开设备！")


    def uart_auto_connect(self):
        connect_cmd = "5C 40 00 F0 F0 00 00 40 CA"
        connect_cmd = str(connect_cmd.replace(' ',''))
        connect_cmd = connect_cmd.decode("hex")
        hex_decode  = HexDecode()
        ser         = None
        ser_list    = []
        ports_dict  = {}

        button_str = self.bind_button.text()

        if button_str == u"打开设备":
            for i in range(256):
                try:
                    s = serial.Serial(i)
                    ports_dict[s.portstr] = i
                    ser_list.append(s.portstr)
                    s.close()
                except serial.SerialException:
                    pass
            print "SEARCH COM LIST: ",
            print ser_list

            # 发送链接指令
            for item in ser_list:
                try:
                    ser = serial.Serial( ports_dict[item], 115200, timeout = 0.5)
                except serial.SerialException:
                    pass

                if ser:
                    if ser.isOpen() == True:
                        ser.write( connect_cmd )
                        cmd_result = ser.read(39)
                        print cmd_result
                        if cmd_result != None and cmd_result != '':
                            for i in cmd_result:
                                cmd_str = hex_decode.r_machine(i)
                            print cmd_str
                            if cmd_str:
                                ser.close()
                                ser = serial.Serial( ports_dict[item], 115200)
                                self.bind_button.setText(u"关闭设备")
                                self.led1.set_color("blue")
                                self.com_monitor = ComMonitor(ser)
                                self.connect(self.com_monitor,SIGNAL('r_cmd_message(QString, QString)'),
                                    self.uart_update_text)
                                self.com_monitor.start()
                                self.browser.append(u"打开串口: %s" % (item))
                                return item
                        else:
                            self.browser.append(u"打开串口失败")
                            return 0

        if button_str == u"关闭设备":
            self.led1.set_color("gray")
            self.com_monitor.com.close()
            self.com_monitor.quit()
            self.bind_button.setText(u"打开设备")

    def uart_update_text(self,port,data):
        port = str(port)
        data = str(data)

        log_str = u"[%s]: %s" % (port,data)
        result_str = ''
        print log_str,

        if data[2:4] == '11':
            if len(data) == len("5C11000F0F0002040017CA"):
                self.send_cmd_max = self.send_cmd_max + 1
                if self.send_cmd_max >= 5:
                    result_str = u"NO TAG"
                    self.tag_status = TAG_IDLE
            else:
                if self.tag_status == TAG_SHOW:
                    if data[16:48] == '0'*32:
                        self.tag_status = TAG_SET
                    else:
                        self.tag_status = TAG_CLEAR
                if self.tag_status == TAG_CHECK:
                    if data[16:48] == '0'*32:
                        self.tag_status = TAG_SET
                    else:
                        # self.tag_status = TAG_IDLE
                        result_str = u'[%s]: 同步参数成功' % self.current_name
                        self.sync_fg_dict[self.current_name] = 1
                        self.tag_status   = TAG_SHOW
                        self.send_cmd_max = 0
                        self.current_name = None

        if data[2:4] == '10':
            if data[14:16] == '01':
                self.tag_status = TAG_CHECK
                self.send_cmd_max = 0

            if data[14:16] == '02':
                self.tag_status = TAG_IDLE
                self.send_cmd_max = 0
                result_str = u'此区域已经写过数据'

            if data[14:16] == '00':
                self.send_cmd_max = self.send_cmd_max + 1
                if self.send_cmd_max >= 5:
                    result_str = u'[%s]: 同步参数失败' % self.current_name
                    self.current_name = None
                    self.tag_status   = TAG_SHOW
                    self.send_cmd_max = 0

        if data[2:4] == '12':
            if data[14:16] == '01':
                self.tag_status = TAG_CHECK
                self.send_cmd_max = 0
            else:
                self.send_cmd_max = self.send_cmd_max + 1
                if self.send_cmd_max >= 5:
                    result_str = u'[%s]: 同步参数失败' % self.current_name
                    # self.tag_status = TAG_IDLE
                    self.current_name = None
                    self.tag_status   = TAG_SHOW
                    self.send_cmd_max = 0

        # 解析读取UID指令对应的返回
        print result_str
        logging.debug( u"%s %s" % (log_str, result_str) )
        self.browser.append(u"%s" % (log_str))
        if result_str:
            self.browser.append(u"%s" % result_str)
            self.browser.append(u'=================================================================')

    def exit(self):
        print "exit"
        self.close()

if __name__=='__main__':
    app = QApplication(sys.argv)
    datburner = rfid_debug()
    datburner.show()
    app.exec_()