# -*- coding: utf-8 -*-
import sys
from datetime import datetime
from datetime import timedelta
from multiprocessing.dummy import Pool
from urlparse import parse_qsl

import portal
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

_addon = xbmcaddon.Addon()
_addon_path = xbmc.translatePath(_addon.getAddonInfo('profile')).decode('utf-8')

STR_TITLE_CTV = _addon.getLocalizedString(30000)

STR_TV = _addon.getLocalizedString(30001)

STR_INTERNET_TV = _addon.getLocalizedString(30002)

STR_ARCHIVE = _addon.getLocalizedString(30003)

PARAM_ACTION = 'action'

ACTION_PREVIOUS_MENU = 10

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2

ACTION_MOVE_UP = 3

ACTION_MOVE_DOWN = 4

ACTION_PAGE_UP = 5

ACTION_PAGE_DOWN = 6

ACTION_SELECT_ITEM = 7

ACTION_HIGHLIGHT_ITEM = 8

ACTION_PARENT_DIR = 9

ACTION_SHOW_INFO = 11


class MainWindow(xbmcgui.Window):
    def __init__(self):
        self.strActionInfo = xbmcgui.ControlLabel(250, 80, 200, 200, '', 'font14', '0xFFBBBBFF')
        self.addControl(self.strActionInfo)
        self.strActionInfo.setLabel('Push BACK to quit')
        self.list = xbmcgui.ControlList(200, 150, 300, 400)
        self.addControl(self.list)
        self.list.addItem('Item 1')
        self.list.addItem('Item 2')
        self.list.addItem('Item 3')
        self.setFocus(self.list)

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU:
            self.close()
        if action == ACTION_MOVE_UP:
            pos = self.list.getSelectedPosition()
            self.strActionInfo.setLabel(str(pos))
            self.list.getSelectedItem().setLabel('not selected')
            if pos < 1:
                self.list.selectItem(2)
            else:
                self.list.selectItem(pos - 1)
            self.list.getSelectedItem().setLabel('selected')
        if action == ACTION_MOVE_DOWN:
            pos = self.list.getSelectedPosition()
            self.strActionInfo.setLabel(str(pos))
            self.list.getSelectedItem().setLabel('not selected')
            if pos >= len(self.list):
                self.list.selectItem(pos + 1)
            else:
                self.list.selectItem(0)
            self.list.getSelectedItem().setLabel('selected')

        self.strActionInfo.setLabel('Action is: ' + str(action))

    def onControl(self, control):
        if control == self.list:
            item = self.list.getSelectedItem()

    def message(self, message):
        dialog = xbmcgui.Dialog()
        dialog.ok(" My message title", message)


class ArchDateClass(xbmcgui.Window):
    def __init__(self):
        self.addControl(xbmcgui.ControlImage(0, 0, 800, 600, 'background.png'))
        self.strActionInfo = xbmcgui.ControlLabel(200, 60, 200, 200, '', 'font14', '0xFFBBFFBB')
        self.addControl(self.strActionInfo)
        self.strActionInfo.setLabel('Push BACK to return to the first window')
        self.strActionInfo = xbmcgui.ControlLabel(240, 200, 200, 200, '', 'font13', '0xFFFFFF99')
        self.addControl(self.strActionInfo)
        self.strActionInfo.setLabel('This is the child window')

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU:
            self.close()


main = MainWindow()
try:
    main.doModal()
except Exception as e:
    xbmcgui.Dialog().ok('Error', e.message)
del main
