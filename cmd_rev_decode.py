
# -*- coding: utf-8 -*-
"""
Created on Sat Apr 22 10:59:35 2017

@author: john
"""
import string

R_STATUS_HEADER = 0
R_STATUS_CMD    = 1
R_STATUS_SIGN   = 2
R_STATUS_LEN    = 3
R_STATUS_DTAT   = 4
R_STATUS_CRC    = 5
R_STATUS_END    = 6

class HexDecode():
    def __init__(self):
        self.init()
        self.cmd_m   = {
            R_STATUS_HEADER : self.r_header ,
            R_STATUS_CMD    : self.r_cmd    ,
            R_STATUS_SIGN   : self.r_sign   ,
            R_STATUS_LEN    : self.r_len    ,
            R_STATUS_DTAT   : self.r_data   ,
            R_STATUS_CRC    : self.r_crc_fun,
            R_STATUS_END    : self.r_end
        }

    def init(self):
        self.status  = 0
        self.header  = ""
        self.cmd     = ""
        self.sign_c  = 0
        self.sign    = ""
        self.len     = 0
        self.len_str = ""
        self.data    = ""
        self.data_c  = 0
        self.crc     = 0
        self.crc_str = ""
        self.end     = ""
        self.end     = ""

    def r_header(self,x):
        if x == "5C":
            self.header =  x
            self.status = R_STATUS_CMD

    def r_cmd(self,x):
        # print 'header : %s ' % self.header
        self.crc    = self.crc ^ string.atoi(x, 16)
        self.cmd    = x
        self.sign_c = 4
        self.status = R_STATUS_SIGN

    def r_sign(self,x):
        # print 'cmd : %s ' % self.cmd
        self.crc    = self.crc ^ string.atoi(x, 16)
        self.sign =  self.sign + x
        self.sign_c = self.sign_c - 1
        if self.sign_c == 0:
            self.status = R_STATUS_LEN

    def r_len(self,x):
        # print 'sign : %s ' %  self.sign
        self.crc  = self.crc ^ string.atoi(x, 16)
        self.len_str= x
        self.len    = string.atoi(x, 16)
        if self.len != 0:
            self.status = R_STATUS_DTAT
        else:
            self.status = R_STATUS_CRC

    def r_data(self,x):
        # print self.len
        self.crc  = self.crc ^ string.atoi(x, 16)
        self.data_c = self.data_c + 1
        self.data = self.data + x
        if self.data_c == self.len:
            self.status = R_STATUS_CRC

    def r_crc_fun(self,x):
        # print 'data : %s ' %  self.data
        self.crc_str = x
        # print "c_crc = %02X r_crc = %s" % (self.crc,x)
        if self.crc == string.atoi(x, 16):
            self.status = R_STATUS_END
        else:
            self.init()

    def r_end(self,x):
        # print self.data
        self.end = x
        if x != "CA":
            self.init()
        else:
            self.status = R_STATUS_HEADER
            cmd_str = self.header + self.cmd + self.sign + self.len_str + \
                      self.data + self.crc_str + self.end
            return cmd_str

    def get_str(self,mode):
        self.crc = 0
        crc_data = self.len_str + self.data
        # print crc_data
        i = 0
        crc_len = len( crc_data )

        for item in crc_data:
            if i <= crc_len-2:
                self.crc  = self.crc ^ string.atoi(crc_data[i:i+2], 16)
                # print "c_crc = %02X crc_in = %s" % (self.crc,crc_data[i:i+2])
            i = i + 2
        self.crc_str = "%02X" % self.crc
        # print self.crc_str

        data_str = ''
        i = 0
        for item in self.data:
            if i % 2 == 0 and i > 0:
                data_str = data_str + ' '
            data_str = data_str + item
            i = i + 1

        returm_str = self.header
        if mode == 0:
            returm_str = self.header + self.len_str + self.cmd_str + \
                  self.op_str + data_str + self.crc_str + self.end
        else:
            color_len_str = "<font color=lightgreen> %s</font>" % self.len_str
            returm_str    = returm_str + color_len_str
            color_cmd_str = "<font color=red> %s</font>" % self.cmd_str
            returm_str    = returm_str + color_cmd_str
            color_op_str  = "<font color=green> %s</font>" % self.op_str
            returm_str    = returm_str + color_op_str
            if data_str:
                data_str   = "<font color=blue> %s</font>" % data_str
                returm_str = returm_str + data_str
            color_crc_str  = "<font color=red> %s </font>" % self.crc_str
            returm_str = returm_str + color_crc_str
            returm_str = returm_str + self.end
        return returm_str

    def format_print(self):
        print "header = %s" % self.header
        print "len    = %s" % self.len_str
        print "cmd    = %s" % self.cmd_str
        print "type   = %s" % self.op_str
        print "data   = %s" % self.data
        print "crc    = %s" % self.crc_str
        print "end    = %s" % self.end
        # self.clear()

    def r_machine(self,x):
        if x:
            char = "%02X" % ord(x)
            # print "status = %d, char = %s" % (self.status, char )
            cmd_str = self.cmd_m[self.status](char)
            # print cmd_str
            return cmd_str

if __name__=='__main__':
    cmd_str = "5C 40 00 F0 F0 00 1E E0 D9 B4 F3 00 01 00 5A 4C 2D 52 50 35 35 31 2D 4D 41 49 4E 2D 46 D1 B6 C1 AA B9 C9 B7 DD 72 CA"
    hex_decode = HexDecode()
    print u"测试指令：%s" % cmd_str
    cmd_str = cmd_str.replace(' ','')
    cmd_str = cmd_str.decode("hex")
    for i in cmd_str:
        cmd_str = hex_decode.r_machine(i)
        if cmd_str:
            print cmd_str,len(cmd_str)/2