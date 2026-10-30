#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import re
import base64
import urllib.parse
import requests
from lxml import etree
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "咕噜电影"

    def init(self, extend=""):
        self.name = "咕噜电影"
        self.host = "https://www.guludyw.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
            "Referer": self.host + "/"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.categories = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "3", "type_name": "动漫"},
            {"type_id": "4", "type_name": "综艺"},
            {"type_id": "10", "type_name": "短剧"}
        ]

    def _get(self, url):
        try:
            r = self.session.get(url, timeout=15, verify=False, proxies=self.session.proxies or None)
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except Exception:
            return ""

    def _fix(self, u):
        if not u:
            return ""
        if u.startswith("http"):
            return u
        return self.host + (u if u.startswith("/") else "/" + u)

    def _list(self, html):
        out = []
        seen = set()
        try:
            tree = etree.HTML(html)
        except Exception:
            return out
        boxes = tree.xpath('//div[contains(@class,"list_yy")]//li | //div[contains(@class,"list_search")]//li')
        for li in boxes:
            try:
                a = li.xpath('.//a[contains(@href,"vod-read-id-")]')
                if not a:
                    continue
                a = a[0]
                href = a.get("href") or ""
                m = re.search(r"id-(\d+)\.html", href)
                if not m or m.group(1) in seen:
                    continue
                seen.add(m.group(1))
                img = a.xpath('.//img')[0] if a.xpath('.//img') else None
                pic = self._fix((img.get("src") or "") if img is not None else "")
                name = (a.get("title") or (img.get("alt") if img is not None else "") or "".join(a.xpath(".//text()")).strip() or str(m.group(1)))
                rem = ""
                ol = li.xpath('.//ol')
                if ol:
                    rem = " ".join(t.strip() for t in ol[0].xpath(".//text()") if t.strip())
                item = {"vod_id": m.group(1), "vod_name": name, "vod_pic": pic}
                if rem:
                    item["vod_remarks"] = rem
                out.append(item)
            except Exception:
                continue
        return out

    def _pagecount(self, html, pg):
        try:
            tree = etree.HTML(html)
        except Exception:
            return pg
        nums = []
        for a in tree.xpath('//div[contains(@class,"wap_page")]//a'):
            h = a.get("href") or ""
            mm = re.search(r"-p-(\d+)\.html", h)
            if mm:
                nums.append(int(mm.group(1)))
            else:
                t = "".join(a.xpath(".//text()")).strip()
                if t.isdigit():
                    nums.append(int(t))
        nxt = tree.xpath('//div[contains(@class,"wap_page")]//a[contains(@href,"-p-%d") or contains(normalize-space(.),"下一页")]' % (pg + 1))
        return max(nums + [pg + 1 if nxt else pg]) if nums else (pg + 1 if nxt else pg)

    def homeContent(self, filter):
        return {"class": self.categories, "list": self._list(self._get(self.host + "/index.php")), "filters": {}}

    def homeVideoContent(self):
        return {"list": self._list(self._get(self.host + "/index.php"))}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if str(pg).isdigit() else 1
        url = self.host + "/index.php?s=vod-show-id-%s.html" % tid
        if pg > 1:
            url = self.host + "/index.php?s=vod-show-id-%s-p-%d.html" % (tid, pg)
        html = self._get(url)
        items = self._list(html)
        pagecount = self._pagecount(html, pg)
        return {"page": pg, "pagecount": pagecount, "limit": len(items) or 20, "total": pagecount * (len(items) or 20), "list": items}

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else str(ids)
        if isinstance(vid, str) and not vid.isdigit():
            mm = re.search(r"(\d+)", vid)
            vid = mm.group(1) if mm else vid
        out = []
        try:
            tree = etree.HTML(self._get(self.host + "/index.php?s=vod-read-id-%s.html" % vid))
            h1s = tree.xpath("//h1")
            name = "".join(h1s[0].xpath(".//text()")).strip() if h1s else str(vid)
            pic = self._fix((tree.xpath('//div[contains(@class,"text_img")]//img/@src') or [""])[0])
            fs = []
            us = []
            for show in tree.xpath('//div[contains(@class,"show_1")]'):
                h2 = show.xpath('./div/h2/text()')
                src = re.sub(r"\s+", "", "".join(h2).strip()) or "播放源%d" % (len(fs) + 1)
                eps = show.xpath('.//a[contains(@href,"vod-play-id-")]')
                links = []
                for a in eps:
                    h = a.get("href") or ""
                    t = "".join(a.xpath(".//text()")).strip()
                    if not h:
                        continue
                    links.append((t or h, self._fix(h)))
                if links:
                    fs.append(src)
                    us.append("#".join("%s$%s" % (t, u) for t, u in links))
            item = {"vod_id": str(vid), "vod_name": name, "vod_pic": pic}
            item["vod_play_from"] = "$$$".join(fs) if fs else ""
            item["vod_play_url"] = "$$$".join(us) if us else ""
            out.append(item)
        except Exception:
            pass
        return {"list": out}

    def searchContent(self, key, quick, pg="1"):
        html = self._get(self.host + "/index.php?s=vod-search&wd=" + urllib.parse.quote(key))
        return {"page": int(pg) if str(pg).isdigit() else 1, "list": self._list(html)}

    def playerContent(self, flag, id, vipFlags):
        url = self._fix(id)
        if not re.search(r"vod-play-id-", url):
            return {"parse": 1, "url": url, "header": json.dumps(self.headers)}
        html = self._get(url)
        m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html)
        if m:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(m.group(1)).query)
            mu = q.get("mu", [""])[0]
            if mu:
                try:
                    direct = base64.b64decode(urllib.parse.unquote(mu) + "=" * (-len(mu) % 4)).decode("utf-8", "ignore")
                except Exception:
                    direct = ""
                if direct:
                    return {"parse": 0, "url": direct, "header": json.dumps({"User-Agent": self.headers["User-Agent"], "Referer": "https://dvvs.fengniaotv.com/"})}
        allmu = re.search(r"mu=([^&\"'\s]+)", html)
        if allmu:
            try:
                direct = base64.b64decode(urllib.parse.unquote(allmu.group(1)) + "=" * (-len(allmu.group(1)) % 4)).decode("utf-8", "ignore")
            except Exception:
                direct = ""
            if direct:
                return {"parse": 0, "url": direct, "header": json.dumps({"User-Agent": self.headers["User-Agent"], "Referer": "https://dvvs.fengniaotv.com/"})}
        return {"parse": 1, "url": url, "header": json.dumps(self.headers)}