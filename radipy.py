import os
import datetime
import subprocess
import sys
import time
import base64
import asyncio
from xml.etree import ElementTree as ET

import requests
import click
from prettytable import PrettyTable
import threading


# http://stackoverflow.com/questions/4995733/how-to-create-a-spinning-command-line-cursor-using-pythonのパクリ
class Spinner:
    busy = False
    delay = 0.5

    @staticmethod
    def spinning_cursor():
        while 1:
            for cursor in '|/-\\':
                yield cursor

    def __init__(self, delay=None):
        self.spinner_generator = self.spinning_cursor()
        if delay and float(delay):
            self.delay = delay

    def spinner_task(self):
        while self.busy:
            sys.stdout.write(next(self.spinner_generator))
            sys.stdout.flush()
            time.sleep(self.delay)
            sys.stdout.write('\b')
            sys.stdout.flush()

    def start(self):
        self.busy = True
        threading.Thread(target=self.spinner_task).start()

    def stop(self):
        self.busy = False
        time.sleep(self.delay)


class Response(object):
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            self.__setattr__(k, v)


class Radipy(object):
    player_url = 'http://radiko.jp/apps/js/flash/myplayer-release.swf'
    fms1_url = 'https://radiko.jp/v2/api/auth1_fms'
    fms2_url = 'https://radiko.jp/v2/api/auth2_fms'
    LANG = 'ja_JP.utf8'
    date = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d-%H')
    playerfile='./tmp/player.%s.swf' % date
    keyfile = './tmp/authkey.%s.jpg' % date
    playlistfile = './tmp/playlist.%s.m3u8' % date
    auth_response = Response()
    auth_success_response = Response()
    partialkey = ''
    stream_url = ''
    area_id = ''
    title = ''
    output_path = './output'

    def __init__(self, station_id, ft):
        self.station_id = station_id
        self.ft = ft

    @staticmethod
    def clear():
        subprocess.call('rm -v ./tmp/*.jpg', shell=True)
        subprocess.call('rm -v ./tmp/*.swf', shell=True)

    def authenticate(self):
        self._get_playerfile()
        self._get_keyfile()
        self._get_auth1()
        self._generate_particlekey()
        self._get_auth2()
        print('--------------------------')
        print('authentication success.')

    def get_channels(self):
        self.authenticate()
        self._get_area_id()
        self._get_area_channels()

    def create(self):
        self.authenticate()
        self._get_area_id()
        self._get_stream_url()
        spinner = Spinner()
        sys.stdout.write("Now Downloading...")
        spinner.start()
        if self._create_aac():
            sys.stdout.write('finish!!')
        else:
            sys.stdout.write('failed!!')
        spinner.stop()

    def _get_playerfile(self):
        if not os.path.exists(self.playerfile):
            print('create playerFile...')
            res = requests.get(self.player_url)
            if res.status_code == 200:
                with open(self.playerfile, 'wb') as file:
                    file.write(res.content)
                if not os.path.exists(self.playerfile):
                    print('PlayerFile is not created.')

    def _get_keyfile(self):
        if not os.path.exists(self.keyfile):
            print('create KeyFile...')
            subprocess.call('swfextract -b 12 {} -o {}'.format(self.playerfile, self.keyfile), shell=True)
            if not os.path.exists(self.keyfile):
                print('Keyfile is not created.')

    def _get_auth1(self):
        print('access auth1_fms...')
        headers = {
            'Host': 'radiko.jp',
            'pragma': 'no-cache',
            'X-Radiko-App': 'pc_ts',
            'X-Radiko-App-Version': '4.0.0',
            'X-Radiko-User': 'test-stream',
            'X-Radiko-Device': 'pc'
        }
        res = requests.post(url=self.fms1_url, headers=headers)
        self.auth_response.body = res.text
        self.auth_response.headers = res.headers
        self.auth_response.authtoken = self.auth_response.headers['x-radiko-authtoken']
        self.auth_response.offset = int(self.auth_response.headers['x-radiko-keyoffset'])
        self.auth_response.length = int(self.auth_response.headers['x-radiko-keylength'])

    def _generate_particlekey(self):
        print('generate particleKey...')
        f = open(self.keyfile, 'rb+')
        f.seek(self.auth_response.offset)
        data = f.read(self.auth_response.length)
        self.partialkey = base64.b64encode(data)

    def _get_auth2(self):
        print('access auth2_fms...')
        headers ={
          'pragma': 'no-cache',
          'X-Radiko-App': 'pc_ts',
          'X-Radiko-App-Version': '4.0.0',
          'X-Radiko-User': 'test-stream',
          'X-Radiko-Device': 'pc',
          'X-Radiko-Authtoken': self.auth_response.authtoken,
          'X-Radiko-Partialkey': self.partialkey,
        }
        res = requests.post(url=self.fms2_url, headers=headers)
        self.auth_success_response.body = res.text
        self.auth_success_response.headers = res.headers

    def _get_area_id(self):
        area = self.auth_success_response.body.strip().split(',')
        self.area_id = area[0]
        print('area_id: %s' % self.area_id)

    def _get_area_channels(self):
        area_api_url = "http://radiko.jp/v2/api/program/today"
        params = {'area_id': self.area_id}
        res = requests.get(url=area_api_url, params=params)
        channels_xml = res.content
        tree = ET.fromstring(channels_xml)
        channels = tree.findall('.//station')
        table = PrettyTable(['id', '名前'])
        table.align['id'] = 'l'
        table.align['名前'] = 'l'
        table.padding_width = 2
        for channel in channels:
            table.add_row([channel.attrib['id'], channel.find('name').text])
        print(table)

    def _get_stream_url(self):
        try:
            datetime_api_url = 'http://radiko.jp/v3/program/date/{}/{}.xml'.format(self.ft[:8], self.area_id)
            res = requests.get(url=datetime_api_url)
            channels_xml = res.content
            tree = ET.fromstring(channels_xml)
            station = tree.find('.//station[@id="{}"]'.format(self.station_id))
            prog = station.find('.//prog[@ft="{}"]'.format(self.ft))
            to = prog.attrib['to']

        # 日を跨いでいる場合は前の日の番組表を探す
        except AttributeError:
            datetime_api_url = 'http://radiko.jp/v3/program/date/{}/{}.xml'.format(int(self.ft[:8]) - 1, self.area_id)
            res = requests.get(url=datetime_api_url)
            channels_xml = res.content
            tree = ET.fromstring(channels_xml)
            station = tree.find('.//station[@id="{}"]'.format(self.station_id))
            prog = station.find('.//prog[@ft="{}"]'.format(self.ft))
            to = prog.attrib['to']

        self.title = prog.find('.//title').text.replace('　', '')
        table = PrettyTable(['title'])
        table.add_row([self.title])
        table.padding_width = 2
        print(table)
        self.stream_url = 'https://radiko.jp/v2/api/ts/playlist.m3u8?l=15&station_id={}&ft={}&to={}'.format(
            self.station_id,
            self.ft,
            to
        )

    def _create_aac(self):
        try:
            if not os.path.exists(self.output_path):
                subprocess.call('mkdir {}'.format(self.output_path), shell=True)
            cmd = ('ffmpeg '
                   '-loglevel fatal '
                   '-n -headers "X-Radiko-AuthToken: {}" '
                   '-i "{}" '
                   '-vn -acodec copy "{}/{}/{}.aac"'.format(
                    self.auth_response.authtoken,
                    self.stream_url,
                    self.output_path,
                    self.title,
                    '{}_{}'.format(self.title, self.ft[:8])
                    ))
            subprocess.call(cmd, shell=True)
            print('{}/{}/{}.aac'.format(self.output_path, self.title, '{}_{}'.format(self.title, self.ft[:8])))
            return True
        except:
            return False


@click.command(help='Radipy is CLI radiko Downloader written by python3.')
@click.option('-a', '--area', is_flag=True, help='print station id & name in your area')
@click.option('-id', type=str, help='set station id')
@click.option('-ft', type=str, help='set start time')
@click.option('--clear', is_flag=True, help='clear authkey and player in tmp dir')
def main(area, id, ft, clear):
    if clear:
        Radipy.clear()
    if area:
        radipy = Radipy(0, 0)
        radipy.get_channels()
    if id and ft:
        radipy = Radipy(station_id=id, ft=ft)
        radipy.create()

if __name__ == '__main__':
    main()
