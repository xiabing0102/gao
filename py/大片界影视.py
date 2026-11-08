#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大片界影视 TVBox Python Spider
✅ 首页正常加载
✅ 分类tid使用纯数字，修复路径解析问题
✅ MacCMS /tv/1.html 分类页面
✅ 搜索增加容错优化，空关键词防报错
"""
import re
import json
import ssl
import gzip
import base64
import urllib.request
import urllib.parse
import html as html_mod

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def getName(self): return ""
        def homeContent(self, filter): return {}
        def homeVideoContent(self): return {}
        def categoryContent(self, tid, pg, filter, extend): return {}
        def detailContent(self, ids): return {}
        def searchContent(self, key, quick, pg="1"): return {}
        def playerContent(self, flag, id, vipFlags): return {}


class Spider(BaseSpider):
    BASE_URL = "https://www.janatomo.com"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    def init(self, extend=""):
        pass

    def getName(self):
        return "大片界影视"

    # 网络请求
    def getHtml(self, url):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={
                "User-Agent": self.UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Referer": self.BASE_URL + "/",
            })
            with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
                data = resp.read()
                if "gzip" in resp.headers.get("Content-Encoding", ""):
                    data = gzip.decompress(data)
                for enc in ["utf-8", "gbk", "gb2312"]:
                    try:
                        return data.decode(enc)
                    except Exception:
                        continue
                return data.decode("utf-8", errors="replace")
        except Exception:
            return ""

    def clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        return re.sub(r"\s+", " ", text).strip()

    # 解析视频卡片
    def _parse_cards(self, html):
        videos, seen = [], set()
        for m in re.finditer(r'<a[^>]+href="/video/(\d+)\.html"[^>]*>([\s\S]*?)</a>', html):
            vid, block = m.group(1), m.group(2)
            if vid in seen:
                continue
            seen.add(vid)

            name = ""
            nm = re.search(r'alt="([^"]+)"', block)
            if nm:
                name = self.clean(nm.group(1))
            if not name:
                nm = re.search(r'<h5 class="subject"><a[^>]*>([^<]+)</a>', block)
                if nm:
                    name = self.clean(nm.group(1))
            if not name:
                continue

            pic = ""
            pm = re.search(r'data-original="([^"]+)"', block)
            if pm:
                pic = pm.group(1)
                if pic.startswith("//"):
                    pic = "https:" + pic

            remarks = ""
            rm = re.search(r'<span class="hot">([^<]+)</span>', block)
            if rm:
                remarks = self.clean(rm.group(1))

            videos.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remarks
            })
        return videos

    # 首页分类【tid纯数字】
    def homeContent(self, filter):
        cats = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "3", "type_name": "短剧"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "5", "type_name": "综艺"},
        ]
        return {"class": cats, "filters": {}}

    # 首页推荐列表
    def homeVideoContent(self):
        try:
            html = self.getHtml(self.BASE_URL)
            lst = self._parse_cards(html)[:30]
            return {"list": lst}
        except Exception:
            return {"list": []}

    # 分类页面：tid数字，内部拼接真实地址 /tv/{tid}.html
    def categoryContent(self, tid, pg, filter, extend):
        res = {"list": [], "page": pg, "pagecount": pg, "total": "0"}
        try:
            page = int(pg)
            tid_num = str(tid)
            if page == 1:
                cat_url = f"{self.BASE_URL}/tv/{tid_num}.html"
            else:
                cat_url = f"{self.BASE_URL}/tv/{tid_num}/page/{page}.html"

            html = self.getHtml(cat_url)
            if not html:
                return res
            res["list"] = self._parse_cards(html)
            if re.search(r"下一页", html):
                res["pagecount"] = str(page + 1)
        except Exception as e:
            pass
        return res

    # ========== 搜索 增加容错优化 ==========
    def searchContent(self, key, quick, pg="1"):
        res = {"list": [], "page": pg, "pagecount": pg, "total": "0"}
        # 去除首尾空格，空关键词直接返回空，不请求网页
        key = self.clean(key)
        if not key:
            return res
        try:
            page = int(pg)
            url = f"{self.BASE_URL}/search.html?wd={urllib.parse.quote(key)}&page={page}"
            html = self.getHtml(url)
            raw_list = self._parse_cards(html)
            res["list"] = raw_list[:25] # 限制搜索结果条数，减轻压力
            if re.search(r"下一页", html):
                res["pagecount"] = str(page + 1)
        except Exception:
            pass
        return res

    # 详情页
    def detailContent(self, ids):
        result = {"list": []}
        try:
            vid = str(ids[0]).split(",")[0].strip()
            html = self.getHtml(f"{self.BASE_URL}/video/{vid}.html")
            if not html:
                return result

            vod = {"vod_id": vid}
            h1 = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
            vod["vod_name"] = self.clean(h1.group(1)) if h1 else ""
            pic_match = re.search(r'data-original="([^"]+)"', html)
            vod["vod_pic"] = pic_match.group(1).replace("//", "https://") if pic_match else ""
            desc_match = re.search(r'og:description" content="([^"]+)"', html)
            vod["vod_content"] = self.clean(desc_match.group(1)) if desc_match else ""

            play_from, play_url = [], []
            sources = {}
            for ep_reg in re.finditer(r'href="/play/' + re.escape(vid) + r'/(\d+)/([^"]+)\.html"', html):
                sid, ep = ep_reg.group(1), ep_reg.group(2)
                sources.setdefault(sid, [])
                sources[sid].append(ep)

            for sid in sorted(sources.keys(), key=int):
                eps = []
                for ep in sources[sid]:
                    eps.append(f"{ep}${self.BASE_URL}/play/{vid}/{sid}/{ep}.html")
                play_from.append(f"线路{sid}")
                play_url.append("#".join(eps))

            vod["vod_play_from"] = "$$$".join(play_from)
            vod["vod_play_url"] = "$$$".join(play_url)
            result["list"] = [vod]
        except Exception:
            pass
        return result

    # 播放器解析
    def _get_play_src(self, html):
        js_data = re.search(r"playerdata\s*=\s*({[\s\S]+?})", html)
        if js_data:
            try:
                j = json.loads(js_data.group(1))
                u = j.get("url", "")
                encrypt = str(j.get("encrypt", "0"))
                if encrypt == "2":
                    u = base64.b64decode(u).decode("utf-8")
                u = urllib.parse.unquote(u)
                if u.startswith("http"):
                    return u
            except:
                pass
        r = re.search(r'["\']url["\']\s*:\s*["\']([^"\']+?(m3u8|mp4))', html)
        if r:
            u = r.group(1)
            if u.startswith("//"):
                u = "https:" + u
            return u
        return ""

    def playerContent(self, flag, id, vipFlags):
        play_page_url = id
        header = json.dumps({"User-Agent": self.UA, "Referer": self.BASE_URL})
        try:
            html = self.getHtml(play_page_url)
            real_url = self._get_play_src(html)
            if real_url:
                return {"parse": "0", "url": real_url, "header": header}
            return {"parse": "1", "url": play_page_url, "header": header}
        except Exception:
            return {"parse": "1", "url": play_page_url, "header": header}

    def localProxy(self, param=""):
        return None
    def isVideoFormat(self, url):
        return bool(re.search(r"\.(m3u8|mp4)", url))
    def manualVideoCheck(self):
        return False
