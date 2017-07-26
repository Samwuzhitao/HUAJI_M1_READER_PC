# -*- coding: utf-8 -*-
"""
Created on Sat Apr 22 10:59:35 2017

@author: john
"""
from PyQt4.QtCore import *
from PyQt4.QtGui  import *

class LED(QLabel):
    def __init__(self,x,parent=None):
        super(LED, self).__init__(parent)
        self.led_b = QImage('./data/ico/ledlightblue.ico')
        self.led_g = QImage('./data/ico/ledgreen.ico')
        self.led_r = QImage('./data/ico/ledred.ico')
        self.led_y = QImage('./data/ico/ledgray.ico')
        self.color_dict = {'blue':self.led_b,'green':self.led_g,'red':self.led_r,'gray':self.led_y}
        self.resize(x,x)
        self.setAlignment(Qt.AlignCenter)
        self.setPixmap(QPixmap.fromImage(self.color_dict['gray']).scaled(self.size(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def set_color(self,color):
        self.setPixmap(QPixmap.fromImage(self.color_dict[color]).scaled(self.size(),
                Qt.KeepAspectRatio, Qt.SmoothTransformation))
