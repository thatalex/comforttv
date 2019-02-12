# -*- coding: utf-8 -*-
import sys
from datetime import datetime
from datetime import timedelta
from urlparse import parse_qsl

import portal
import xbmc
import xbmcgui
import xbmcplugin

PARAM_ACTION = 'action'


class Addon:
    str_title_ctv = 'Comfort TV'
    str_tv = 'TV'
    str_internet_tv = 'Internet TV'
    str_archive = 'Archive'

    def _set_localization(self, kodi_addon):
        # keep default values if kodi_addon is stub
        if kodi_addon.getLocalizedString(30000) == '':
            return
        self.str_title_ctv = kodi_addon.getLocalizedString(30000)
        self.str_tv = kodi_addon.getLocalizedString(30001)
        self.str_internet_tv = kodi_addon.getLocalizedString(30002)
        self.str_archive = kodi_addon.getLocalizedString(30003)

    def __init__(self, url, handle, mac_orig, kodi_addon):
        self.handle = handle
        self.url = url
        self.mac = mac_orig
        self._set_localization(kodi_addon)

        path = kodi_addon.getAddonInfo('path')
        if path == '':
            path = '.'
        addon_path = xbmc.translatePath(path).decode('utf-8')
        self.loader = portal.Loader(self.mac, addon_path)
        self.channels = dict()
        self.internet_channels = dict()
        try:
            for line in self.loader.get_channels():
                if line != '':
                    e = portal.Element.parse(line)
                    self.channels[e.id] = line
        except Exception as error:
            xbmcgui.Dialog().ok(self.str_title_ctv, error.message)
            sys.exit()

        try:
            for line in self.loader.get_internet_channels():
                if line != '':
                    e = portal.Element.parse(line)
                    self.internet_channels[e.id] = line
        except Exception as error:
            xbmcgui.Dialog().ok(self.str_title_ctv, error.message)
            sys.exit()

    def _list_main(self):
        items = [{'name': self.str_tv, 'url': '{0}?action=tv'.format(self.url)},
                 {'name': self.str_internet_tv, 'url': '{0}?action=internet_tv'.format(self.url)}]

        listing = []

        for item in items:
            list_item = xbmcgui.ListItem(label=item['name'])
            list_item.setProperty('IsPlayable', 'false')
            is_folder = True
            listing.append((item['url'], list_item, is_folder))
        xbmcplugin.addDirectoryItems(self.handle, listing, len(listing))

        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_UNSORTED)

        xbmcplugin.endOfDirectory(self.handle)

    def _action_tv(self):
        listing = []
        epg = self.loader.get_epg(self.channels.keys(), datetime.today())
        for ch_id in self.channels.keys():
            channel = self.channels.get(ch_id)
            ch_epg = epg.get(ch_id)
            cur_playing = ''
            plot = []
            for epg_item in ch_epg:
                time = datetime.fromtimestamp(float(epg_item['stop_timestamp']))
                if datetime.today() < time:
                    info = ''.join(
                        ['[LIGHT]', epg_item['t_time'], ' - ', epg_item['t_time_to'], ':[/LIGHT]  ', epg_item['name'],
                         '[CR]'])
                    plot.append(info.encode('utf-8'))
                    if cur_playing is '':
                        cur_playing = ''.join(['[LIGHT](', epg_item['name'], ')[/LIGHT]'])
            self.channels[ch_id]['cur_playing'] = cur_playing
            item = xbmcgui.ListItem(label=''.join(['[B]', channel['name'], '[/B]     ', cur_playing]))
            item.setProperty('ch_id', ch_id)
            item.setProperty('IsPlayable', 'true')
            item.setInfo('video', {'plot': ''.join(plot)})
            item.addContextMenuItems(self._get_context_menu(ch_id))
            listing.append((channel['cmd'], item, False))
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.addDirectoryItems(self.handle, listing, len(listing))
        xbmcplugin.endOfDirectory(self.handle, updateListing=True, cacheToDisc=False)

    def _get_context_menu(self, ch_id):
        listing = []
        url = '{0}?action=action_archive_dates&id={1}'.format(self.url, ch_id)
        action = 'Container.Update(' + url + ', replace)'
        item = (self.str_archive, action)
        listing.append(item)
        return listing

    def _action_archive_dates(self, ch_id):
        listing = []
        now = datetime.now()
        for i in range(0, 7, 1):
            day = now - timedelta(days=i)
            name = ''.join(
                [str(day.day).zfill(2), ' ', xbmc.getLocalizedString(day.month + 20), ' ', str(day.year)])
            list_item = xbmcgui.ListItem(label=name)
            list_item.setProperty('IsPlayable', 'false')
            url = '{0}?action=action_ch_archive&id={1}&day_ago={2}'.format(self.url, ch_id, i)
            listing.append((url, list_item, True))

        xbmcplugin.addDirectoryItems(self.handle, listing, len(listing))
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(self.handle, updateListing=False, cacheToDisc=False)

    def _action_ch_archive(self, ch_id, day_ago):
        listing = []

        arch_epg = self.loader.download_channel_epg(ch_id, datetime.today() - timedelta(days=int(day_ago)))
        for i, item in enumerate(arch_epg):
            info = ''.join(['[B]', item['name'], '[/B] [LIGHT](', item['t_time'], ' - ',
                                                        item['t_time_to'], ')[/LIGHT]'])
            list_item = xbmcgui.ListItem(label=info)
            list_item.setProperty('IsPlayable', 'true')
            list_item.setInfo('video', {'plot': info})
            url = '{0}?action=ch_archive_play&id={1}'.format(self.url, item['id'])
            listing.append((url, list_item, False))

        xbmcplugin.addDirectoryItems(self.handle, listing, len(listing))
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(self.handle, updateListing=False, cacheToDisc=False)

    def _action_internet_tv(self):
        listing = []

        for ch in self.internet_channels.values():
            list_item = xbmcgui.ListItem(label=ch['name'])
            list_item.setProperty('IsPlayable', 'true')
            is_folder = False
            listing.append((ch['cmd'], list_item, is_folder))
        xbmcplugin.addDirectoryItems(self.handle, listing, len(listing))
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.endOfDirectory(self.handle, updateListing=True, cacheToDisc=False)

    def _action_play_video(self, path):
        play_item = xbmcgui.ListItem(path=path)
        xbmcplugin.setResolvedUrl(self.handle, True, listitem=play_item)

    def router(self, arg):
        params = dict(parse_qsl(arg[1:]))
        if params:
            if params[PARAM_ACTION] == 'action_archive_dates':
                self._action_archive_dates(params['id'])
            if params[PARAM_ACTION] == 'action_ch_archive':
                self._action_ch_archive(params['id'], params['day_ago'])
            if params[PARAM_ACTION] == 'ch_archive_play':
                data = self.loader.get_archive_video_url(params['id'])
                self._action_play_video(data['cmd'])
        else:
            self._action_tv()
