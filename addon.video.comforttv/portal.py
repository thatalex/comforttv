# -*- coding: utf-8 -*-
import urllib2
import json
import os
from datetime import datetime
from threading import Semaphore, Thread

import xbmc
import xbmcgui

BUFFER_SIZE = 2048

DATE_FORMAT = '%Y-%m-%d'

DATA = 'data'

JS = 'js'

UTF8 = 'utf8'

TITLE_GET_URL = 'get url'

TITLE_PARSE_ERROR = 'Parse error'

TITLE_PARSE_ARCH_EPG = 'Parse arch epg'

CACHE_PATH = 'cache'

CACHE_EPG = 'epg.txt'

CACHE_SHORT_EPG = 'shortepg_id({0}).txt'

CACHE_CH_EPG = 'epg_id({0})_dayago({1}).txt'

CACHE_INTERNET_CHANNELS = 'inet_channels.txt'

CACHE_TV_CHANNELS = 'channels.txt'

ERROR_DELETE = 'Can''t delete {0}: {1}'

ERROR_WRITE = 'Can''t write {0}: {1}'

ERROR_READ = 'Can''t read {0}: {1}'

THREADS_COUNT = 20


class Element:
    def __init__(self):
        pass

    name = ''
    cmd = ''
    cur_playing = ''
    id = ''

    def __str__(self):
        return (''.join(['name: ', self.name, ', cmd: ', self.cmd, ', cur_playing: ', self.cur_playing])).encode('utf8')

    @staticmethod
    def parse(row):
        element = Element()
        element.name = row['name']
        element.cmd = row['cmd']
        element.cur_playing = row['cur_playing']
        element.id = row['id']
        return element


class Loader:
    def __init__(self, mac, path):
        self.path = os.path.join(path, CACHE_PATH)
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        self.mac = mac
        self.clean_cache()

    LIST_URL = 'http://komfort.iptv.by/portal/server/load.php?type=itv&action=get_all_channels&quality=high' \
               '&include_censored=true'

    INET_LIST_URL = 'http://komfort.iptv.by/portal/server/load.php?type=tvint&action=get_all_channels'

    SHORT_EPG_URL = 'http://komfort.iptv.by/portal/server/load.php?type=itv&action=get_short_epg&ch_id={0}' \
                    '&JsHttpRequest=1-xml'
    EPG_URL = 'http://komfort.iptv.by/portal/server/load.php?type=epg&action=get_simple_data_table&ch_id={0}&date={1}' \
              '&p=1&page_items=100&JsHttpRequest=1-xml'

    ARCH_TV_URL = 'http://komfort.iptv.by/portal/server/load.php?type=tv_archive&action=create_link&cmd=auto/media/{0}' \
                  '.mpg&forced_storage=undefined&JsHttpRequest=1-xml'

    def clean_cache(self):
        """
        clean yesterday cache
        """
        if os.path.exists(self.path):
            for f in os.listdir(self.path):
                full_path = os.path.join(self.path, f)
                if os.path.isfile(full_path):
                    if not self._is_recent(full_path):
                        try:
                            os.remove(full_path)
                        except Exception as e:
                            xbmc.log(ERROR_DELETE.format(full_path, e.message), xbmc.LOGERROR)

    def _is_recent(self, full_path):
        """
        Returns True if file was last time modified today

        :param full_path: full path to file
        :return: bool -- ``True`` or ``False``
        """
        if os.path.isfile(full_path):
            # delete file less than 100 bytes
            if os.path.getsize(full_path) < 100:
                os.remove(full_path)
                return False
            else:
                last_edit = datetime.fromtimestamp(os.path.getmtime(full_path))
                today = datetime.today()
                return last_edit.day == today.day and last_edit.month == today.month and last_edit.year == today.year
        return False

    def _getOpener(self):
        opener = urllib2.build_opener()
        opener.addheaders.append(('Authorization', 'Bearer 790AB725CC9EDB25A261A99FD4D68B01'))
        opener.addheaders.append(('Cookie', 'mac=' + self.mac))
        return opener

    def _get_content(self, url, filename):
        result = None
        try:
            content = self._load_content(filename)
            if content is None:
                opener = self._getOpener()
                content = opener.open(url).read()
                self._save_content(filename, content)
            result = content.decode(UTF8)
        except Exception as e:
            xbmc.log(ERROR_READ.format(filename, e.message), xbmc.LOGERROR)
            xbmcgui.Dialog().ok(TITLE_GET_URL, ''.join([e.message, ': ', url]))
        return result

    def _parse(self, content):
        result = None
        try:
            if content is not None:
                result = json.loads(content)[JS]
        except ValueError as e:
            xbmc.log(ERROR_READ.format(filename, e.message), xbmc.LOGERROR)
            xbmcgui.Dialog().ok(TITLE_PARSE_ERROR, e.message)
        return result

    def _parse_epg(self, content):
        result = None
        try:
            if content is not None:
                result = json.loads(content)
        except ValueError as e:
            xbmc.log(ERROR_READ.format(filename, e.message), xbmc.LOGERROR)
            xbmcgui.Dialog().ok(TITLE_PARSE_ERROR, e.message)
        return result

    def _parse_data(self, content):
        result = None
        try:
            if content is not None:
                result = json.loads(content)[JS][DATA]
        except ValueError as e:
            xbmc.log(ERROR_READ.format(filename, e.message), xbmc.LOGERROR)
            xbmcgui.Dialog().ok(TITLE_PARSE_ERROR, e.message)
        return result

    def get_short_epg(self, ch_id):
        """
        Returns short epg for given channel

        :param ch_id: channel's id
        :return: list -- ``epg data``
        """
        content = self._get_content(self.SHORT_EPG_URL.format(ch_id), CACHE_SHORT_EPG.format(ch_id))
        result = list()
        try:
            for e in json.loads(content)[JS]:
                result.append(''.join([e['t_time'], ' - ', e['t_time_to'], ': ', e['name']]))
            return result
        except ValueError as e:
            xbmc.log(ERROR_READ.format(filename, e.message), xbmc.LOGERROR)
            xbmcgui.Dialog().ok(TITLE_PARSE_ARCH_EPG, e.message)

    def _download_epg(self, ch_ids, date):
        semaphore = Semaphore(THREADS_COUNT)
        threads = []
        epg = dict()
        for ch_id in ch_ids:
            thread = Thread(target=self._add_ch_epg, args=(epg, ch_id, date, semaphore))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        return epg

    def _add_ch_epg(self, epg, ch_id, date, semaphore):
        semaphore.acquire()
        try:
            epg[ch_id] = self.download_channel_epg(ch_id, date)
        finally:
            semaphore.release()

    def get_epg(self, ch_ids, date):
        """
        Returns epg for channels by given date

        :param ch_ids: array of channel's id
        :param date: date for epg retrieving
        :return: dict -- ``epg data``
        """
        content = self._load_content(CACHE_EPG)
        if content is None:
            epg = self._download_epg(ch_ids, date)
            content = json.dumps(epg)
            self._save_content(CACHE_EPG, content)
        content = content.decode(UTF8)
        return self._parse_epg(content)

    def download_channel_epg(self, ch_id, date):
        """
        Returns epg for channel by given date

        :param ch_id: id of channel
        :param date: date for epg retrieving
        :return: dict -- ``epg data``
        """
        opener = self._getOpener()
        content = opener.open(self.EPG_URL.format(ch_id, date.strftime(DATE_FORMAT))).read()
        content = content.decode(UTF8)
        return self._parse_data(content)

    def get_archive_video_url(self, ch_id):
        """
        Returns url of archived video

        :param ch_id: id of archived video
        :return: url
        """
        opener = self._getOpener()
        content = opener.open(self.ARCH_TV_URL.format(ch_id)).read()
        content = content.decode(UTF8)
        return self._parse(content)

    def get_channels(self):
        """
        Returns list of channels

        :return: list
        """
        return self._parse_data(self._get_content(self.LIST_URL, CACHE_TV_CHANNELS))

    def get_internet_channels(self):
        """
        Returns list of internet channels

        :return: list
        """
        return self._parse_data(self._get_content(self.INET_LIST_URL, CACHE_INTERNET_CHANNELS))

    def _load_content(self, filename):
        result = None
        full_path = os.path.join(self.path, filename)
        if self._is_recent(full_path):
            arr = []
            try:
                f = open(full_path)
                line = f.readline(BUFFER_SIZE)
                while line:
                    arr.append(line)
                    line = f.readline(BUFFER_SIZE)
                f.close()
                result = ''.join(arr)
            except Exception as e:
                xbmc.log(ERROR_READ.format(filename, e.message), xbmc.LOGERROR)
        return result

    def _save_content(self, filename, content):
        try:
            f = open(os.path.join(self.path, filename), "w+")
            f.write(content)
            f.close()
        except Exception as e:
            xbmc.log(ERROR_WRITE.format(filename, e.message), xbmc.LOGERROR)
