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
from functools import partial
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
        self.a_phone_dict = {}
        self.d_phone_dict = {}
        self.addr_dict    = {u'爸爸':u'38',u'妈妈':u'39',u'爷爷':u'3A',
                             u'奶奶':u'3C',u'哥哥':u'3D',u'姐姐':u'3E'}
        self.sync_fg_dict = {}
        self.current_cmd  = None
        self.current_name = None

        self.setWindowTitle(u"话机 RFID 标签参数配置")

        self.connect_label = QLabel(u"连接:")
        self.connect_label.setFixedWidth(30)
        self.connect_label.setFixedHeight(30)
        self.led1          = LED(30)
        self.e_button      = QPushButton(u"退出")
        self.bind_button   = QPushButton(u"打开设备")
        self.read_id_button= QPushButton(u"读取卡号")
        self.id_edit       = QLineEdit()
        self.id_label      = QLabel(u"卡号:")
        self.sync_button   = QPushButton(u"写入数据")
        self.clear_button  = QPushButton(u"查看数据")

        e_layout = QGridLayout()
        e_layout.addWidget(self.connect_label,1,0)
        e_layout.addWidget(self.led1         ,1,1)

        m_layout = QHBoxLayout()
        m_layout.addLayout(e_layout)
        m_layout.addWidget(self.bind_button    )
        m_layout.addWidget(self.e_button       )

        b_layout = QHBoxLayout()
        b_layout.addWidget(self.id_label       )
        b_layout.addWidget(self.id_edit        )
        b_layout.addWidget(self.read_id_button )

        c_layout = QHBoxLayout()
        c_layout.addWidget(self.clear_button   )
        c_layout.addWidget(self.sync_button    )

        self.family_label=QLabel(u"亲属:")
        self.family_combo = QComboBox()
        self.family_combo.addItems([u'爸爸',u'妈妈',u'爷爷',u'奶奶',u'哥哥',u'姐姐'])
        self.f_phone_label=QLabel(u"电话:")
        self.f_phone_edit = QLineEdit(u'18576658098')
        self.f_phone_edit.setMaxLength(15)
        self.f_phone_button_a = QPushButton(u"添加")
        self.f_phone_button_d = QPushButton(u"移除")

        self.family_combo.setFont(QFont( "Roman times",CONF_FONT_SIZE,QFont.Bold))
        self.f_phone_edit.setFont(QFont( "Roman times",CONF_FONT_SIZE,QFont.Bold))
        self.id_edit.setFont(QFont( "Roman times",CONF_FONT_SIZE,QFont.Bold))

        g_hbox = QGridLayout()
        g_hbox.addWidget(self.family_label     ,1,0)
        g_hbox.addWidget(self.family_combo     ,1,1,1,2)
        g_hbox.addWidget(self.f_phone_label    ,1,3)
        g_hbox.addWidget(self.f_phone_edit     ,1,4)
        g_hbox.addWidget(self.f_phone_button_a ,1,5)
        g_hbox.addWidget(self.f_phone_button_d ,1,6)

        self.browser = QTextBrowser()

        box = QVBoxLayout()
        box.addLayout(m_layout)
        box.addLayout(b_layout)
        box.addLayout(g_hbox)
        box.addLayout(c_layout)
        box.addWidget(self.browser)

        self.setLayout(box)

        self.e_button.clicked.connect(self.exit)
        self.bind_button.clicked.connect(self.uart_auto_connect)
        self.sync_button.clicked.connect(self.tag_write_data_strat)
        self.clear_button.clicked.connect(self.tag_read_data_strat)
        self.read_id_button.clicked.connect(self.read_id)
        self.f_phone_button_a.clicked.connect(partial(self.f_phone_number_add_or_del, u"添加"))
        self.f_phone_button_d.clicked.connect(partial(self.f_phone_number_add_or_del, u"移除"))

        self.resize( 440, 400 )
        self.timer = QTimer()
        self.timer.timeout.connect(self.tag_auto_rdwr_data)

    def read_id(self):
        button_str = self.bind_button.text()
        if button_str == u"关闭设备":
            if self.tag_status == TAG_IDLE:
                self.current_cmd = u'id'
                self.uart_send_data("5C 13 00 0F 0F 00 00 13 CA")
            else:
                self.browser.append(u'请等待数据同步完成在操作软件！')
        else:
            self.browser.append(u"请先打开设备！")


    def f_phone_number_add_or_del(self,button_str):
        self.clear_show_message()
        name_str   = unicode(self.family_combo.currentText())
        iphone_str = str(self.f_phone_edit.text())
        dict_len = len(self.a_phone_dict)
        if button_str == u"添加":
            if self.a_phone_dict.has_key( name_str ) == False:
                self.a_phone_dict[name_str] = iphone_str
            if self.d_phone_dict.has_key( name_str ) == True:
                self.d_phone_dict.pop(name_str)
            self.sync_fg_dict[name_str] = 0
            self.current_cmd = u'add'

        if button_str == u"移除":
            if self.a_phone_dict.has_key( name_str ) == True:
                self.d_phone_dict[name_str] = ''
                self.a_phone_dict.pop(name_str)
                self.sync_fg_dict[name_str] = 0
                self.current_cmd = u'del'

        self.browser.append(u'=======================当前需要同步的号码如下====================')
        for item in self.a_phone_dict:
            self.browser.append(u" * [ %s ] : %s" % (item,self.a_phone_dict[item]))
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
        if len(phone) % 2 != 0:
            phone = phone + 'F'

        data_len = len( phone )
        for item in phone:
            if i <= data_len - 2:
                hex_h = (string.atoi(phone[i],16)<<4) & 0xF0
                hex_l = (string.atoi(phone[i+1],16) & 0x0F)
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
        name_str = self.name_to_hex(name)
        phone_str = self.phone_number_to_hex(phone)
        data     = name_str + 'F'*(16-len(name_str)) + phone_str + 'F'*(16-len(phone_str))
        crc_str  = cmd_str + sign_str + len_str + addr_str + ' ' + data
        crc      = self.get_cmd_crc(crc_str)
        cmd      = '5C' + crc_str + crc + 'CA'
        # print cmd
        return cmd

    def tag_auto_rdwr_data(self):
        if self.current_name == None:
            for item in self.sync_fg_dict:
                if self.sync_fg_dict[item] == 0:
                    self.current_name = item

        if self.tag_status == TAG_IDLE:
            self.browser.append(u'=================================================================')
            self.browser.append(u"退出操作！")
            self.browser.append(u'=================================================================')
            self.uart_send_data("5C 30 00 0F 0F 00 01 03 32 CA")

            for item in self.sync_fg_dict:
                self.sync_fg_dict[item] = 0
            self.sync_fg_dict = {}
            self.timer.stop()
        else:
            if self.current_name == None:
                self.tag_status = TAG_IDLE
                self.browser.append(u'=================================================================')
                self.browser.append(u"所有数据同步完成！")
                self.browser.append(u'=================================================================')
                self.uart_send_data("5C 30 00 0F 0F 00 01 01 30 CA")

                for item in self.sync_fg_dict:
                    self.sync_fg_dict[item] = 0
                # self.a_phone_dict   = {}
                self.sync_fg_dict = {}
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
                    if self.a_phone_dict[self.current_name] != '':
                        cmd = self.get_set_tag_cmd(self.current_name,self.a_phone_dict[self.current_name])
                    else:
                        self.tag_status == TAG_CLEAR

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
                # return cmd
                if cmd:
                    self.uart_send_data(cmd)
                    # self.browser.append(u"[STATUS = %d] CMD: %s" % (self.tag_status,cmd))

    def tag_write_data_strat(self):
        button_str = self.bind_button.text()

        if button_str == u"关闭设备":
            if self.tag_status == TAG_IDLE:
                self.tag_status   = TAG_SHOW
                self.send_cmd_max = 0
                for item in self.sync_fg_dict:
                    self.sync_fg_dict[item] = 0

                self.clear_show_message()
                # self.current_cmd = u'wr'
                self.browser.append(u'=======================当前需要同步的号码如下====================')
                for item in self.a_phone_dict:
                    self.browser.append(u" * [ %s ] : %s" % (item,self.a_phone_dict[item]))
                self.browser.append(u'=================================================================')
                self.timer.start(500)
            else:
                self.browser.append(u'请等待数据同步完成在操作软件！')
        else:
            self.browser.append(u"请先打开设备！")

    def tag_read_data_strat(self):
        button_str = self.bind_button.text()

        if button_str == u"关闭设备":
            if self.tag_status == TAG_IDLE:
                self.a_phone_dict = {}
                self.tag_status   = TAG_CHECK
                self.send_cmd_max = 0
                for item in self.addr_dict:
                    self.sync_fg_dict[item] = 0

                self.clear_show_message()
                self.current_cmd = u'rd'
                self.browser.append(u'=========================当前查询的号码如下======================')
                self.timer.start(500)
            else:
                self.browser.append(u'请等待数据同步完成在操作软件！')
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
            # print "SEARCH COM LIST: ",

            self.browser.append(u"SEARCH COM LIST: ")
            for item in ser_list:
                self.browser.append(" * %s " % item)
            self.browser.append(u'=================================================================')
            # 发送链接指令
            for item in ser_list:
                # self.browser.append(u' * [ %s ] SEND CMD' % item)
                try:
                    ser = serial.Serial( ports_dict[item], 115200, timeout = 0.2)
                except serial.SerialException:
                    pass

                if ser:
                    if ser.isOpen() == True:
                        ser.write( connect_cmd )
                        cmd_result = ser.readall()
                        # self.browser.append(u'REV  CMD: %s' % cmd_result)
                        print cmd_result
                        if cmd_result != None and cmd_result != '':
                            for i in cmd_result:
                                cmd_str = hex_decode.r_machine(i)
                            print cmd_str
                            # self.browser.append(u' * [ %s ] REV  CMD: %s' % (item,cmd_str))
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
        if self.current_cmd == u'id':
            if data[2:4] == '13':
                device_id = data[14:14+8]
                device_id = device_id[6:8] + device_id[4:6] + device_id[2:4] + device_id[0:2]
                device_id = string.atoi(device_id,16)
                if device_id == 0:
                    self.id_edit.setText(u"NO TAG" )
                else:
                    self.uart_send_data("5C 30 00 0F 0F 00 01 01 30 CA")
                    self.id_edit.setText(u"%010u" %device_id )

        if self.current_cmd == u'add':
            if data[2:4] == '11':
                if len(data) == len("5C11000F0F0002040017CA"):
                    if data[16:18] == '00':
                        self.send_cmd_max = self.send_cmd_max + 1
                        if self.send_cmd_max >= 3:
                            result_str = u"NO TAG"
                            self.tag_status = TAG_IDLE
                    if data[16:18] == '03':
                        result_str = u"ERROR TAG"
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
                            phone = data[32:32+15]
                            real_phone = ''
                            for item in phone:
                                if item != 'F':
                                    real_phone = real_phone + item
                            result_str = u' * [ %s ] : 同步数据成功：%s' % (self.current_name,real_phone)
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
                    if self.send_cmd_max >= 3:
                        result_str = u' * [ %s ] : 同步数据失败' % self.current_name
                        self.current_name = None
                        self.tag_status   = TAG_SHOW
                        self.send_cmd_max = 0

            if data[2:4] == '12':
                if data[14:16] == '01':
                    self.tag_status = TAG_CHECK
                    self.send_cmd_max = 0
                else:
                    self.send_cmd_max = self.send_cmd_max + 1
                    if self.send_cmd_max >= 3:
                        result_str = u' * [ %s ] : 同步数据失败' % self.current_name
                        # self.tag_status = TAG_IDLE
                        self.current_name = None
                        self.tag_status   = TAG_SHOW
                        self.send_cmd_max = 0

        if self.current_cmd == u'del':
            if data[2:4] == '11':
                if len(data) == len("5C11000F0F0002040017CA"):
                    if data[16:18] == '00':
                        self.send_cmd_max = self.send_cmd_max + 1
                        if self.send_cmd_max >= 3:
                            result_str = u"NO TAG"
                            self.tag_status = TAG_IDLE
                    if data[16:18] == '03':
                        result_str = u"ERROR TAG"
                        self.tag_status = TAG_IDLE
                else:
                    if self.tag_status == TAG_SHOW:
                        if data[16:48] == '0'*32:
                            self.tag_status = TAG_SET
                        else:
                            self.tag_status = TAG_CLEAR
                    if self.tag_status == TAG_CHECK:
                        if data[16:48] == '0'*32:
                            self.sync_fg_dict[self.current_name] = 1
                            self.tag_status   = TAG_CHECK
                            self.send_cmd_max = 0
                            result_str = u' * [ %s ] : 清除数据成功！' % (self.current_name)
                            self.current_name = None
                        else:
                            self.tag_status   = TAG_CLEAR

            if data[2:4] == '12':
                if data[14:16] == '01':
                    self.tag_status = TAG_CHECK
                    self.send_cmd_max = 0
                else:
                    self.send_cmd_max = self.send_cmd_max + 1
                    if self.send_cmd_max >= 3:
                        result_str = u' * [ %s ] : 同步数据失败' % self.current_name
                        result_str = u"NO TAG"
                        self.tag_status = TAG_IDLE

        if self.current_cmd == u'rd':
            if data[2:4] == '11':
                if len(data) == len("5C11000F0F0002040017CA"):
                    self.send_cmd_max = self.send_cmd_max + 1
                    if self.send_cmd_max >= 3:
                        result_str = u"NO TAG"
                        self.tag_status = TAG_IDLE
                else:
                    if self.tag_status == TAG_CHECK:
                        if data[16:48] == '0'*32 :
                            self.tag_status = TAG_CHECK
                            self.send_cmd_max = self.send_cmd_max + 1
                            if self.send_cmd_max >= 2:
                                result_str = u' * [ %s ] : 读取数据成功: NONE' % self.current_name
                                self.sync_fg_dict[self.current_name] = 1
                                self.send_cmd_max = 0
                                self.current_name = None
                        else:
                            # self.tag_status = TAG_IDLE
                            phone = data[32:32+15]
                            real_phone = ''
                            for item in phone:
                                if item != 'F':
                                    real_phone = real_phone + item
                            result_str = u' * [ %s ] : 读取数据成功：%s' % (self.current_name,real_phone)
                            self.a_phone_dict[self.current_name]   = real_phone

                            self.sync_fg_dict[self.current_name] = 1
                            self.tag_status   = TAG_CHECK
                            self.send_cmd_max = 0
                            self.current_name = None
        # 解析读取UID指令对应的返回
        print result_str
        logging.debug( u"%s %s" % (log_str, result_str) )
        # self.browser.append(u"%s" % (log_str))
        if result_str:
            self.browser.append(u"%s" % result_str)

    def exit(self):
        print "exit"
        self.close()

if __name__=='__main__':
    app = QApplication(sys.argv)
    datburner = rfid_debug()
    datburner.show()
    app.exec_()