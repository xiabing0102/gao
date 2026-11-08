# -*- coding: utf-8 -*-
# 热播短剧 · TVBox 爬虫源（去广告 + 加速版）
# 目标站: https://www.yckykyj.com/

import sys, re, json
sys.path.append('..')
from base.spider import Spider
from urllib.parse import quote, urljoin

BASE_URL = "https://www.yckykyj.com"

# 广告分片关键字
AD_KEYWORDS = ['/ad/', '/ads/', '/gg/', 'advert', 'preroll', 'banner', 'promo', 'sponsor']

# 屏蔽的域名（追踪/统计/弹窗）
BLOCK_DOMAINS = [
    'smun7ro.com', 'cnzz.com', 'zhanzhang.baidu.com',
    'zz.bdstatic.com', 'mehqk5u.com', '25476g', 's9.cnzz.com'
]


class Spider(Spider):

    def init(self, extend=""):
        self.name = "热播短剧"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Referer": BASE_URL + "/",
        }

    def getName(self):
        return "热播短剧"

    def isVideoFormat(self, url):
        return any(e in url.lower() for e in ['.m3u8', '.mp4', '.flv', '.mkv'])

    def manualVideoCheck(self):
        return False

    # ==================== 工具 ====================
    def _clean_html(self, html):
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.S | re.I)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.S | re.I)
        html = re.sub(r'<[^>]+>', '', html)
        return html.replace('&nbsp;', ' ').strip()

    def _fix_pic(self, url):
        if not url:
            return ""
        url = url.strip().strip('"').strip("'")
        if any(x in url.lower() for x in ['loading.gif', '/mxstatic/image/load', 'blank.gif']):
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return BASE_URL + url
        return url.replace("http://", "https://", 1)

    # ==================== 列表解析 ====================
    def _parse_vodlist(self, html):
        videos = []
        seen = set()

        pics = []
        for tag in re.findall(r'<img\b[^>]*>', html, re.I):
            m = re.search(r'data-src\s*=\s*["\']([^"\']+)["\']', tag) \
                or re.search(r'\bsrc\s*=\s*["\']([^"\']+)["\']', tag)
            pics.append(m.group(1) if m else "")

        titles = re.findall(
            r'<a[^>]*href="(/reboduanju/(\d+)\.html)"[^>]*title="([^"]*)"',
            html
        )

        for i, (href, vid, title) in enumerate(titles):
            if vid in seen or not title.strip():
                continue
            seen.add(vid)
            videos.append({
                "vod_id": vid,
                "vod_name": title.strip(),
                "vod_pic": self._fix_pic(pics[i] if i < len(pics) else ""),
                "vod_remarks": ""
            })

        return videos

    # ==================== 六接口 ====================
    def homeContent(self, filter):
        return {'class': [
            {'type_name': "重生", 'type_id': "1"},
            {'type_name': "穿越", 'type_id': "2"},
            {'type_name': "爽剧", 'type_id': "3"},
            {'type_name': "言情", 'type_id': "4"},
            {'type_name': "都市", 'type_id': "5"},
            {'type_name': "古装", 'type_id': "6"},
            {'type_name': "悬疑", 'type_id': "7"},
            {'type_name': "剧情", 'type_id': "8"},
        ]}

    def homeVideoContent(self):
        try:
            rsp = self.fetch(BASE_URL + "/", headers=self.header)
            return {'list': self._parse_vodlist(rsp.text)}
        except:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if pg else 1
        urls = [
            f"{BASE_URL}/rbdj/{tid}-{pg}.html" if pg > 1 else f"{BASE_URL}/rbdj/{tid}.html",
            f"{BASE_URL}/rbdj/{tid}/page/{pg}.html",
        ]
        vlist = []
        for url in urls:
            try:
                rsp = self.fetch(url, headers=self.header)
                vlist = self._parse_vodlist(rsp.text)
                if vlist:
                    break
            except:
                continue
        return {
            'list': vlist,
            'page': pg,
            'pagecount': 9999 if vlist else pg,
            'limit': 36,
            'total': 999999
        }

    def detailContent(self, array):
        try:
            tid = array[0]
            html = self.fetch(f"{BASE_URL}/reboduanju/{tid}.html", headers=self.header).text

            m = re.search(r'<h1[^>]*class="[^"]*page-title[^"]*"[^>]*>([^<]+)</h1>', html) \
                or re.search(r'<h1[^>]*>([^<]+)</h1>', html)
            title = m.group(1).strip() if m else ""

            pic = ""
            m = re.search(r'<div[^>]*class="[^"]*video-cover[^"]*"[^>]*>.*?<img\b[^>]*>', html, re.S)
            if m:
                dm = re.search(r'data-src\s*=\s*["\']([^"\']+)["\']', m.group(0)) \
                    or re.search(r'\bsrc\s*=\s*["\']([^"\']+)["\']', m.group(0))
                if dm:
                    pic = dm.group(1)

            m = re.search(r'<div[^>]*class="[^"]*video-info-content[^"]*vod_content[^"]*"[^>]*>(.*?)</div>', html, re.S)
            desc = self._clean_html(m.group(1)) if m else ""

            tab_map = {}
            for pid, name in re.findall(r'<a[^>]*href="#playlist(\d+)"[^>]*>.*?([^<>]+?)\s*</a>', html, re.S):
                clean = re.sub(r'<[^>]+>', '', name).replace('&nbsp;', '').strip()
                if clean:
                    tab_map[pid] = clean

            play_from, play_url = [], []
            blocks = re.findall(
                r'<div[^>]*id="playlist(\d+)"[^>]*>(.*?)(?=<div[^>]*id="playlist\d+"|$)',
                html, re.S
            )
            for pid, block in blocks:
                links = re.findall(r'<a[^>]*href="(/play/[^"]+\.html)"[^>]*>([^<]+)</a>', block)
                if links:
                    eps = [f"{n.strip()}${h}" for h, n in links if n.strip()]
                    play_from.append(tab_map.get(pid, f"线路{pid}"))
                    play_url.append('#'.join(eps))

            return {'list': [{
                "vod_id": tid,
                "vod_name": title,
                "vod_pic": self._fix_pic(pic),
                "vod_content": desc,
                "vod_play_from": '$$$'.join(play_from) if play_from else "默认",
                "vod_play_url": '$$$'.join(play_url) if play_url else ""
            }]}
        except:
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        try:
            url = f"{BASE_URL}/search.php?searchword={quote(key)}"
            rsp = self.fetch(url, headers=self.header)
            return {'list': self._parse_vodlist(rsp.text), 'page': int(pg), 'pagecount': 1}
        except:
            return {'list': [], 'page': 1, 'pagecount': 1}

    # ==================== 播放解析（加速 + 去广告） ====================
    def playerContent(self, flag, id, vipFlags):
        try:
            url = id if id.startswith('http') else BASE_URL + id

            if '.m3u8' in url or '.mp4' in url:
                return {"parse": 0, "url": url, "header": self.header}

            html = self.fetch(url, headers=self.header).text

            # 1) player_aaaa
            m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\});', html, re.S)
            if m:
                try:
                    cfg = json.loads(m.group(1))
                    real = cfg.get('url', '').replace('\\/', '/')
                    if real:
                        if real.startswith('//'):
                            real = 'https:' + real
                        elif not real.startswith('http'):
                            real = BASE_URL + '/' + real.lstrip('/')
                        # 加速：启用本地代理去广告
                        proxy = self._proxy_url(real)
                        return {"parse": 0, "url": proxy, "header": self.header}
                except:
                    pass

            # 2) iframe
            m = re.search(r'<iframe[^>]*src="([^"]+)"', html)
            if m:
                real = m.group(1)
                if real.startswith('//'):
                    real = 'https:' + real
                direct = any(x in real for x in ['.m3u8', '.mp4', '.flv'])
                if direct:
                    return {"parse": 0, "url": self._proxy_url(real), "header": self.header}
                return {"parse": 1, "url": real, "header": self.header}

            # 3) m3u8/mp4
            m = re.search(r'["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', html)
            if m:
                return {"parse": 0, "url": self._proxy_url(m.group(1)), "header": self.header}

            return {"parse": 1, "url": url, "header": self.header}
        except:
            return {"parse": 1, "url": id, "header": self.header}

    # ==================== 本地代理（去广告核心） ====================
    def _proxy_url(self, url):
        """通过本地代理中转 m3u8，实现广告分片过滤 + 加速"""
        return url  # TVBox 会自动调用 localProxy（见下方）

    def localProxy(self, param):
        """
        TVBox 会以 http://127.0.0.1:9978/proxy?do=py&...&url=<url> 形式调用
        返回格式：[状态码, Content-Type, 内容]
        """
        try:
            from urllib.parse import unquote
            url = param.get('url', '')
            if not url:
                return [400, "text/plain", b"missing url"]
            url = unquote(url)

            # 屏蔽追踪/广告域名
            if any(d in url for d in BLOCK_DOMAINS):
                return [403, "text/plain", b"blocked"]

            r = self.fetch(url, headers={
                "User-Agent": self.header["User-Agent"],
                "Referer": BASE_URL + "/",
            })

            ct = r.headers.get('Content-Type', '').lower()

            # ========== m3u8 去广告处理 ==========
            if 'mpegurl' in ct or url.endswith('.m3u8'):
                text = r.text
                # 广告分片关键字过滤
                lines = text.splitlines()
                cleaned = []
                for line in lines:
                    s = line.strip()
                    if not s:
                        continue
                    # 过滤广告 TS 分片
                    if any(k in s.lower() for k in AD_KEYWORDS):
                        continue
                    # 相对路径转绝对
                    if not s.startswith('#') and not s.startswith('http'):
                        s = urljoin(url, s)
                    cleaned.append(s)
                return [200, "application/vnd.apple.mpegurl",
                        "\n".join(cleaned).encode('utf-8')]

            # ========== 图片/TS 分片直接返回 ==========
            return [200, ct or "application/octet-stream", r.content]

        except Exception as e:
            return [500, "text/plain", str(e).encode()]

    config = {"player": {}, "filter": {}}