# coding=utf-8
# !/usr/bin/python

"""

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
import hashlib
import base64
import json
import time
import sys
import re
import os

sys.path.append('..')

xurl = "https://api-store.qmplaylet.com"
xurl1 = "https://api-read.qmplaylet.com"
keys = "d3dGiJc651gSQ8w1"

data = {
    "static_score": "0.8",
    "uuid": "00000000-7fc7-08dc-0000-000000000000",
    "device-id": "20250220125449b9b8cac84c2dd3d035c9052a2572f7dd0122edde3cc42a70",
    "mac": "",
    "sourceuid": "aa7de295aad621a6",
    "refresh-type": "0",
    "model": "22021211RC",
    "wlb-imei": "",
    "client-id": "aa7de295aad621a6",
    "brand": "Redmi",
    "oaid": "",
    "oaid-no-cache": "",
    "sys-ver": "12",
    "trusted-id": "",
    "phone-level": "H",
    "imei": "",
    "wlb-uid": "aa7de295aad621a6",
    "session-id": str(int(time.time() * 1000)),
}

json_str = json.dumps(data, separators=(',', ':'))
encoded = base64.b64encode(json_str.encode()).decode()

char_map = {
    '+': 'P', '/': 'X', '0': 'M', '1': 'U', '2': 'l', '3': 'E', '4': 'r',
    '5': 'Y', '6': 'W', '7': 'b', '8': 'd', '9': 'J', 'A': '9', 'B': 's',
    'C': 'a', 'D': 'I', 'E': '0', 'F': 'o', 'G': 'y', 'H': '_', 'I': 'H',
    'J': 'G', 'K': 'i', 'L': 't', 'M': 'g', 'N': 'N', 'O': 'A', 'P': '8',
    'Q': 'F', 'R': 'k', 'S': '3', 'T': 'h', 'U': 'f', 'V': 'R', 'W': 'q',
    'X': 'C', 'Y': '4', 'Z': 'p', 'a': 'm', 'b': 'B', 'c': 'O', 'd': 'u',
    'e': 'c', 'f': '6', 'g': 'K', 'h': 'x', 'i': '5', 'j': 'T', 'k': '-',
    'l': '2', 'm': 'z', 'n': 'S', 'o': 'Z', 'p': '1', 'q': 'V', 'r': 'v',
    's': 'j', 't': 'Q', 'u': '7', 'v': 'D', 'w': 'w', 'x': 'n', 'y': 'L',
    'z': 'e'
}

qm_params = ''
for c in encoded:
    qm_params += char_map.get(c, c)

params_str = (
    "AUTHORIZATION=" +
    "app-version=10001" +
    "application-id=com.duoduo.read" +
    "channel=unknown" +
    "is-white=" +
    "net-env=5" +
    "platform=android" +
    f"qm-params={qm_params}" +
    f"reg={keys}"
)

signs = hashlib.md5(params_str.encode()).hexdigest()

headerx = {
    'net-env': '5',
    'reg': '',
    'channel': 'unknown',
    'is-white': '',
    'platform': 'android',
    'application-id': 'com.duoduo.read',
    'authorization': '',
    'app-version': '10001',
    'user-agent': 'webviewversion/0',
    'qm-params': qm_params,
    'sign': signs
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
}

class Spider(Spider):
    def __init__(self):
        self.xurl = xurl
        self.xurl1 = xurl1
        self.keys = keys
        self.headerx = headerx
        self.headers = headers

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
                            output += f"#{match[1]}${number}{self.xurl}{match[0]}"
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
        result = {"class": [], "filters": {}}

        sign_string = f"operation=1playlet_privacy=1tag_id=0{self.keys}"
        sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()

        url = f"{self.xurl}/api/v1/playlet/index?tag_id=0&playlet_privacy=1&operation=1&sign={sign}"
        try:
            detail = requests.get(url=url, headers=self.headerx, timeout=10)
            detail.encoding = "utf-8"
            data = detail.json()
        except Exception as e:
            print(f"请求失败: {e}")
            return result

        if 'data' not in data or 'tag_categories' not in data['data']:
            return result

        cats = data['data']['tag_categories']

        # ---- 各题材专属筛选子集（按标签名匹配，id 动态从 API 取） ----
        # 题材名 -> (细分题材白名单, 人物设定白名单, 情感白名单)；None=全部
        self._cat_filter_names = {
            '新剧': (None, None, None),
            '都市情感': (['逆袭','复仇','打脸虐渣','家庭','重生','女性成长','穿越','追妻火葬场','闪婚','权谋','马甲','强者回归','职场','系统','异能','商战','致富','高手下山','偷听心声','娱乐明星','脑洞','社会话题','穿书','替身','种田经商','伦理'], ['豪门总裁','真假千金','赘婿','神医','小人物','欢喜冤家','神豪','团宠','银发'], None),
            '都市': (['逆袭','复仇','打脸虐渣','家庭','重生','女性成长','穿越','追妻火葬场','闪婚','权谋','马甲','强者回归','职场','系统','异能','商战','致富','高手下山','偷听心声','娱乐明星','脑洞','社会话题','穿书','替身','种田经商','伦理'], ['豪门总裁','真假千金','赘婿','神医','小人物','欢喜冤家','神豪','团宠','银发'], None),
            '古装': (['宫斗','宅斗','穿书','替身','权谋','马甲','重生','穿越','团宠','真假千金','银发','女帝','追妻火葬场','脑洞','复仇','逆袭','神医','欢喜冤家'], ['女帝','真假千金','团宠','银发','神医','小人物','欢喜冤家','赘婿','战神','兵王','豪门总裁'], None),
            '玄幻仙侠': (['强者回归','高手下山','系统','重生','穿越','马甲','异能','权谋','逆袭','复仇','打脸虐渣','脑洞','穿书','替身'], ['战神','兵王','女帝','神医','小人物','神豪','团宠','银发'], None),
            '年代': (['重生','穿越','马甲','家庭','致富','种田经商','逆袭','打脸虐渣','追妻火葬场','替身','社会话题'], ['小人物','欢喜冤家','赘婿','神医','真假千金','团宠'], None),
            '奇幻': (['穿越','重生','系统','异能','马甲','强者回归','脑洞','穿书','替身','逆袭','复仇'], ['战神','兵王','女帝','神豪','团宠','银发','神医'], None),
            '乡村': (['家庭','致富','种田经商','逆袭','打脸虐渣','重生','社会话题'], ['小人物','欢喜冤家','赘婿','神医'], None),
            '民国': (['重生','穿越','马甲','替身','权谋','宫斗','宅斗','追妻火葬场','复仇','脑洞','社会话题'], ['真假千金','小人物','欢喜冤家','团宠','神医','赘婿'], None),
            '青春校园': (['甜宠','家庭','重生','穿书','替身','脑洞','追妻火葬场','社会话题'], ['小人物','欢喜冤家','团宠','真假千金'], None),
            '末世': (['系统','异能','强者回归','重生','穿越','脑洞','逆袭','复仇'], ['战神','兵王','神医','小人物','神豪'], None),
            '科幻': (['系统','异能','脑洞','强者回归','穿越','重生','马甲','权谋'], ['战神','兵王','神医','小人物','神豪'], None),
            '武侠': (['强者回归','高手下山','权谋','复仇','逆袭','打脸虐渣','宫斗','宅斗','脑洞'], ['战神','兵王','女帝','神医','小人物','欢喜冤家','赘婿'], None),
            '二次元': (['脑洞','搞笑','穿书','替身','重生','穿越','系统','异能','马甲'], ['团宠','小人物','欢喜冤家','银发','神医'], None),
        }

        def _pick_tags(tags, whitelist):
            """从 API tags 里按名称白名单挑出 {v, n}，白名单 None=全部"""
            if not tags:
                return []
            out = [{"v": "", "n": "全部"}]
            for t in tags:
                nm = t.get('tag_name', '')
                tid = t.get('tag_id', '')
                if not nm or str(tid) == '':
                    continue
                if whitelist is None or nm in whitelist:
                    out.append({"v": str(tid), "n": nm})
            return out if len(out) > 1 else []

        # ---- 分类：层0(新剧) + 层1(题材大类) ----
        class_list = []
        for duo in ('0', '1'):
            if int(duo) >= len(cats):
                continue
            js = cats[int(duo)].get('tags', [])
            for vod in js:
                name = vod.get('tag_name', '')
                if "推荐" in name:
                    continue
                tid = vod.get('tag_id', '')
                if name and tid:
                    class_list.append({"type_id": str(tid), "type_name": name})

        # ---- 为每个分类生成专属筛选面板 ----
        for c in class_list:
            cid, cname = str(c['type_id']), c['type_name']
            wl = self._cat_filter_names.get(cname, (None, None, None))
            groups = []
            for li, key, gname, whitelist in (
                (2, 'tag2', '细分题材', wl[0]),
                (3, 'tag3', '人物设定', wl[1]),
                (4, 'tag4', '情感', wl[2]),
            ):
                if li >= len(cats):
                    continue
                vals = _pick_tags(cats[li].get('tags', []), whitelist)
                if vals:
                    groups.append({"key": key, "name": gname, "value": vals})
            if groups:
                result["filters"][cid] = groups

        result["class"] = class_list
        return result

    def homeVideoContent(self):
        videos = []

        sign_string = f"operation=1playlet_privacy=1tag_id=0{self.keys}"
        sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()

        url = f"{self.xurl}/api/v1/playlet/index?tag_id=0&playlet_privacy=1&operation=1&sign={sign}"
        try:
            detail = requests.get(url=url, headers=self.headerx, timeout=10)
            detail.encoding = "utf-8"
            data = detail.json()
        except Exception as e:
            print(f"请求失败: {e}")
            return {'list': videos}

        if 'data' not in data or 'list' not in data['data']:
            return {'list': videos}

        data_list = data['data']['list']
        for vod in data_list:
            name = vod.get('title', '')
            id = vod.get('playlet_id', '')
            pic = vod.get('image_link', '')
            remark = vod.get('hot_value', '')

            if name and id:
                video = {
                    "vod_id": id,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": remark
                }
                videos.append(video)

        return {'list': videos}

    def categoryContent(self, cid, pg, filter, ext):
        result = {}
        videos = []

        page = int(pg) if pg else 1

        # ---- 解析筛选（兼容 dict / JSON 字符串），单选替换：细分>设定>情感 ----
        f = {}
        for d in (filter, ext):
            if isinstance(d, dict):
                for k, v in d.items():
                    if v is not None and str(v) not in ('', '0', 'None'):
                        f[str(k)] = str(v)
            elif isinstance(d, str) and d.strip().startswith('{'):
                try:
                    dd = json.loads(d)
                    for k, v in dd.items():
                        if v is not None and str(v) not in ('', '0', 'None'):
                            f[str(k)] = str(v)
                except Exception:
                    pass

        # 七猫 API 只支持单个 tag_id，不支持多标签组合：
        # 筛选选中哪个标签，就用哪个标签请求（单选替换），未选则用分类本身
        tag = str(cid)
        for k in ('tag2', 'tag3', 'tag4'):
            v = f.get(k, '')
            if v:
                tag = str(v)
                break

        if page == 1:
            sign_string = f"operation=1playlet_privacy=1tag_id={tag}{self.keys}"
            sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
            url = f'{self.xurl}/api/v1/playlet/index?tag_id={tag}&playlet_privacy=1&operation=1&sign={sign}'
        else:
            sign_string = f"next_id={str(page)}operation=1playlet_privacy=1tag_id={tag}{self.keys}"
            sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
            url = f'{self.xurl}/api/v1/playlet/index?tag_id={tag}&next_id={str(page)}&playlet_privacy=1&operation=1&sign={sign}'

        try:
            detail = requests.get(url=url, headers=self.headerx, timeout=10)
            detail.encoding = "utf-8"
            data = detail.json()
        except Exception as e:
            print(f"请求失败: {e}")
            return {'list': videos, 'page': pg, 'pagecount': 1, 'limit': 90, 'total': 0}

        if 'data' not in data or 'list' not in data['data']:
            return {'list': videos, 'page': pg, 'pagecount': 1, 'limit': 90, 'total': 0}

        data_list = data['data']['list']
        for vod in data_list:
            name = vod.get('title', '')
            id = vod.get('playlet_id', '')
            pic = vod.get('image_link', '')
            remark = vod.get('hot_value', '')

            if name and id:
                video = {
                    "vod_id": id,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": remark
                }
                videos.append(video)

        result = {
            'list': videos,
            'page': pg,
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }
        return result

    def detailContent(self, ids):
        did = ids[0]
        result = {}
        videos = []
        xianlu = ''
        bofang = ''

        sign_string = f"playlet_id={did}{self.keys}"
        sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()

        urls = f'{self.xurl1}/player/api/v1/playlet/info?playlet_id={did}&sign={sign}'
        try:
            detail = requests.get(url=urls, headers=self.headerx, timeout=10)
            detail.encoding = "utf-8"
            detail_data = detail.json()
        except Exception as e:
            print(f"请求失败: {e}")
            return {'list': videos}

        if 'data' not in detail_data:
            return {'list': videos}

        data = detail_data['data']
        blurb = data.get('intro', '未知')
        content = blurb

        jisu = data.get('total_episode_num', '未知')
        jisu = f'{jisu}全集'

        leixing = data.get('tags', '未知')
        remarks = f"{leixing} {jisu}"

        # 获取播放列表
        play_list = data.get('play_list', [])
        for sou in play_list:
            video_url = sou.get('video_url', '')
            sort_name = sou.get('sort', '')
            if video_url and sort_name:
                bofang += f"{sort_name}${video_url}#"

        if bofang:
            bofang = bofang[:-1]  # 去掉最后一个#
            xianlu = '七猫专线'

        videos.append({
            "vod_id": did,
            "vod_remarks": remarks,
            "vod_content": content,
            "vod_play_from": xianlu,
            "vod_play_url": bofang
        })

        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {
            "parse": 0,
            "playUrl": '',
            "url": id,
            "header": self.headers
        }
        return result

    def searchContentPage(self, key, quick, pg):
        result = {}
        videos = []

        page = int(pg) if pg else 1

        sign_string = f"extend=page={str(page)}read_preference=0track_id=ec1280db127955061754851657967wd={key}{self.keys}"
        sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()

        url = f'{self.xurl}/api/v1/playlet/search?extend=&page={str(page)}&wd={key}&read_preference=0&track_id=ec1280db127955061754851657967&sign={sign}'
        try:
            detail = requests.get(url=url, headers=self.headerx, timeout=10)
            detail.encoding = "utf-8"
            data = detail.json()
        except Exception as e:
            print(f"搜索失败: {e}")
            return {'list': videos, 'page': pg, 'pagecount': 1, 'limit': 90, 'total': 0}

        if 'data' not in data or 'list' not in data['data']:
            return {'list': videos, 'page': pg, 'pagecount': 1, 'limit': 90, 'total': 0}

        data_list = data['data']['list']
        for vod in data_list:
            name = vod.get('title', '')
            # 清理HTML标签和多余空格
            name = re.sub(r'<[^>]+>', '', name)
            name = ' '.join(name.split())

            id = vod.get('id', '')
            pic = vod.get('image_link', '')
            remark = vod.get('total_num', '')

            if name and id:
                video = {
                    "vod_id": id,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": remark
                }
                videos.append(video)

        result = {
            'list': videos,
            'page': pg,
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        elif params['type'] == "media":
            return self.proxyMedia(params)
        elif params['type'] == "ts":
            return self.proxyTs(params)
        return None