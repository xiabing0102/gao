# coding=utf-8
# 旺旺影视 (vip.wwgz.cn:5200) - TVBox py源
import re
import json
import html as html_parser
from urllib.parse import quote
from base.spider import Spider


class Spider(Spider):
    HOST = "https://vip.wwgz.cn:5200"
    UA = ("Mozilla/5.0 (Linux; Android 16; 2510DRK44C Build/BP2A.250605.031.A3) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.192 "
          "Mobile Safari/537.36")

    def getName(self):
        return "旺旺影视"

    def init(self, extend=""):
        self.headers = {
            "User-Agent": self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.HOST + "/",
        }

    # ============ 基础 ============
    def _req(self, url):
        try:
            r = self.fetch(url, headers=self.headers, timeout=15)
            if hasattr(r, 'text'):
                return r.text
            return r if isinstance(r, str) else ""
        except Exception as e:
            print(f"[旺旺影视] req error: {e}")
            return ""

    def _clean(self, s):
        if not s:
            return ""
        s = html_parser.unescape(s)
        s = re.sub(r'<[^>]+>', ' ', s)
        return re.sub(r'\s+', ' ', s).strip()

    def _extract_one(self, text, pattern, group=1):
        m = re.search(pattern, text, re.S | re.I)
        return m.group(group).strip() if m else ""

    def _fix(self, u):
        if not u:
            return ""
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("/"):
            return self.HOST + u
        return u

    # ============ 首页 ============
    def homeContent(self, filter):
        classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "连续剧"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "26", "type_name": "短剧"},
            {"type_id": "20", "type_name": "小姐姐"},
            {"type_id": "31", "type_name": "音乐"},
        ]
        filters = {}
        if filter:
            for c in classes:
                cid = c["type_id"]
                filters[cid] = [
                    {"key": "area", "name": "地区", "value": self._area_options()},
                    {"key": "year", "name": "年份", "value": self._year_options()},
                    {"key": "by", "name": "排序", "value": self._order_options()},
                ]
        lst = []
        try:
            html = self._req(self.HOST + "/")
            lst = self._parse_list(html)[:30]
        except Exception:
            pass
        return {"class": classes, "filters": filters, "list": lst}

    def homeVideoContent(self):
        try:
            html = self._req(self.HOST + "/")
            return {"list": self._parse_list(html)[:30]}
        except Exception:
            return {"list": []}

    def _area_options(self):
        return [
            {"n": "全部", "v": ""},
            {"n": "大陆", "v": "大陆"},
            {"n": "香港", "v": "香港"},
            {"n": "台湾", "v": "台湾"},
            {"n": "美国", "v": "美国"},
            {"n": "韩国", "v": "韩国"},
            {"n": "日本", "v": "日本"},
            {"n": "泰国", "v": "泰国"},
            {"n": "英国", "v": "英国"},
            {"n": "法国", "v": "法国"},
            {"n": "其它", "v": "其它"},
        ]

    def _year_options(self):
        years = [{"n": "全部", "v": ""}]
        for y in range(2026, 1999, -1):
            years.append({"n": str(y), "v": str(y)})
        return years

    def _order_options(self):
        return [
            {"n": "按时间", "v": "time"},
            {"n": "按人气", "v": "hit"},
            {"n": "按评分", "v": "score"},
        ]

    # ============ 分类页/首页列表解析 ============
    def _parse_list(self, html):
        if not html:
            return []
        result = []
        seen = set()
        matches = list(re.finditer(
            r'<a[^>]+href="(/vod-detail-id-\d+\.html)"[^>]*title="([^"]*)"',
            html
        ))
        if not matches:
            matches = list(re.finditer(r'<a[^>]+href="(/vod-detail-id-\d+\.html)"', html))
        for i, m in enumerate(matches):
            link = m.group(1)
            vid_m = re.search(r'vod-detail-id-(\d+)', link)
            if not vid_m:
                continue
            vid = vid_m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            if i + 1 < len(matches):
                block_end = matches[i + 1].start()
            else:
                block_end = min(len(html), m.end() + 800)
            block = html[m.start():block_end]

            title = ""
            if m.lastindex and m.lastindex >= 2 and m.group(2):
                title = m.group(2).strip()
            if not title:
                title = self._extract_one(block, r'class="sTit"[^>]*>([^<]+)<')
            if not title:
                title = self._extract_one(block, r'title="([^"]+)"')
            if not title:
                title = vid

            pic = ""
            for pat in [
                r'<img[^>]+src="([^"]+)"',
                r'<img[^>]+data-src="([^"]+)"',
                r'<img[^>]+data-echo="([^"]+)"',
            ]:
                pic = self._extract_one(block, pat)
                if pic:
                    break

            remark = self._extract_one(block, r'class="sBottom"[^>]*>[\s\S]*?<span>([^<]+)<')
            if not remark:
                remark = self._extract_one(block, r'<em>([\d.]+)</em>')

            result.append({
                "vod_id": vid,
                "vod_name": self._clean(title),
                "vod_pic": self._fix(pic),
                "vod_remarks": self._clean(remark),
            })
        return result

    # ============ 分类 ============
    def categoryContent(self, tid, pg, filter, ext):
        try:
            page = int(pg) if str(pg).isdigit() else 1
            ext = self._parse_ext(ext)
            area = quote(ext.get("area", ""), safe='')
            year = ext.get("year", "")
            by = ext.get("by", "") or "time"
            url = (f"{self.HOST}/index.php?m=vod-list-id-{tid}"
                   f"-pg-{page}-order--by-{by}-class-0-year-{year}"
                   f"-letter--area-{area}-lang-.html")
            print(f"[旺旺影视] 分类URL: {url}")
            html = self._req(url)
            if not html:
                return {"list": [], "page": page, "pagecount": 1, "limit": 30, "total": 0}
            vods = self._parse_list(html)
            print(f"[旺旺影视] 第{page}页: {len(vods)}条")
            return {"list": vods, "page": page, "pagecount": 9999, "limit": 30, "total": 9999 * 30}
        except Exception as e:
            print(f"[旺旺影视] category error: {e}")
            return {"list": [], "page": 1, "pagecount": 1, "limit": 30, "total": 0}

    def _parse_ext(self, ext):
        if not ext:
            return {}
        if isinstance(ext, dict):
            return ext
        if isinstance(ext, str):
            ext = ext.strip()
            if not ext or ext in ("{}", "null", "undefined"):
                return {}
            try:
                return json.loads(ext)
            except Exception:
                return {}
        return {}

    # ============ 详情（展开全部线路+剧集）============
    def detailContent(self, ids):
        try:
            vid = ids[0] if isinstance(ids, list) else ids
            if vid.startswith("http"):
                m = re.search(r'vod-detail-id-(\d+)', vid)
                vid = m.group(1) if m else vid
            url = f"{self.HOST}/vod-detail-id-{vid}.html"
            html = self._req(url)
            if not html:
                return {"list": []}

            title = self._extract_one(html, r'<h1 class="title">[\s\S]*?title="([^"]+)"')
            if not title:
                title = self._extract_one(html, r'<h1[^>]*>([^<]+)</h1>')
            pic = self._extract_one(html, r'<section class="page-hd">[\s\S]*?<img src="([^"]+)"')
            if not pic:
                pic = self._extract_one(html, r'<meta property="og:image" content="([^"]+)"')

            names = []
            line_box = self._extract_one(html, r'<div class="hd">[\s\S]*?<ul>([\s\S]*?)</ul>')
            if line_box:
                names = re.findall(r'<a[^>]*>([^<]+)</a>', line_box)

            play_from = []
            play_url = []
            blocks = re.findall(r'<div id="\w+" class="numList">([\s\S]*?)</div>', html)
            if not blocks:
                blocks = re.findall(r'<div class="numList">([\s\S]*?)</div>', html)
            for idx, blk in enumerate(blocks):
                eps = re.findall(
                    r'href="(/vod-play-id-' + str(vid) + r'-src-\d+-num-\d+\.html)"[^>]*>([^<]+)</a>',
                    blk
                )
                if not eps:
                    continue
                ep_list = []
                for ep_url, ep_name in eps:
                    ep_name = ep_name.strip() or "正片"
                    ep_list.append(f"{ep_name}${ep_url}")
                lname = names[idx] if idx < len(names) else f"线路{idx+1}"
                play_from.append(lname)
                play_url.append("#".join(ep_list))

            print(f"[旺旺影视] 详情 {vid}: {len(play_from)}条线路")
            return {"list": [{
                "vod_id": vid,
                "vod_name": self._clean(title) or vid,
                "vod_pic": self._fix(pic),
                "vod_content": self._clean(title),
                "vod_play_from": "$$$".join(play_from) if play_from else "线路①",
                "vod_play_url": "$$$".join(play_url) if play_url else f"第01集$/vod-play-id-{vid}-src-1-num-1.html",
            }]}
        except Exception as e:
            print(f"[旺旺影视] detail error: {e}")
            return {"list": []}

    # ============ 播放（取 mac_url 明文表）============
    def playerContent(self, flag, id, vipFlags):
        try:
            url = id if id.startswith("http") else (self.HOST + id if id.startswith("/") else f"{self.HOST}/{id}")
            if any(x in url for x in [".m3u8", ".mp4"]):
                return {"parse": 0, "playUrl": "", "url": url, "header": self.headers}
            html = self._req(url)
            if not html:
                return {"parse": 1, "url": url, "header": self.headers}
            m = re.search(r"var\s+mac_url\s*=\s*'([^']+)'", html)
            if not m:
                print("[旺旺影视] 未找到 mac_url")
                return {"parse": 1, "url": url, "header": self.headers}
            sources = m.group(1).split("$$$")
            num_m = re.search(r'num-(\d+)', url)
            idx = int(num_m.group(1)) - 1 if num_m else 0
            first = sources[0].split("#")
            if 0 <= idx < len(first):
                target = first[idx]
            else:
                target = first[0]
            real = target.split("$")[-1]
            print(f"[旺旺影视] 播放解析: {real[:70]}...")
            return {"parse": 0, "playUrl": "", "url": real, "header": self.headers}
        except Exception as e:
            print(f"[旺旺影视] player error: {e}")
            return {"parse": 1, "url": id, "header": self.headers}

    # ============ 搜索（GET 提交）============
    def searchContent(self, key, quick, pg="1"):
        try:
            kw = quote(str(key).strip())
            url = f"{self.HOST}/index.php?m=vod-search&wd={kw}"
            print(f"[旺旺影视] 搜索URL: {url}")
            html = self._req(url)
            vods = self._parse_search(html)
            print(f"[旺旺影视] 搜索'{key}': {len(vods)}条")
            return {"list": vods, "page": 1, "pagecount": 1, "limit": 30, "total": len(vods)}
        except Exception as e:
            print(f"[旺旺影视] search error: {e}")
            return {"list": [], "page": 1, "pagecount": 1, "limit": 30, "total": 0}

    def searchContentPage(self, key, quick, pg="1"):
        return self.searchContent(key, quick, pg)

    # ============ 搜索页解析（标题在 span.sTit）============
    def _parse_search(self, html):
        if not html:
            return []
        result = []
        seen = set()
        blocks = re.findall(r'<li>([\s\S]*?)</li>', html)
        for block in blocks:
            hm = re.search(r'href="(/vod-detail-id-(\d+)\.html)"', block)
            if not hm:
                continue
            vid = hm.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            title = self._extract_one(block, r'class="sTit"[^>]*>([^<]+)<')
            if not title:
                title = self._extract_one(block, r'<a[^>]+title="([^"]+)"')
            pic = self._extract_one(block, r'<img[^>]+src="([^"]+)"')
            if not pic:
                pic = self._extract_one(block, r'<img[^>]+data-src="([^"]+)"')
            remark = self._extract_one(block, r'class="sStyle"[^>]*>([^<]+)<')
            result.append({
                "vod_id": vid,
                "vod_name": self._clean(title) or vid,
                "vod_pic": self._fix(pic),
                "vod_remarks": self._clean(remark),
            })
        return result

    # ============ 其他 ============
    def isVideoFormat(self, url):
        return any(x in (url or "") for x in [".m3u8", ".mp4", ".ts"])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        return [404, "text/plain", "", ""]