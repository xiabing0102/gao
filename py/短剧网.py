# -*- coding: utf-8 -*-
# 短剧网 · a2zshow.com · TVBox 爬虫
# 严格遵循遮天法 · 完全自包含

import re
import json
import html as html_module
import threading
from urllib.parse import quote

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        pass

import requests


# ============================================================
#  配置
# ============================================================
CONFIG = {
    "name": "短剧网",
    "host": "https://www.a2zshow.com",
    "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.a2zshow.com/",
    },
}

# 8 大类
CLASSES = [
    ("重生", "1"),
    ("穿越", "2"),
    ("爽剧", "3"),
    ("言情", "4"),
    ("都市", "5"),
    ("古装", "6"),
    ("悬疑", "7"),
    ("剧情", "8"),
]


# ============================================================
#  工具
# ============================================================
def clean_text(raw):
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", "", str(raw))
    text = html_module.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fix_pic(url):
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("http://"):
        return "https://" + url[7:]
    if url.startswith("/"):
        return CONFIG["host"] + url
    if not url.startswith("http"):
        return CONFIG["host"] + "/" + url.lstrip("/")
    return url


# ============================================================
#  主类
# ============================================================
class Spider(BaseSpider):

    def __init__(self):
        super().__init__()
        self.host = CONFIG["host"]
        self.headers = dict(CONFIG["headers"])
        self._local = threading.local()

    def _session(self):
        if not hasattr(self._local, "s"):
            s = requests.Session()
            s.headers.update(self.headers)
            self._local.s = s
        return self._local.s

    def _get(self, url, **kw):
        try:
            return self._session().get(url, timeout=15, allow_redirects=True, **kw)
        except Exception as e:
            print(f"[get] {e}")
            return None

    # ---------- TVBox 接口 ----------
    def init(self, extend=""):
        pass

    def getName(self):
        return CONFIG["name"]

    def isVideoFormat(self, url):
        return any(x in url.lower() for x in [".m3u8", ".mp4", ".flv", ".ts"])

    def manualVideoCheck(self):
        return False

    # ============================================================
    #  首页分类
    # ============================================================
    def homeContent(self, filter=False):
        classes = [{"type_id": tid, "type_name": name} for name, tid in CLASSES]
        return {"class": classes}

    # ============================================================
    #  分类内容
    # ============================================================
    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg or 1)
            if pg <= 1:
                url = f"{self.host}/list/{tid}.html"
            else:
                url = f"{self.host}/list/{tid}-{pg}.html"

            r = self._get(url)
            if not r:
                return {"list": [], "page": pg, "pagecount": 1}

            videos = self._parse_list(r.text)
            has_next = bool(re.search(rf'/list/{tid}-\d+\.html', r.text)) or bool(re.search(r'下一页', r.text))

            return {
                "list": videos,
                "page": pg,
                "pagecount": pg + 1 if has_next else pg,
                "limit": len(videos),
                "total": 999999,
            }
        except Exception as e:
            print(f"[category] {e}")
            return {"list": [], "page": int(pg or 1), "pagecount": 1}

    def _parse_list(self, html):
        """列表页解析"""
        videos = []
        seen = set()

        pattern = re.compile(
            r'<a[^>]*class="fed-list-pics[^"]*"[^>]*'
            r'href="(/show/(\d+)\.html)"[^>]*'
            r'data-original="([^"]*)"[^>]*'
            r'title="([^"]*)"[^>]*>'
            r'(.*?)</a>',
            re.S | re.I
        )
        for m in pattern.finditer(html):
            href, vid, pic, title, inner = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
            if vid in seen:
                continue
            remark_m = re.search(r'<span[^>]*class="fed-list-remarks[^"]*"[^>]*>([^<]+)</span>', inner)
            remark = clean_text(remark_m.group(1)) if remark_m else ""
            seen.add(vid)
            videos.append({
                "vod_id": vid,
                "vod_name": clean_text(title),
                "vod_pic": fix_pic(pic),
                "vod_remarks": remark,
            })

        # 兜底
        if not videos:
            for m in re.finditer(
                r'<a[^>]*href="(/show/(\d+)\.html)"[^>]*title="([^"]*)"[^>]*data-original="([^"]*)"',
                html, re.S
            ):
                href, vid, title, pic = m.group(1), m.group(2), m.group(3), m.group(4)
                if vid in seen:
                    continue
                seen.add(vid)
                videos.append({
                    "vod_id": vid,
                    "vod_name": clean_text(title),
                    "vod_pic": fix_pic(pic),
                    "vod_remarks": "",
                })

        return videos

    # ============================================================
    #  详情
    # ============================================================
    def detailContent(self, ids):
        try:
            vod_id = ids[0] if isinstance(ids, list) else ids
            if not vod_id:
                return {"list": []}

            url = f"{self.host}/show/{vod_id}.html"
            r = self._get(url)
            if not r:
                return {"list": []}
            html = r.text

            # 标题
            title_m = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]*)"', html) \
                      or re.search(r'<h1[^>]*>([^<]+)</h1>', html) \
                      or re.search(r'<title>([^<]+)</title>', html)
            title = clean_text(title_m.group(1)) if title_m else ""

            # 封面
            pic_m = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]*)"', html) \
                    or re.search(r'<img[^>]*data-original="([^"]+)"', html) \
                    or re.search(r'<img[^>]*src="([^"]+)"', html)
            pic = fix_pic(pic_m.group(1)) if pic_m else ""

            # 简介
            desc_m = re.search(r'<meta[^>]*property="og:description"[^>]*content="([^"]*)"', html) \
                     or re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html, re.I)
            desc = desc_m.group(1).strip() if desc_m else ""

            # 播放源：优先从 og:video 拿播放页 URL
            play_from, play_url = [], []

            og_video_m = re.search(r'<meta[^>]*property="og:video"[^>]*content="([^"]*)"', html)
            if og_video_m:
                play_page = og_video_m.group(1).strip()
                play_from.append("默认")
                play_url.append(f"正片${play_page}")

            # 兜底1：详情页里含 /play/{id}-*.html 链接
            if not play_from:
                play_links = re.findall(
                    r'href="(/play/' + re.escape(str(vod_id)) + r'-\d+-\d+\.html)"',
                    html
                )
                if play_links:
                    eps = [f"正片${link}" for link in dict.fromkeys(play_links)]
                    play_from.append("默认")
                    play_url.append("#".join(eps))

            # 兜底2：构造标准播放 URL
            if not play_from:
                play_from.append("默认")
                play_url.append(f"正片$/play/{vod_id}-0-0.html")

            print(f"[详情] {vod_id} - {title} - 播放源: {play_url}")

            return {"list": [{
                "vod_id": str(vod_id),
                "vod_name": title,
                "vod_pic": pic,
                "vod_content": desc,
                "vod_play_from": "$$$".join(play_from),
                "vod_play_url": "$$$".join(play_url),
            }]}
        except Exception as e:
            print(f"[detail] {e}")
            return {"list": []}

    # ============================================================
    #  播放
    # ============================================================
    def playerContent(self, flag, id, vipFlags=None):
        try:
            if not id:
                return {"parse": 0, "url": "", "header": {}}

            url = id if id.startswith("http") else self.host + id
            print(f"[播放] 请求: {url}")

            # 直链
            if self.isVideoFormat(url):
                return {"parse": 0, "url": url, "header": {"Referer": self.host + "/"}}

            r = self._get(url, headers={
                "Referer": self.host + "/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            })
            if not r:
                return {"parse": 1, "url": url, "header": {"Referer": self.host + "/"}}

            html = r.text
            print(f"[播放] 页面长度: {len(html)}")

            # ---- 优先级1：JS 变量 player_aaaa / player_data / player_json ----
            for var_name in ["player_aaaa", "player_data", "player_json"]:
                m = re.search(rf'var\s+{var_name}\s*=\s*(\{{.*?\}})\s*;', html, re.S)
                if m:
                    try:
                        data = json.loads(m.group(1))
                        for key in ["url", "video", "playurl"]:
                            v = data.get(key)
                            if v and isinstance(v, str) and v.startswith("http"):
                                v = v.replace("\\/", "/").strip()
                                print(f"[播放] ✓ JS变量({var_name}).{key}: {v}")
                                return {
                                    "parse": 0,
                                    "url": v,
                                    "header": {"Referer": self.host + "/"},
                                }
                    except Exception as e:
                        print(f"[播放] JSON解析失败: {e}")

            # ---- 优先级2：m3u8 / mp4 直链 ----
            m = re.search(
                r'["\']?(https?://[^\s"\'<>\\]+\.(?:m3u8|mp4)[^\s"\'<>\\]*)["\']?',
                html
            )
            if m:
                real_url = m.group(1).replace("\\/", "/").strip()
                print(f"[播放] ✓ m3u8/mp4 直链: {real_url}")
                return {
                    "parse": 0,
                    "url": real_url,
                    "header": {"Referer": self.host + "/"},
                }

            # ---- 优先级3：iframe / video / source ----
            for tag in ["iframe", "video", "source"]:
                m = re.search(rf'<{tag}[^>]*src=["\']([^"\']+)["\']', html, re.I)
                if m:
                    real_url = m.group(1).replace("\\/", "/").strip()
                    if real_url.startswith("//"):
                        real_url = "https:" + real_url
                    if real_url.startswith("http"):
                        print(f"[播放] ✓ {tag}: {real_url}")
                        return {
                            "parse": 0,
                            "url": real_url,
                            "header": {"Referer": self.host + "/"},
                        }

            # ---- 优先级4：URL 参数 ----
            for key in ["url", "video", "src", "source", "playurl"]:
                m = re.search(
                    rf'["\']{key}["\']\s*[:=]\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
                    html, re.I
                )
                if m:
                    real_url = m.group(1).replace("\\/", "/").strip()
                    print(f"[播放] ✓ url参数({key}): {real_url}")
                    return {
                        "parse": 0,
                        "url": real_url,
                        "header": {"Referer": self.host + "/"},
                    }

            # 兜底：丢给嗅探
            print(f"[播放] ✗ 未提取到直链，交给嗅探")
            return {"parse": 1, "url": url, "header": {"Referer": self.host + "/"}}
        except Exception as e:
            print(f"[play] {e}")
            return {"parse": 1, "url": id, "header": {}}

    # ============================================================
    #  搜索
    # ============================================================
    def searchContent(self, key, quick, pg="1"):
        try:
            url = f"{self.host}/search.php?searchword={quote(key)}"
            r = self._get(url)
            if not r:
                return {"list": [], "page": 1, "pagecount": 1}
            videos = self._parse_list(r.text)
            return {"list": videos, "page": int(pg), "pagecount": 1}
        except Exception as e:
            print(f"[search] {e}")
            return {"list": [], "page": 1, "pagecount": 1}

    def homeVideoContent(self):
        r = self._get(f"{self.host}/list/1.html")
        return {"list": self._parse_list(r.text) if r else []}


# ============================================================
#  TVBox 入口
# ============================================================
def get_spider():
    return Spider()