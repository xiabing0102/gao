# coding=utf-8
# !/usr/bin/python

"""

作者 丢丢喵 🚓 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容
                    ====================Diudiumiao====================

"""

from Crypto.Util.Padding import unpad
from Crypto.Util.Padding import pad
from urllib.parse import unquote
from Crypto.Cipher import ARC4
from urllib.parse import quote
from base.spider import Spider
from Crypto.Cipher import AES
from datetime import datetime
from bs4 import BeautifulSoup
from base64 import b64decode
import urllib.request
import urllib.parse
import datetime
import binascii
import requests
import base64
import json
import time
import sys
import re
import os

sys.path.append('..')

xurl = "https://www.fun.tv"

xurl1 = "https://fs-im-kefu.7moor-fs1.com"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
          }

headerx = {
    'Host': 'www.fun.tv',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0'
          }

class Spider(Spider):

    def getName(self):
        return "首页"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def extract_middle_text(self, text, start_str, end_str, pl, start_index1: str = '', end_index2: str = ''):
        if pl == 3:
            plx = []
            while True:
                start_index = text.find(start_str)
                if start_index == -1:
                    break
                end_index = text.find(end_str, start_index + len(start_str))
                if end_index == -1:
                    break
                middle_text = text[start_index + len(start_str):end_index]
                plx.append(middle_text)
                text = text.replace(start_str + middle_text + end_str, '')
            if len(plx) > 0:
                purl = ''
                for i in range(len(plx)):
                    matches = re.findall(start_index1, plx[i])
                    output = ""
                    for match in matches:
                        match3 = re.search(r'(?:^|[^0-9])(\d+)(?:[^0-9]|$)', match[1])
                        if match3:
                            number = match3.group(1)
                        else:
                            number = 0
                        if 'http' not in match[0]:
                            output += f"#{match[1]}${number}{xurl}{match[0]}"
                        else:
                            output += f"#{match[1]}${number}{match[0]}"
                    output = output[1:]
                    purl = purl + output + "$$$"
                purl = purl[:-3]
                return purl
            else:
                return ""
        else:
            start_index = text.find(start_str)
            if start_index == -1:
                return ""
            end_index = text.find(end_str, start_index + len(start_str))
            if end_index == -1:
                return ""

        if pl == 0:
            middle_text = text[start_index + len(start_str):end_index]
            return middle_text.replace("\\", "")

        if pl == 1:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                jg = ' '.join(matches)
                return jg

        if pl == 2:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                new_list = [f'{item}' for item in matches]
                jg = '$$$'.join(new_list)
                return jg

    def homeContent(self, filter):
        result = {"class": []}
        category_data = self._fetch_home_categories()
        categories = self._parse_home_categories(category_data)
        result["class"] = categories
        return result

    def _fetch_home_categories(self):
        detail = requests.get(url=f"{xurl}/retrieve/c-e794b5e8a786e589a7/", headers=headerx)
        detail.encoding = "utf-8"
        return detail.text

    def _parse_home_categories(self, html_content):
        categories = []
        doc = BeautifulSoup(html_content, "lxml")
        soup = doc.find('div', class_="ls-nav-bar fix")
        if soup:
            vods = soup.find_all('li')
            for vod in vods:
                category = self._extract_category_info(vod)
                categories.append(category)
        return categories

    def _extract_category_info(self, vod_element):
        category_info = {
            "type_id": vod_element.find('a')['href'] if vod_element.find('a') else "",
            "type_name": vod_element.text.strip()
                        }
        return category_info

    def homeVideoContent(self):
        pass

    def categoryContent(self, cid, pg, filter, ext):
        result = {}
        videos = []
        page = self._get_page_number(pg)
        url = self._build_category_url(cid, page)
        res = self._fetch_category_data(url)
        videos = self._parse_category_videos(res)
        result = {
            'list': videos,
            'page': pg,
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
                 }
        return result

    def _get_page_number(self, pg):
        if pg:
            return int(pg)
        else:
            return 1

    def _build_category_url(self, cid, page):
        fenge = cid.split("/")
        return f'{xurl}/{fenge[1]}/{fenge[2]}.pg-{str(page)}'

    def _fetch_category_data(self, url):
        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        return detail.text

    def _parse_category_videos(self, res):
        videos = []
        doc = BeautifulSoup(res, "lxml")
        soups = doc.find_all('div', class_="mod-wrap-in")
        for soup in soups:
            vods = soup.find_all('div', class_="mod-vd-i")
            for vod in vods:
                video = self._extract_video_info(vod)
                videos.append(video)
        return videos

    def _extract_video_info(self, vod):
        video = {
            "vod_id": vod.find('h3', class_="tit").find('a')['href'],
            "vod_name": vod.find('h3', class_="tit").find('a')['title'],
            "vod_pic": self._process_image_url(vod.find('img')['_lazysrc']),
            "vod_remarks": self._get_video_remarks(vod)
                }
        return video

    def _process_image_url(self, img_src):
        return img_src.replace('w=200', 'w=400').replace('h=112', 'h=400')

    def _get_video_remarks(self, vod):
        tip_element = vod.find('i', class_="tip")
        if tip_element is not None:
            return tip_element.text.strip()
        else:
            return " "

    def detailContent(self, ids):
        did = self.process_id(ids[0])
        res = self.fetch_detail_data(did)
        video_info = self.parse_detail_content(res, did)
        result = {}
        result['list'] = [video_info]
        return result

    def process_id(self, did):
        if 'http' not in did:
            did = xurl + did
        return did

    def fetch_detail_data(self, did):
        detail = requests.get(url=did, headers=headerx)
        detail.encoding = "utf-8"
        return detail.text

    def parse_detail_content(self, html_content, did):
        doc = BeautifulSoup(html_content, "lxml")
        content = self.extract_content(html_content)
        director = self.extract_director(html_content)
        actor = self.extract_actor(html_content)
        remarks = self.extract_remarks(html_content)
        play_info = self.extract_play_info(doc)
        video_info = {
            "vod_id": did,
            "vod_director": director,
            "vod_actor": actor,
            "vod_remarks": remarks,
            "vod_content": content,
            "vod_play_from": play_info['xianlu'],
            "vod_play_url": play_info['bofang']
                     }
        return video_info

    def extract_content(self, html_content):
        return '😸丢丢为您介绍剧情📢' + self.extract_middle_text(html_content, 'style="display:none;">', '<', 0)

    def extract_director(self, html_content):
        return self.extract_middle_text(html_content, 'dirsort ">导演：', '</p>', 1, 'target=".*?">(.*?)</a>')

    def extract_actor(self, html_content):
        actor = self.extract_middle_text(html_content, 'dirsort ">主演：', '</p>', 1, 'target=".*?">(.*?)</a>')
        return actor.replace('<a>', '') if actor else ''

    def extract_remarks(self, html_content):
        return self.extract_middle_text(html_content, 'dirsort ">类型：', '</p>', 1, 'target=".*?">(.*?)</a>')

    def extract_play_info(self, doc):
        soups = doc.find_all('ul', class_="torrent fix")
        if not soups:
            return self.extract_single_play_info(doc)
        else:
            return self.extract_multiple_play_info(soups)

    def extract_single_play_info(self, doc):
        bofang = doc.find('div', class_="vd-list block").find('a')['href']
        if 'http' not in bofang:
            bofang = xurl + bofang
        return {
            'xianlu': '风行视频',
            'bofang': bofang
               }

    def extract_multiple_play_info(self, soups):
        bofang = ''
        for item in soups:
            vods = item.find_all('a')
            for sou in vods:
                id = xurl + sou['href'] if 'http' not in sou['href'] else sou['href']
                bofang = bofang + sou.text.strip() + '$' + id + '#'
        if bofang:
            bofang = bofang[:-1]
        return {
            'xianlu': '风行视频',
            'bofang': bofang
               }

    def encode_path(self, path):
        char_mapping = {'n': '.'}
        encoded_path = ""
        for char in path:
            encoded_path += char_mapping.get(char, char)
        return encoded_path

    def playerContent(self, flag, id, vipFlags):
        url = self.get_play_url(id)
        return self.format_result(url)

    def get_original_path(self):
        return "/ly/4d2c3f00-7d4c-11e5-af15-41bf63ae4ea0/43890aa7bfc8fb64/didiuntxt"

    def get_encoded_path(self):
        original_path = self.get_original_path()
        return self.encode_path(original_path)

    def get_code_token(self):
        encoded_path = self.get_encoded_path()
        response = requests.get(f'{xurl1}{encoded_path}')
        response.encoding = 'utf-8'
        return response.text

    def fetch_video_data(self, id):
        code = self.get_code_token()
        detail = requests.get(url=f'{code}{id}', headers=headers)
        detail.encoding = "utf-8"
        return detail.json()

    def get_play_url(self, id):
        data = self.fetch_video_data(id)
        return data['data']['url']

    def format_result(self, url):
        result = {}
        result["parse"] = 0
        result["playUrl"] = ''
        result["url"] = url
        result["header"] = headers
        return result

    def searchContentPage(self, key, quick, pg):
        url = self.build_search_url(key)
        res = self.fetch_search_data(url)
        videos = self.parse_search_results(res)
        result = self.format_search_result(videos, pg)
        return result

    def build_search_url(self, key):
        return f'{xurl}/search/?word={key}'

    def fetch_search_data(self, url):
        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        return detail.text

    def parse_search_results(self, html_content):
        videos = []
        doc = BeautifulSoup(html_content, "lxml")
        soups = doc.find_all('div', class_="face")
        for vod in soups:
            video = self.extract_video_info(vod)
            videos.append(video)
        return videos

    def extract_video_info(self, vod_element):
        video = {
            "vod_id": vod_element.find('a')['href'],
            "vod_name": vod_element.find('img')['title'],
            "vod_pic": vod_element.find('img')['_lazysrc'],
            "vod_remarks": self.extract_video_remarks(vod_element)
                }
        return video

    def extract_video_remarks(self, vod_element):
        remarks_element = vod_element.find('div', class_="updateinfo")
        if remarks_element is not None:
            return remarks_element.text.strip()
        else:
            return " "

    def format_search_result(self, videos, pg):
        result = {}
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, '1')

    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        elif params['type'] == "media":
            return self.proxyMedia(params)
        elif params['type'] == "ts":
            return self.proxyTs(params)
        return None





