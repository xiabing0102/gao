# coding=utf-8
# !/usr/bin/python

from urllib.parse import unquote
from urllib.parse import quote
from base.spider import Spider
from bs4 import BeautifulSoup
from base64 import b64decode
import urllib.request
import urllib.parse
import requests
import base64
import html
import json
import re
import sys

sys.path.append('..')

# ==================== 网址配置 ====================
xurl = "https://rb.huaduys.org"
REFERER = "https://rb.huaduys.org/"

headerz = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Accept-Encoding': 'gzip, deflate'
}

# 动态 cookie 头（在 Spider 实例化时同步更新）
headerx = {
    "Host": "rb.huaduys.org",
    "User-Agent": headerz["User-Agent"],
    "Accept": headerz["Accept"],
    "Referer": REFERER,
    "Accept-Language": headerz["Accept-Language"],
    "Accept-Encoding": "gzip, deflate"
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Pixel 3 XL) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/98.0.4758.101 Mobile Safari/537.36'
}
# =================================================


class Spider(Spider):
    global xurl
    global headerx
    global headers

    def getName(self):
        return "花都影院"

    def init(self, extend):
        # 首次访问获取 cookie，注入到全局 headerx
        try:
            s = requests.Session()
            s.headers.update(headerz)
            r = s.get(xurl, timeout=12)
            cookies = s.cookies.get_dict()
            if cookies:
                ck = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                headerx["Cookie"] = ck
        except Exception:
            pass

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.split("?")[0].split("#")[0].lower()
        return u.endswith(".m3u8") or u.endswith(".mp4") or u.endswith(".flv")

    def manualVideoCheck(self):
        pass

    def extract_middle_text(self, text, start_str, end_str, pl,
                            start_index1: str = '', end_index2: str = ''):
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

    # ---------------- 列表解析 ----------------
    def parse_videos_from_doc(self, doc, xurl):
        videos = []
        skip_names = ["广告点赞", "广告"]

        soups = doc.find_all('ul', class_="stui-vodlist clearfix")
        for soup in soups:
            for vod in soup.find_all('li'):
                remark_tag = vod.find('a', class_="stui-vodlist__thumb picture w-thumb img-shadow")
                if not remark_tag:
                    continue
                remark = remark_tag.text.strip()
                if remark in skip_names:
                    continue

                names = vod.find('h4', class_="title text-overflow")
                if not names:
                    continue
                name_a = names.find('a')
                if not name_a:
                    continue
                name = name_a.text.strip()
                vid = name_a.get('href', '')

                img = vod.find('img')
                pic = ""
                if img:
                    pic = img.get('data-original') or img.get('src') or ""
                if pic and 'http' not in pic:
                    pic = xurl + pic

                videos.append({
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": remark
                })
        return videos

    # ---------------- 首页 ----------------
    def homeContent(self, filter):
        result = {"class": []}
        detail = requests.get(url=xurl, headers=headerx, timeout=15)
        detail.encoding = "utf-8"
        doc = BeautifulSoup(detail.text, "lxml")

        soups = doc.find_all('ul', class_="stui-header__menu type-slide")
        skip_names = ["首页", "发布页", "免费VPN下载", "VPN下载"]
        for soup in soups:
            for vod in soup.find_all('li'):
                name = vod.text.strip()
                if name in skip_names:
                    continue
                a = vod.find('a')
                if not a:
                    continue
                id1 = a.get('href', '')
                if 'vodtype' not in id1:
                    continue
                fenge = id1.split(".html")
                id = f"{fenge[0]}-----------.html"
                id = id.replace('vodtype', 'vodshow')
                result["class"].append({"type_id": id, "type_name": name})
        return result

    def homeVideoContent(self):
        detail = requests.get(url=xurl, headers=headerx, timeout=15)
        detail.encoding = "utf-8"
        doc = BeautifulSoup(detail.text, "lxml")
        videos = self.parse_videos_from_doc(doc, xurl)
        return {'list': videos}

    # ---------------- 分类 ----------------
    def categoryContent(self, cid, pg, filter, ext):
        if pg:
            page = int(pg)
        else:
            page = 1
        fenge = cid.split("---.html")
        url = f'{xurl}{fenge[0]}{str(page)}---.html'
        detail = requests.get(url=url, headers=headerx, timeout=15)
        detail.encoding = "utf-8"
        doc = BeautifulSoup(detail.text, "lxml")
        videos = self.parse_videos_from_doc(doc, xurl)
        return {
            'list': videos,
            'page': pg,
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }

    # ---------------- 详情 ----------------
    def detailContent(self, ids):
        did = ids[0]
        if 'http' not in did:
            did = xurl + did

        res = requests.get(url=did, headers=headerx, timeout=15)
        res.encoding = "utf-8"
        res_text = html.unescape(res.text)
        doc = BeautifulSoup(res_text, "lxml")

        title_el = doc.find('h1', class_='title') or doc.find('title')
        name = title_el.text.strip() if title_el else ""
        name = re.sub(r'《|》|详情介绍.*', '', name).strip()

        pic_el = doc.find('img', class_='lazyload')
        vod_pic = pic_el.get('data-original') if pic_el and pic_el.get('data-original') else ""

        desc_el = doc.find('meta', attrs={'name': 'description'})
        content = desc_el.get('content', '').strip() if desc_el else ""

        director, actor, remarks, year, area = "", "", "", "", ""
        detail_p = doc.find('p', class_='stui-player__detail detail')
        if detail_p:
            for a in detail_p.find_all('a'):
                href = a.get('href', '')
                t = a.text.strip()
                if 'vodshow' in href and not remarks:
                    remarks = t
                elif 'vodsearch' in href and not area:
                    area = t
                elif 'voddetail' in href and not director:
                    director = t

        episodes = []
        playlist = doc.find('ul', class_='stui-content__playlist')
        if not playlist:
            playlist = doc.find('ul', class_='stui-content__playlist clearfix')
        if playlist:
            for a in playlist.find_all('a'):
                href = a.get('href', '')
                ep_name = a.text.strip()
                if href and ep_name:
                    if 'http' not in href:
                        href = xurl + href
                    episodes.append(f"{ep_name}${href}")

        if not episodes:
            btn = doc.find('a', class_='btn btn-primary')
            if btn and btn.get('href'):
                href = btn['href']
                if 'http' not in href:
                    href = xurl + href
                episodes.append(f"正片${href}")

        vod = {
            "vod_id": did,
            "vod_director": director,
            "vod_actor": actor,
            "vod_remarks": remarks,
            "vod_year": year,
            "vod_area": area,
            "vod_content": content,
            "vod_play_from": "花都专线",
            "vod_play_url": "#".join(episodes) if episodes else ""
        }
        return {'list': [vod]}

    # ---------------- 播放 ----------------
    def _parse_player_data(self, html_text):
        m = re.search(r'(?:var\s+)?player_(?:data|aaaa)\s*=\s*', html_text)
        if not m:
            return None
        start = html_text.find('{', m.end())
        if start < 0:
            return None
        depth = 0
        in_str = False
        quote_char = ""
        esc = False
        for i in range(start, len(html_text)):
            c = html_text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == quote_char:
                    in_str = False
                continue
            if c in ('"', "'"):
                in_str = True
                quote_char = c
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(html_text[start:i + 1])
                    except Exception:
                        return None
        return None

    def _decode_player_url(self, url, encrypt):
        if not url:
            return ""
        try:
            if encrypt == 1:
                return unquote(url)
            if encrypt == 2:
                b = base64.b64decode(url)
                return unquote(b.decode('utf-8', 'ignore'))
        except Exception:
            pass
        return url

    def playerContent(self, flag, id, vipFlags):
        try:
            detail = requests.get(url=id, headers=headerx, timeout=12)
            detail.encoding = "utf-8"
            res = detail.text

            data = self._parse_player_data(res)
            url = ""
            if data and data.get("url"):
                url = self._decode_player_url(data["url"], data.get("encrypt", 0))

            if not url or not self.isVideoFormat(url):
                m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', res)
                if m:
                    src = m.group(1)
                    m2 = re.search(r'[?&]url=([^&"\']+)', src)
                    if m2:
                        cand = unquote(m2.group(1))
                        if self.isVideoFormat(cand):
                            url = cand

            if not url or not self.isVideoFormat(url):
                m = re.search(r'["\'](https?://[^"\']+?\.(?:m3u8|mp4)[^"\']*)["\']', res, re.I)
                if m:
                    url = m.group(1).replace("\\/", "/").replace("\\", "")

            result = {}
            if url and self.isVideoFormat(url):
                result["parse"] = 0
                result["playUrl"] = ''
                result["url"] = url
                result["header"] = {
                    "User-Agent": headers["User-Agent"],
                    "Referer": id,
                    "Origin": xurl
                }
            else:
                result["parse"] = 1
                result["playUrl"] = ''
                result["url"] = url if url else id
                result["header"] = headers
            return result

        except Exception:
            return {"parse": 1, "playUrl": "", "url": id, "header": headers}

    # ---------------- 搜索 ----------------
    def searchContentPage(self, key, quick, pg):
        if pg:
            page = int(pg)
        else:
            page = 1
        url = f'{xurl}/vodsearch/-------------.html?wd={quote(key)}'
        if page > 1:
            url = f'{xurl}/vodsearch/-------------.html?wd={quote(key)}&page={page}'
        detail = requests.get(url=url, headers=headerx, timeout=15)
        detail.encoding = "utf-8"
        doc = BeautifulSoup(detail.text, "lxml")
        videos = self.parse_videos_from_doc(doc, xurl)
        return {
            'list': videos,
            'page': page,
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def localProxy(self, params):
        if params.get('type') == "m3u8":
            return self.proxyM3u8(params)
        elif params.get('type') == "media":
            return self.proxyMedia(params)
        elif params.get('type') == "ts":
            return self.proxyTs(params)
        return None