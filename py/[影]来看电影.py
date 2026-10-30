# -*- coding: utf-8 -*-
"""
来看电影 (lkdy.tv / www.lkdy.tv) Python Spider
兼容 FongMi/TV (T3) 与 WebHomeTV/PeekPro (T4)
站点：纯 API 驱动 (ysapi.uczyw.us/api)
播放解析：jiexi.zhblyjpj.com + RC4 解密
海报：观潮海报网 (haibaowang.top)
"""
import sys
import re
import json
import time
import base64
from urllib.parse import quote, unquote, urljoin

sys.path.append('..')

# ===== 兼容导入 =====
try:
    from base.spider import Spider
except ImportError:
    import requests as rq

    class Spider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            kw.setdefault('verify', False)
            r = rq.get(url, headers=headers, timeout=30, **kw)
            r.encoding = 'utf-8'
            return r

try:
    import requests as _rq
except ImportError:
    _rq = None

API_BASE = "https://ysapi.uczyw.us/api"
SITE_HOST = "https://www.lkdy.tv"
IMG_PROXY = "https://apiimg.uczyw.us"
# 海报网 API（观潮海报网）
HAIBAO_API = "https://www.haibaowang.top/api/api.php"
# jiexi.zhblyjpj.com 解析站（抓包实测）
JIEXI_HOST = "https://jiexi.zhblyjpj.com"
# RC4 密钥（抓包 dmplayer.js 实测）
RC4_KEY = "202305051826239865"
UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
HEADER = {
    "User-Agent": UA,
    "Referer": SITE_HOST + "/",
    "Content-Type": "application/json",
}

# 视频详情缓存
_detail_cache = {}
# 海报缓存（减少请求）
_haibao_cache = {}

# ===== 分类定义（按截图底部导航 + 子分类）=====
CATEGORIES = {
    "首页": [],
    "动漫": [
        {"type_id": "category:1774397922971", "type_name": "动漫"},
        {"type_id": "category:1774397928670", "type_name": "bilibili番剧"},
        {"type_id": "category:1774397976538", "type_name": "bilibili国创"},
        {"type_id": "category:1774397971906", "type_name": "bilibili电影"},
        {"type_id": "category:1774400694603", "type_name": "动画片"},
    ],
    "电影": [
        {"type_id": "category:1774448688271", "type_name": "动作片"},
        {"type_id": "category:1774454056540", "type_name": "喜剧片"},
        {"type_id": "category:1774454211660", "type_name": "爱情片"},
        {"type_id": "category:1774479654646", "type_name": "剧情片"},
        {"type_id": "category:1774454470815", "type_name": "科幻片"},
        {"type_id": "category:1774480076155", "type_name": "犯罪片"},
        {"type_id": "category:1774479897460", "type_name": "战争片"},
        {"type_id": "category:1774486184666", "type_name": "惊悚片"},
        {"type_id": "category:1774489573252", "type_name": "冒险片"},
        {"type_id": "category:1774489659949", "type_name": "悬疑片"},
        {"type_id": "category:1774489751864", "type_name": "奇幻片"},
        {"type_id": "category:1778827023947", "type_name": "其他片"},
    ],
    "电视剧": [
        {"type_id": "category:1774397945672", "type_name": "国产剧"},
        {"type_id": "category:1774397971906", "type_name": "港台剧"},
        {"type_id": "category:1774486101912", "type_name": "日韩剧"},
        {"type_id": "category:1774486015953", "type_name": "欧美剧"},
        {"type_id": "category:1774397935233", "type_name": "bilibili电视剧"},
        {"type_id": "category:1778828160385", "type_name": "其他剧"},
    ],
    "综艺": [
        {"type_id": "category:1774397919420", "type_name": "综艺"},
    ],
}

# 一级分类（底部导航 bar）
TAB_CLASSES = [
    {"type_id": "首页", "type_name": "首页"},
    {"type_id": "动漫", "type_name": "动漫"},
    {"type_id": "电影", "type_name": "电影"},
    {"type_id": "电视剧", "type_name": "电视剧"},
    {"type_id": "综艺", "type_name": "综艺"},
]

# 域名 → 平台名映射（用于线路名识别）
DOMAIN_PLATFORM = {
    "v.qq.com": "腾讯视频", "qq.com": "腾讯视频",
    "www.iqiyi.com": "爱奇艺", "iqiyi.com": "爱奇艺",
    "www.youku.com": "优酷", "youku.com": "优酷",
    "www.bilibili.com": "哔哩哔哩", "bilibili.com": "哔哩哔哩",
    "www.mgtv.com": "芒果TV", "mgtv.com": "芒果TV",
    "tv.sohu.com": "搜狐视频", "sohu.com": "搜狐视频",
    "www.pptv.com": "PPTV", "pptv.com": "PPTV",
    "www.le.com": "乐视", "le.com": "乐视",
    "www.1905.com": "1905电影网", "1905.com": "1905电影网",
}


def _get(url, headers=None, timeout=20):
    """统一 GET 请求，返回 JSON"""
    h = dict(HEADER)
    if headers:
        h.update(headers)
    try:
        if _rq:
            r = _rq.get(url, headers=h, timeout=timeout, verify=False)
            return json.loads(r.text) if r.text else {}
        else:
            r = rq.get(url, headers=h, timeout=timeout, verify=False)
            return json.loads(r.text) if r.text else {}
    except Exception:
        return {}


def _get_raw(url, headers=None, timeout=20):
    """统一 GET 请求，返回原始文本"""
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    try:
        if _rq:
            r = _rq.get(url, headers=h, timeout=timeout, verify=False)
            return r.text or ""
        else:
            r = rq.get(url, headers=h, timeout=timeout, verify=False)
            return r.text or ""
    except Exception:
        return ""


def _img_proxy(url, w=300, q=75):
    """站点图片代理"""
    if not url:
        return ""
    return f"{IMG_PROXY}/?url={quote(url, safe='')}&w={w}&q={q}"


def _search_haibao(title):
    """通过观潮海报网搜索海报图片"""
    if not title:
        return ""
    global _haibao_cache
    if title in _haibao_cache:
        return _haibao_cache[title]
    try:
        url = f"{HAIBAO_API}?search={quote(title, safe='')}&limit=1"
        text = _get_raw(url, timeout=10)
        if not text:
            return ""
        data = json.loads(text)
        items = data.get("data") or []
        if items:
            pic_url = items[0].get("url", "")
            if pic_url:
                _haibao_cache[title] = pic_url
                return pic_url
    except Exception:
        pass
    return ""


def _rc4_decrypt(data, key=RC4_KEY):
    """RC4 解密（jiexi.zhblyjpj.com dmplayer.js）"""
    try:
        decoded = base64.b64decode(data)
        pwd = [ord(c) for c in key]
        S = list(range(256))
        j = 0
        for i in range(256):
            j = (j + S[i] + pwd[i % len(pwd)]) % 256
            S[i], S[j] = S[j], S[i]
        i = j = 0
        result = bytearray()
        for byte in decoded:
            i = (i + 1) % 256
            j = (j + S[i]) % 256
            S[i], S[j] = S[j], S[i]
            k = S[(S[i] + S[j]) % 256]
            result.append(byte ^ k)
        return unquote(result.decode('utf-8', 'ignore'))
    except Exception:
        return ""


class Spider(Spider):

    def getName(self):
        return "来看电影"

    def init(self, extend=""):
        if isinstance(extend, list):
            self.extend = ''
        else:
            self.extend = extend or ''
        self.host = SITE_HOST
        self.header = dict(HEADER)
        self._categories = []
        self._cat_time = 0
        self._home_cache = []
        self._home_cache_time = 0
        self._video_data_map = {}

    def _txt(self, url, referer=None, timeout=30):
        """统一文本抓取"""
        headers = dict(self.header)
        if referer:
            headers["Referer"] = referer
        try:
            rsp = self.fetch(url, headers=headers, timeout=timeout)
            try:
                rsp.encoding = "utf-8"
            except Exception:
                pass
            return rsp.text or ""
        except Exception:
            pass
        if _rq:
            try:
                rsp = _rq.get(url, headers=headers, timeout=timeout, verify=False)
                rsp.encoding = "utf-8"
                return rsp.text or ""
            except Exception:
                return ""
        return ""

    @staticmethod
    def _match(pattern, text, group=1, flags=0):
        try:
            m = re.search(pattern, text, flags)
            return m.group(group) if m else ""
        except Exception:
            return ""

    @staticmethod
    def _strip_tags(html):
        text = re.sub(r'<[^>]+>', '', html or '')
        text = text.replace('&nbsp;', ' ').replace('&nbsp', ' ')
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return text.strip()

    # ========== 首页 ==========

    def homeContent(self, filter):
        result = {"class": TAB_CLASSES}
        if filter:
            filters = {}
            for tab_name, subcats in CATEGORIES.items():
                if subcats:
                    filters[tab_name] = [{
                        "key": "subcate",
                        "name": "子分类",
                        "value": [{"n": "全部", "v": ""}] + [
                            {"n": sc["type_name"], "v": sc["type_id"]}
                            for sc in subcats
                        ]
                    }]
            result["filters"] = filters
        return result

    def homeVideoContent(self):
        now = int(time.time())
        if self._home_cache and now - self._home_cache_time < 300:
            return {"list": self._home_cache[:72]}

        data = _get(f"{API_BASE}/videos/recommended")
        items = data if isinstance(data, list) else data.get("list") or data.get("data") or []
        videos = []
        for v in items[:72]:
            vid = v.get("id", "")
            if vid:
                self._video_data_map[vid] = v
            videos.append(self._video_to_vod(v))
        self._home_cache = videos
        self._home_cache_time = now
        return {"list": self._home_cache}

    def _get_cover(self, v):
        """获取封面：优先原始 cover → 海报网搜索 → img_proxy"""
        cover = v.get("cover") or v.get("banner") or ""
        if cover:
            return _img_proxy(cover)
        # 原图无封面，从海报网搜索
        title = v.get("title", "")
        if title:
            haibao_url = _search_haibao(title)
            if haibao_url:
                return haibao_url
        return ""

    @staticmethod
    def _video_to_vod(v):
        """API 视频对象转壳子 vod 格式"""
        cover = v.get("cover") or v.get("banner") or ""
        return {
            "vod_id": v.get("id", ""),
            "vod_name": v.get("title", ""),
            "vod_pic": _img_proxy(cover),
            "vod_remarks": v.get("subTitle", ""),
            "vod_content": v.get("desc", ""),
        }

    # ========== 分类列表 ==========

    def categoryContent(self, tid, pg, filter, extend):
        actual_cat_id = ""

        # 优先检查 extend 中的子分类
        if extend:
            if isinstance(extend, str):
                try:
                    extend = json.loads(extend)
                except Exception:
                    extend = {}
            if isinstance(extend, dict):
                subcate = extend.get("subcate", "")
                if subcate and subcate.startswith("category:"):
                    actual_cat_id = subcate

        if not actual_cat_id:
            if tid.startswith("category:"):
                actual_cat_id = tid
            elif tid in CATEGORIES:
                subcats = CATEGORIES[tid]
                if subcats:
                    actual_cat_id = subcats[0]["type_id"]
                else:
                    return self._home_category_fallback(pg)

        if not actual_cat_id:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}

        url = f"{API_BASE}/videos?category={quote(actual_cat_id, safe='')}&page={pg}&pageSize=20"
        data = _get(url)
        items = data.get("list") or []
        total = data.get("total") or 0
        page = data.get("page") or pg
        page_size = data.get("pageSize") or 20
        pagecount = (total + page_size - 1) // page_size if total and page_size else 1

        videos = []
        seen = set()
        for v in items:
            vid = v.get("id", "")
            if vid and vid not in seen:
                seen.add(vid)
                self._video_data_map[vid] = v
                videos.append(self._video_to_vod(v))

        return {
            "list": videos,
            "page": str(page),
            "pagecount": pagecount,
            "limit": page_size,
            "total": total,
        }

    def _home_category_fallback(self, pg):
        if pg == "1":
            data = _get(f"{API_BASE}/videos/recommended")
            items = data if isinstance(data, list) else data.get("list") or []
            videos = []
            for v in items[:20]:
                vid = v.get("id", "")
                if vid:
                    self._video_data_map[vid] = v
                videos.append(self._video_to_vod(v))
            return {"list": videos, "page": "1", "pagecount": 1, "limit": 20, "total": len(videos)}
        return {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}

    # ========== 详情页 ==========

    def detailContent(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        vod_id = ids[0]

        if vod_id in _detail_cache:
            return {"list": [_detail_cache[vod_id]]}

        video_data = self._find_video(vod_id)
        if not video_data:
            return {"list": [{"vod_id": vod_id, "vod_name": "未知", "vod_play_from": "", "vod_play_url": ""}]}

        vod = self._video_to_vod(video_data)
        vod["vod_id"] = vod_id
        vod["vod_year"] = ""
        vod["vod_area"] = ""
        vod["vod_actor"] = ""
        vod["vod_director"] = video_data.get("director", "")
        vod["type_name"] = video_data.get("category", "")
        vod["vod_content"] = self._strip_tags(video_data.get("desc", ""))

        # 封面：优先原始 → 海报网
        cover = video_data.get("cover") or video_data.get("banner") or ""
        if cover:
            vod["vod_pic"] = _img_proxy(cover)
        else:
            haibao_url = _search_haibao(video_data.get("title", ""))
            vod["vod_pic"] = haibao_url or ""

        # 从 tags 提取年份和地区
        tags = video_data.get("tags") or []
        for tag in tags:
            name = tag.get("name", "")
            if not name:
                continue
            if re.match(r'^20\d{2}$', name) and not vod["vod_year"]:
                vod["vod_year"] = name
            elif not vod["vod_area"]:
                vod["vod_area"] = name

        # 提取演员
        actors = video_data.get("actors")
        if isinstance(actors, list):
            vod["vod_actor"] = ", ".join(str(a) for a in actors)
        elif isinstance(actors, str):
            try:
                parsed = json.loads(actors)
                if isinstance(parsed, list):
                    vod["vod_actor"] = ", ".join(str(a) for a in parsed)
                else:
                    vod["vod_actor"] = actors
            except Exception:
                vod["vod_actor"] = actors

        # ===== 构建播放列表 =====
        # 关键修复：一个 source 就是一条线路，不按域名拆分
        # API 返回的 source 里的 urls 可能包含不同平台的链接
        # 但每个 source 是一条完整的线路，用户选择线路后能看到所有集数
        sources = video_data.get("sources") or []
        play_from_parts = []
        play_url_parts = []

        source_name_map = {
            "qq": "腾讯视频", "youku": "优酷", "iqiyi": "爱奇艺",
            "bilibili": "哔哩哔哩", "mgtv": "芒果TV", "sohu": "搜狐视频",
            "pptv": "PPTV", "le": "乐视", "1905": "1905电影网",
        }

        for src in sources:
            source_name = src.get("source", "默认线路")
            urls = src.get("urls") or []
            if not urls:
                continue

            # 用 source 标识作为线路名
            display_name = source_name_map.get(source_name, source_name)

            ep_list = []
            for ep in urls:
                ep_url = ep.get("url", "")
                label = ep.get("label", "")
                if not ep_url:
                    continue
                ep_list.append(f"{label}${ep_url}")

            if ep_list:
                play_from_parts.append(display_name)
                play_url_parts.append("#".join(ep_list))

        if not play_from_parts:
            play_from_parts.append("默认线路")
            play_url_parts.append("暂无资源")

        vod["vod_play_from"] = "$$$".join(play_from_parts)
        vod["vod_play_url"] = "$$$".join(play_url_parts)

        _detail_cache[vod_id] = vod
        return {"list": [vod]}

    def _find_video(self, vod_id):
        """从缓存或 API 查找视频原始数据（含 sources）"""
        if vod_id in self._video_data_map:
            v = self._video_data_map[vod_id]
            if v.get("sources"):
                return v

        data = _get(f"{API_BASE}/videos/recommended")
        items = data if isinstance(data, list) else []
        for v in items:
            vid = v.get("id", "")
            if vid:
                self._video_data_map[vid] = v
            if vid == vod_id and v.get("sources"):
                return v

        try:
            search_data = _get(f"{API_BASE}/videos/{quote(vod_id, safe='')}")
            if search_data and search_data.get("sources"):
                self._video_data_map[vod_id] = search_data
                return search_data
        except Exception:
            pass

        return None

    # ========== 搜索 ==========

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg)
        except Exception:
            page = 1

        url = f"{API_BASE}/videos?search={quote(key, safe='')}&page={page}&pageSize=20"
        data = _get(url)
        items = data.get("list") or []

        videos = []
        seen = set()
        for v in items:
            vid = v.get("id", "")
            if vid and vid not in seen:
                seen.add(vid)
                self._video_data_map[vid] = v
                videos.append(self._video_to_vod(v))

        return {"list": videos}

    # ========== 播放解析（核心）==========

    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {"parse": 1, "playUrl": "", "url": ""}

        url = id
        if not url.startswith("http"):
            return {"parse": 1, "playUrl": "", "url": ""}

        # 1. 直链检测
        if self._is_direct_media(url):
            fmt = "application/x-mpegURL" if ".m3u8" in url.lower() else ""
            return {
                "parse": 0, "playUrl": "", "url": url,
                "header": {"User-Agent": UA},
                "format": fmt,
            }

        # 2. jiexi.zhblyjpj.com 解析（主解析方式）
        resolved = self._resolve_jiexi(url)
        if resolved:
            fmt = "application/x-mpegURL" if ".m3u8" in resolved.lower() else ""
            return {
                "parse": 0, "playUrl": "", "url": resolved,
                "header": {"User-Agent": UA, "Referer": JIEXI_HOST + "/"},
                "format": fmt, "contentType": fmt,
            }

        # 3. bfq.txnp.cn 备用解析
        if self._is_official_source(url):
            resolved = self._resolve_bfq(url)
            if resolved:
                fmt = "application/x-mpegURL" if ".m3u8" in resolved.lower() else ""
                return {
                    "parse": 0, "playUrl": "", "url": resolved,
                    "header": {"User-Agent": UA, "Referer": "https://bfq.txnp.cn/"},
                    "format": fmt, "contentType": fmt,
                }

        # 4. 页面解析 fallback
        html = self._txt(url, referer=self.host + "/", timeout=30)
        real = ""

        m = re.search(r'player_aaaa\s*=\s*(\{.*?\})\s*</script>', html, re.S)
        if not m:
            m = re.search(r'player_aaaa\s*=\s*(\{.*?\})\s*[,;]', html, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                real = data.get("url", "") or ""
                encrypt = data.get("encrypt", 0)
                if encrypt in [1, 2] and real:
                    try:
                        real = base64.b64decode(real).decode("utf-8")
                    except Exception:
                        pass
            except Exception:
                real = self._match(r'"url"\s*:\s*"([^"]+)"', m.group(1))

        if real:
            real = real.replace("\\/", "/")
            if ".m3u8" in real.lower():
                real = self._resolve_m3u8_child(real, referer=url)
            fmt = "application/x-mpegURL" if ".m3u8" in real.lower() else ""
            return {
                "parse": 0, "playUrl": "", "url": real,
                "header": {"User-Agent": UA, "Referer": url},
                "format": fmt, "contentType": fmt,
            }

        # 5. 兜底交给壳子嗅探（壳子会尝试 WebView 内嗅探 m3u8/mp4）
        return {"parse": 1, "playUrl": "", "url": url}

    # ========== jiexi.zhblyjpj.com 解析（主解析方式）==========

    def _resolve_jiexi(self, src_url):
        """
        使用 jiexi.zhblyjpj.com 解析站解析视频地址
        流程: analysis.php?v=<src> → 取 config.url → RC4 解密 → m3u8
        """
        try:
            analysis_url = f"{JIEXI_HOST}/player/analysis.php?v={quote(src_url, safe='')}"
            referer = f"{JIEXI_HOST}/player/?url={quote(src_url, safe='')}"
            html = self._txt(analysis_url, referer=referer, timeout=30)

            if not html:
                return ""

            # 如果返回解析失败页面，直接返回空
            if "解析失败" in html:
                return ""

            # 提取 var config = {...} 中的 url 字段
            config_url = self._match(r'"url"\s*:\s*"([^"]{20,})"', html)
            if not config_url:
                return ""

            # RC4 解密得到真实播放地址
            real_url = _rc4_decrypt(config_url)
            if not real_url or not real_url.startswith("http"):
                return ""

            if ".m3u8" in real_url.lower():
                real_url = self._resolve_m3u8_child(real_url, referer=analysis_url)

            return real_url
        except Exception:
            return ""

    # ========== bfq.txnp.cn 备用解析 ==========

    @staticmethod
    def _is_official_source(url):
        url = (url or "").lower()
        keys = (
            "mgtv.com", "youku.com", "iqiyi.com", "qiyi.com",
            "v.qq.com", "qq.com", "bilibili.com", "le.com",
            "sohu.com", "pptv.com", "1905.com",
        )
        return any(k in url for k in keys)

    @staticmethod
    def _is_direct_media(url):
        url = (url or "").lower()
        return ".m3u8" in url or ".mp4" in url or ".flv" in url or ".mkv" in url

    def _aes_cbc_decrypt_text(self, cipher_text):
        try:
            from Crypto.Cipher import AES
            key = cipher_text[-32:-16].encode("utf-8")
            iv = cipher_text[-16:].encode("utf-8")
            data = base64.b64decode(cipher_text[:-32])
            raw = AES.new(key, AES.MODE_CBC, iv).decrypt(data)
            pad = raw[-1] if raw else 0
            if 0 < pad <= 16:
                raw = raw[:-pad]
            return raw.decode("utf-8", "ignore")
        except Exception:
            return ""

    def _resolve_bfq(self, src_url):
        """bfq.txnp.cn 备用解析"""
        if not src_url or not self._is_official_source(src_url):
            return ""
        try:
            page_url = "https://bfq.txnp.cn/player?url=" + quote(src_url, safe="")
            referer = "https://bfq.txnp.cn/excessive?url=" + quote(src_url, safe="")
            html = self._txt(page_url, referer=referer, timeout=20)
            result = self._match(r'let\s+result\s*=\s*"([^"]+)"', html, re.S)
            if not result:
                return ""
            text = self._aes_cbc_decrypt_text(result)
            if not text:
                return ""
            try:
                data = json.loads(text)
            except Exception:
                return ""
            video = ((data.get("video_info") or {}).get("video") or {})
            media = (video.get("url") or "").replace("\\/", "/")
            if media and self._is_direct_media(media):
                if ".m3u8" in media.lower():
                    media = self._resolve_m3u8_child(media, referer=page_url)
                return media
        except Exception:
            pass
        return ""

    # ========== M3U8 兼容 ==========

    def _resolve_m3u8_child(self, m3u8_url, referer=""):
        """Exo 兼容：解析主 m3u8 到子 m3u8"""
        text = self._txt(m3u8_url, referer=referer or self.host + "/", timeout=20)
        if not text or "#EXTM3U" not in text:
            return m3u8_url
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF"):
                for nxt in lines[i + 1:]:
                    if nxt and not nxt.startswith("#"):
                        return urljoin(m3u8_url, nxt)
        return m3u8_url

    # ========== 本地代理 ==========

    def _proxy_url(self, media_url, referer=""):
        if not hasattr(self, "getProxyUrl"):
            return media_url
        try:
            base = self.getProxyUrl()
            return base + "&url=" + quote(media_url, safe="") + \
                   "&referer=" + quote(referer or self.host + "/", safe="")
        except Exception:
            return media_url

    def localProxy(self, param):
        raw_url = param.get("url") or param.get("u") or ""
        referer = param.get("referer") or self.host + "/"
        media_url = unquote(raw_url)
        headers = {
            "User-Agent": UA,
            "Referer": unquote(referer),
        }
        if not _rq:
            return [200, "video/MP2T", b"", ""]
        try:
            r = _rq.get(media_url, headers=headers, timeout=30, verify=False)
            text = r.content.decode("utf-8", errors="ignore")
            if "#EXTM3U" in text:
                out = []
                for line in text.splitlines():
                    s = line.strip()
                    if not s or s.startswith("#"):
                        out.append(line)
                    else:
                        abs_url = urljoin(media_url, s)
                        out.append(self._proxy_url(abs_url, referer))
                return [200, "application/x-mpegURL", "\n".join(out).encode("utf-8")]
            return [200, r.headers.get("content-type") or "application/octet-stream", r.content]
        except Exception:
            return [200, "video/MP2T", b"", ""]

    def destroy(self):
        pass

    def close(self):
        self.destroy()
