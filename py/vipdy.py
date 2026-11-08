#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import re
from urllib.parse import urljoin, urlparse, quote
import requests
from lxml import etree
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "vipdy"

    def init(self, extend=""):
        self.host = "https://www.vipdy.vip"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": self.host + "/"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.categories = [
            {"type_id": "dianying", "type_name": "电影"},
            {"type_id": "juji", "type_name": "剧集"},
            {"type_id": "zongyi", "type_name": "综艺"},
            {"type_id": "dongman", "type_name": "动漫"},
            {"type_id": "tiyu", "type_name": "体育"},
            {"type_id": "dongzuopian", "type_name": "动作片"},
            {"type_id": "xijupian", "type_name": "喜剧片"},
            {"type_id": "aiqingpian", "type_name": "爱情片"},
            {"type_id": "kehuanpian", "type_name": "科幻片"},
            {"type_id": "juqingpian", "type_name": "剧情片"},
            {"type_id": "kongbupian", "type_name": "恐怖片"},
            {"type_id": "qihuanpian", "type_name": "奇幻片"},
            {"type_id": "zhanzhengpian", "type_name": "战争片"},
            {"type_id": "jilupian", "type_name": "记录片"},
            {"type_id": "fulipian", "type_name": "福利片"},
            {"type_id": "donghuapian", "type_name": "动画片"},
            {"type_id": "guochanju", "type_name": "国产剧"},
            {"type_id": "gangtaiju", "type_name": "港台剧"},
            {"type_id": "rihanju", "type_name": "日韩剧"},
            {"type_id": "oumeiju", "type_name": "欧美剧"},
            {"type_id": "haiwaiju", "type_name": "海外剧"},
            {"type_id": "duanju", "type_name": "短剧"},
            {"type_id": "daluzongyi", "type_name": "大陆综艺"},
            {"type_id": "gangtaizongyi", "type_name": "港台综艺"},
            {"type_id": "rihanzongyi", "type_name": "日韩综艺"},
            {"type_id": "oumeizongyi", "type_name": "欧美综艺"},
            {"type_id": "guochandongman", "type_name": "国产动漫"},
            {"type_id": "gangtaidongman", "type_name": "港台动漫"},
            {"type_id": "rihandongman", "type_name": "日韩动漫"},
            {"type_id": "oumeidongman", "type_name": "欧美动漫"},
        ]

    def _get(self, url):
        try:
            r = self.session.get(url, headers=self.headers, timeout=15, verify=False, proxies=getattr(self.session, 'proxies', None) or None)
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except Exception:
            return ""

    def _fix(self, url):
        return urljoin(self.host + "/", url or "")

    def _text(self, node):
        return " ".join("".join(node.xpath(".//text()")).split()) if node is not None else ""

    def _is_media(self, url):
        return bool(re.search(r"\.(?:m3u8|mp4)(?:$|[?#])", urlparse(url).path, re.I))

    def _probe_media(self, url):
        if not url or not self._is_media(url):
            return False
        try:
            r = self.session.get(url, headers=self.headers, timeout=10, verify=False, stream=True, proxies=getattr(self.session, 'proxies', None) or None)
            chunk = next(r.iter_content(4096), b"")
            return b"#EXTM3U" in chunk or chunk[:4] in (b"\x00\x00\x00\x1c", b"ftyp")
        except Exception:
            return False

    def _list(self, html):
        tree = etree.HTML(html or "")
        out, seen = [], set()
        items = tree.xpath('//ul[contains(@class,"stui-vodlist")]/li')
        for li in items:
            try:
                a = li.xpath('.//a')[0] if li.xpath('.//a') else None
                if a is None:
                    continue
                href = a.get("href", "")
                m = re.search(r"/v/(\d+)\.html", href)
                if not m or m.group(1) in seen:
                    continue
                seen.add(m.group(1))
                pic = a.get("data-original") or a.get("data-src") or ""
                name = a.get("title") or self._text(a)
                remarks = li.xpath('.//span[contains(@class,"pic-text")]/b/text()')
                remark = " ".join(remarks) if remarks else ""
                out.append({"vod_id": m.group(1), "vod_name": name, "vod_pic": self._fix(pic), "vod_remarks": remark})
            except Exception:
                continue
        return out

    def _pagecount(self, html, tid, pg):
        nums = [int(x) for x in re.findall(r"/t/" + re.escape(tid) + r"-(\d+)\.html", html)]
        if not nums:
            nxt = re.search("下一页", html)
            return pg + 1 if nxt else pg
        return max(nums)

    def homeContent(self, filter):
        html = self._get(self.host)
        return {"class": self.categories, "list": self._list(html), "filters": {}}

    def homeVideoContent(self):
        return {"list": self._list(self._get(self.host))}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if str(pg).isdigit() else 1
        url = f"{self.host}/t/{tid}-{pg}.html" if pg > 1 else f"{self.host}/t/{tid}.html"
        html = self._get(url)
        items = self._list(html)
        limit = len(items) or 12
        pagecount = self._pagecount(html, tid, pg)
        return {"page": pg, "pagecount": pagecount, "limit": limit, "total": pagecount * limit, "list": items}

    def detailContent(self, ids):
        out = []
        for vid in ids:
            try:
                html = self._get(f"{self.host}/v/{vid}.html")
                tree = etree.HTML(html)
                name_el = tree.xpath('//h1[contains(@class,"title")]')
                name = self._text(name_el[0]) if name_el else str(vid)
                pic = self._fix((tree.xpath('//a[contains(@class,"stui-vodlist__thumb")]/@data-original') or [""])[0])
                detail_ps = tree.xpath('//div[contains(@class,"stui-content__detail")]//p')
                year = area = director = actor = content = state = ""
                for p in detail_ps:
                    text = self._text(p)
                    if text.startswith("年份"):
                        year = text.split("：", 1)[-1].strip() if "：" in text else text.split(":", 1)[-1].strip()
                    elif text.startswith("地区") and not area:
                        area = text.split("：", 1)[-1].strip() if "：" in text else text.split(":", 1)[-1].strip()
                    elif text.startswith("导演"):
                        director = text.split("：", 1)[-1].strip() if "：" in text else text.split(":", 1)[-1].strip()
                    elif text.startswith("主演"):
                        actor = text.split("：", 1)[-1].strip() if "：" in text else text.split(":", 1)[-1].strip()
                    elif text.startswith("状态"):
                        state = text.split("：", 1)[-1].strip() if "：" in text else text.split(":", 1)[-1].strip()
                    elif text.startswith("介绍"):
                        content = text.split("：", 1)[-1].strip() if "：" in text else text.split(":", 1)[-1].strip()
                tabs = tree.xpath('//div[contains(@class,"stui-pannel__head")]//ul[contains(@class,"nav")]//a')
                playlists = tree.xpath('//ul[contains(@class,"stui-content__playlist")]')
                fs, us = [], []
                for i, pl in enumerate(playlists):
                    source_name = self._text(tabs[i]) if i < len(tabs) else f"线路{i + 1}"
                    eps = pl.xpath('.//li/a')
                    links = [f"{self._text(a)}${a.get('href', '')}" for a in eps if a.get("href")]
                    if links:
                        fs.append(source_name)
                        us.append("#".join(links))
                vod = {
                    "vod_id": str(vid),
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_year": year,
                    "vod_area": area,
                    "vod_director": director,
                    "vod_actor": actor,
                    "vod_content": content,
                    "vod_remarks": state,
                    "vod_play_from": "$$$".join(fs),
                    "vod_play_url": "$$$".join(us),
                }
                out.append(vod)
            except Exception:
                continue
        return {"list": out}

    def searchContent(self, key, quick, pg="1"):
        try:
            url = f"{self.host}/sou/{quote(key)}-------------.html"
            html = self._get(url)
            items = self._list(html)
            if not items:
                r = self.session.get(f"{self.host}/index.php/ajax/suggest?mid=1&wd={quote(key)}&limit=20", headers=self.headers, timeout=15, verify=False, proxies=getattr(self.session, 'proxies', None) or None)
                data = r.json()
                items = [{"vod_id": str(v.get("id", "")), "vod_name": v.get("name", ""), "vod_pic": v.get("pic", "")} for v in data.get("list", [])]
            return {"list": items, "page": int(pg) if str(pg).isdigit() else 1}
        except Exception:
            return {"list": [], "page": int(pg) if str(pg).isdigit() else 1}

    def playerContent(self, flag, id, vipFlags):
        url = self._fix(id)
        if self._is_media(url) and self._probe_media(url):
            return {"parse": 0, "url": url, "header": json.dumps(self.headers)}
        html = self._get(url)
        idx = html.find("player_aaaa")
        if idx != -1:
            json_start = html.find("{", idx)
            if json_start != -1:
                try:
                    data, _ = json.JSONDecoder().raw_decode(html[json_start:])
                    play_url = data.get("url", "").replace("\\/", "/")
                    if play_url and self._probe_media(play_url):
                        return {"parse": 0, "url": play_url, "header": json.dumps(self.headers)}
                except Exception:
                    pass
        return {"parse": 1, "url": url, "header": json.dumps(self.headers)}
