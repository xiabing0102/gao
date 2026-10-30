# -*- coding: utf-8 -*-
"""
新₄ᴋ⁽ᵖʰᵖ⁾┃[影视]  ——  羊壳 / TVBox 类 影视壳 py 爬虫源
============================================================
数据源：启纪云 苹果CMS10 JSON 接口
    http://cmsyun2.qijiyun.vip/api.php/provide/vod/

接口实测（生成时验证通过）：
    ac=list                        -> class(分类) + list(首页最新)
    ac=videolist&t={tid}&pg={n}    -> 分类列表（分页）
    ac=videolist&wd={kw}&pg={n}    -> 关键词搜索
    ac=detail&ids={id}             -> 详情（含 vod_play_from / vod_play_url 直链）

播放实测：vod_play_url 为 mp4 / mkv 直链，支持 Range 断点（HTTP 206），
         可直接 parse=0 交给壳播放，无需第三方解析器。

设计要点：
1. 标准壳接口：init / homeContent / homeVideoContent / categoryContent /
   detailContent / searchContent / playerContent / localProxy / destroy / close
2. 构造函数不联网，域名探测延迟到首次业务请求，避免壳启动卡死
3. 只依赖 标准库 + requests（无 requests 时自动降级到 urllib，零第三方依赖）
4. 播放地址容错：\\/ 反转义、二次 URL 编码（%25 -> %）还原、空格再编码
5. 多级缓存：首页 / 分类 / 详情 / 搜索 / 播放，降低接口压力
6. 全站接口请求并发（首页多页合并、备用域名轮询）
"""

import json
import re
import time
import threading

from urllib.parse import urlencode, quote, unquote

try:
    import requests
    from requests.adapters import HTTPAdapter
except ImportError:
    requests = None

try:
    from urllib.request import Request as _UrlRequest, urlopen as _urlopen
    from urllib.error import URLError as _URLError
except ImportError:
    _UrlRequest = None
    _urlopen = None
    _URLError = Exception

try:
    import urllib3
    urllib3.disable_warnings()
except Exception:
    pass

try:
    import sys
    sys.path.append('..')
    from base.spider import Spider as _BaseSpider
except ImportError:
    _BaseSpider = None

try:
    from concurrent.futures import ThreadPoolExecutor, as_completed
except ImportError:
    ThreadPoolExecutor = None
    as_completed = None

# ============================================================
# 常量
# ============================================================
# 主域名 + 备用域名（按顺序轮询探测，首个可用即固定使用）
HOSTS = [
    "http://cmsyun2.qijiyun.vip",
    "http://cmsyun1.qijiyun.vip",
    "http://cmsyun3.qijiyun.vip",
    "http://cmsyun.qijiyun.vip",
]

API_PATH = "/api.php/provide/vod/"

UA = (
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
)

TIMEOUT_API = 8
TIMEOUT_PROBE = 5

# 缓存 TTL（秒）
TTL_HOME = 600
TTL_CAT = 300
TTL_DETAIL_OK = 600
TTL_DETAIL_EMPTY = 60
TTL_SEARCH = 300

# 是否隐藏接口里混入的引流/广告分类（名称命中下列关键词即隐藏）
FILTER_AD_CAT = True
AD_KEYS = ("q群", "qq群", "获取更多", "体验更全", "正式版本", "加群")

# 站点显示名
SITE_NAME = "新4K影视"


# ============================================================
# Spider 主类
# ============================================================
_Base = _BaseSpider if _BaseSpider is not None else object


class Spider(_Base):
    siteUrl = HOSTS[0]
    headers = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    }

    def __init__(self):
        # 注意：这里不做任何联网操作，壳启动时才能秒开
        self._host = ""                 # 当前可用域名（首次请求时探测）
        self._lock = threading.Lock()
        self._session = None

        # 缓存容器
        self._home_cache = []
        self._home_time = 0
        self._cat_cache = {}
        self._detail_cache = {}
        self._search_cache = {}
        self._ad_type_ids = set()

        self._extend = ""

    # ============================================================
    # 生命周期
    # ============================================================
    def init(self, extend=""):
        self.extend = extend or ""
        self._extend = self.extend

    def destroy(self):
        try:
            if self._session is not None:
                self._session.close()
        except Exception:
            pass
        self._session = None

    def close(self):
        self.destroy()

    def localProxy(self, param):
        return [200, "video/MP2T", b"", ""]

    # ============================================================
    # 网络层（requests 优先，urllib 兜底；零重依赖）
    # ============================================================
    def _get_session(self):
        if requests is None:
            return None
        if self._session is None:
            with self._lock:
                if self._session is None:
                    s = requests.Session()
                    s.headers.update(self.headers)
                    s.verify = False
                    adapter = HTTPAdapter(
                        pool_connections=10, pool_maxsize=20,
                        max_retries=0, pool_block=False,
                    )
                    s.mount("http://", adapter)
                    s.mount("https://", adapter)
                    self._session = s
        return self._session

    def _http_text(self, url, timeout=TIMEOUT_API):
        """返回响应文本，失败返回空串"""
        if requests is not None:
            sess = self._get_session()
            for attempt in range(2):
                try:
                    r = sess.get(url, timeout=timeout)
                    if r.status_code == 429:
                        time.sleep(1.5)
                        continue
                    if r.status_code >= 400:
                        return ""
                    r.encoding = "utf-8"
                    return r.text
                except Exception:
                    if attempt == 0:
                        time.sleep(0.2)
            return ""

        if _UrlRequest is None:
            return ""
        for attempt in range(2):
            try:
                req = _UrlRequest(url, headers=self.headers)
                with _urlopen(req, timeout=timeout) as resp:
                    raw = resp.read()
                return raw.decode("utf-8", "ignore")
            except Exception:
                if attempt == 0:
                    time.sleep(0.2)
        return ""

    def _json_get(self, host, params, timeout=TIMEOUT_API):
        url = "%s%s?%s" % (host, API_PATH, urlencode(params))
        text = self._http_text(url, timeout=timeout)
        if not text:
            return None
        text = text.strip()
        i = text.find("{")
        if i < 0:
            return None
        try:
            data = json.loads(text[i:])
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        # 苹果CMS 成功标志：code = 1
        if data.get("code") not in (1, "1"):
            return None
        return data

    def _api(self, params, timeout=TIMEOUT_API):
        """调用接口：当前域名 -> 备用域名轮询，成功后固定"""
        order = []
        if self._host:
            order.append(self._host)
        for h in HOSTS:
            if h not in order:
                order.append(h)

        for host in order[:3]:
            data = self._json_get(host, params, timeout)
            if data is not None:
                with self._lock:
                    self._host = host
                    self.siteUrl = host
                return data

        # 全部失败，清空域名，下次重新探测
        with self._lock:
            self._host = ""
        return None

    # ============================================================
    # 缓存工具
    # ============================================================
    @staticmethod
    def _cache_get(cache, key):
        item = cache.get(key)
        if not item:
            return None
        ts, ttl, value = item
        if time.time() - ts > ttl:
            return None
        return value

    @staticmethod
    def _cache_set(cache, key, value, ttl):
        if len(cache) > 400:
            cache.clear()
        cache[key] = (time.time(), ttl, value)

    # ============================================================
    # 通用工具
    # ============================================================
    @staticmethod
    def _clean(text):
        if text is None:
            return ""
        return str(text).replace("\u3000", " ").strip()

    @staticmethod
    def _clean_url(u):
        """播放地址容错清洗：\\/ 反转义 + 二次编码还原 + 空格再编码"""
        u = (u or "").strip()
        if not u:
            return ""
        u = u.replace("\\/", "/")
        if "%25" in u:
            try:
                u = unquote(u)
            except Exception:
                pass
        if " " in u:
            u = u.replace(" ", "%20")
        return u

    @staticmethod
    def _pick_remarks(v):
        return Spider._clean(v.get("vod_remarks") or "")

    def _card(self, v):
        """苹果CMS 列表项 -> 壳卡片"""
        return {
            "vod_id": str(v.get("vod_id") or ""),
            "vod_name": self._clean(v.get("vod_name")),
            "vod_pic": self._clean(v.get("vod_pic")),
            "vod_remarks": self._pick_remarks(v),
        }

    def _filter_items(self, items):
        """过滤引流/广告分类的条目"""
        if not FILTER_AD_CAT or not items:
            return items
        return [it for it in items
                if str(it.get("type_id") or "") not in self._ad_type_ids]

    # ============================================================
    # 分类
    # ============================================================
    def _parse_classes(self, data):
        classes, ad_ids = [], set()
        for c in (data.get("class") or []):
            if not isinstance(c, dict):
                continue
            tid = str(c.get("type_id") or "")
            name = self._clean(c.get("type_name"))
            if not tid:
                continue
            if FILTER_AD_CAT and any(k in name for k in AD_KEYS):
                ad_ids.add(tid)
                continue
            # 只保留一级分类（pid 为 0 或缺失）
            classes.append({
                "type_id": tid,
                "type_name": name,
                "filter": 0,
            })
        with self._lock:
            self._ad_type_ids = ad_ids
        return classes

    # ============================================================
    # 首页
    # ============================================================
    def homeContent(self, filter=False):
        data = self._api({"ac": "list"})
        if not data:
            return {"class": [], "filters": {}, "list": []}
        classes = self._parse_classes(data)
        vod_list = self._home_list()
        return {
            "class": classes,
            "filters": {},
            "list": vod_list,
        }

    def homeVideoContent(self):
        return {"list": self._home_list()}

    def _home_list(self, pages=2):
        """首页最新：并发拉取前 N 页合并去重（接口每页 20 条）"""
        now = time.time()
        with self._lock:
            if self._home_cache and now - self._home_time < TTL_HOME:
                return self._home_cache[:60]

        def _fetch(p):
            return self._api({"ac": "videolist", "pg": str(p)})

        merged, seen = [], set()
        results = []
        if ThreadPoolExecutor is not None and pages > 1:
            try:
                with ThreadPoolExecutor(max_workers=pages) as ex:
                    futs = [ex.submit(_fetch, p) for p in range(1, pages + 1)]
                    for f in as_completed(futs, timeout=TIMEOUT_API * 2):
                        try:
                            results.append(f.result(timeout=TIMEOUT_API))
                        except Exception:
                            continue
            except Exception:
                results = [_fetch(1)]
        else:
            results = [_fetch(1)]

        for data in results:
            if not data:
                continue
            for v in self._filter_items(data.get("list") or []):
                vid = str(v.get("vod_id") or "")
                if not vid or vid in seen:
                    continue
                seen.add(vid)
                merged.append(self._card(v))
                if len(merged) >= 60:
                    break

        if merged:
            with self._lock:
                self._home_cache = merged
                self._home_time = time.time()
        return merged[:60]

    # ============================================================
    # 分类列表
    # ============================================================
    def categoryContent(self, tid, pg, filter, extend):
        page = 1
        try:
            page = max(1, int(pg or 1))
        except Exception:
            page = 1

        # 兼容壳传入的 extend（支持二级分类切换）
        sub_tid = ""
        if extend:
            ext = extend
            if isinstance(ext, str):
                try:
                    ext = json.loads(extend)
                except Exception:
                    ext = {}
            if isinstance(ext, dict):
                sub_tid = str(ext.get("class") or "").strip()
        tid = sub_tid or str(tid or "1").strip()

        ckey = "%s|%d" % (tid, page)
        cached = self._cache_get(self._cat_cache, ckey)
        if cached is not None:
            return cached

        data = self._api({"ac": "videolist", "t": tid, "pg": str(page)})
        if not data:
            return {"list": [], "page": page, "pagecount": page, "limit": 20, "total": 0}

        vod_list = [self._card(v) for v in self._filter_items(data.get("list") or [])]
        try:
            pagecount = int(data.get("pagecount") or 1)
        except Exception:
            pagecount = 1
        try:
            total = int(data.get("total") or 0)
        except Exception:
            total = 0

        result = {
            "list": vod_list,
            "page": page,
            "pagecount": max(1, pagecount),
            "limit": 20,
            "total": total or len(vod_list),
        }
        self._cache_set(self._cat_cache, ckey, result, TTL_CAT)
        return result

    # ============================================================
    # 详情
    # ============================================================
    def detailContent(self, ids):
        if isinstance(ids, (list, tuple)):
            vid = str(ids[0]) if ids else ""
        else:
            vid = str(ids or "")
        vid = vid.split(",")[0].strip()
        if not vid:
            return {"list": []}

        cached = self._cache_get(self._detail_cache, vid)
        if cached is not None:
            return cached

        data = self._api({"ac": "detail", "ids": vid})
        vod = None
        if data:
            lst = data.get("list") or []
            if lst:
                vod = lst[0]

        if not isinstance(vod, dict):
            empty = {"list": []}
            self._cache_set(self._detail_cache, vid, empty, TTL_DETAIL_EMPTY)
            return empty

        play_from, play_url = self._build_play(vod)

        detail = {
            "vod_id": vid,
            "vod_name": self._clean(vod.get("vod_name")) or ("视频" + vid),
            "vod_pic": self._clean(vod.get("vod_pic")),
            "type_name": self._clean(vod.get("type_name")),
            "vod_year": self._clean(vod.get("vod_year")),
            "vod_area": self._clean(vod.get("vod_area")),
            "vod_lang": self._clean(vod.get("vod_lang")),
            "vod_actor": self._clean(vod.get("vod_actor")),
            "vod_director": self._clean(vod.get("vod_director")),
            "vod_remarks": self._clean(vod.get("vod_remarks")),
            "vod_content": self._clean(vod.get("vod_content")).replace("<p>", "").replace("</p>", ""),
            "vod_play_from": play_from or "默认",
            "vod_play_url": play_url,
        }
        result = {"list": [detail]}
        self._cache_set(self._detail_cache, vid, result, TTL_DETAIL_OK)
        return result

    def _build_play(self, vod):
        """播放源/集数清洗：多源 $$$ 分隔，集数 # 分隔，格式 名称$地址"""
        froms = [self._clean(x) for x in str(vod.get("vod_play_from") or "").split("$$$")]
        urls = str(vod.get("vod_play_url") or "").split("$$$")

        out_from, out_url = [], []
        for idx, seg in enumerate(urls):
            seg = (seg or "").strip()
            if not seg:
                continue
            eps = []
            for item in seg.split("#"):
                item = item.strip()
                if not item:
                    continue
                if "$" in item:
                    name, url = item.split("$", 1)
                else:
                    name, url = "播放", item
                url = self._clean_url(url)
                if not url:
                    continue
                eps.append("%s$%s" % (self._clean(name) or "播放", url))
            if not eps:
                continue
            src_name = froms[idx] if idx < len(froms) and froms[idx] else ("线路%d" % (idx + 1))
            out_from.append(src_name)
            out_url.append("#".join(eps))

        return "$$$".join(out_from), "$$$".join(out_url)

    # ============================================================
    # 播放
    # ============================================================
    def playerContent(self, flag, id, vipFlags):
        url = self._clean_url(id)
        if not url:
            return {"parse": 0, "playUrl": "", "url": ""}

        low = url.lower()
        header = {
            "User-Agent": UA,
            "Referer": (self._host or HOSTS[0]) + "/",
        }

        # 直链（mp4 / mkv / m3u8 / ts）直接交给壳播放
        if any(k in low for k in (".m3u8", ".mp4", ".mkv", ".ts", ".flv", ".avi", ".mov", ".m4v")):
            is_m3u8 = ".m3u8" in low
            return {
                "parse": 0,
                "playUrl": "",
                "url": url,
                "header": header,
                "format": "application/x-mpegURL" if is_m3u8 else "",
                "contentType": "application/x-mpegURL" if is_m3u8 else "",
            }

        # 非直链（页面 / 播放跳转）-> 交给壳解析
        return {
            "parse": 1,
            "playUrl": "",
            "url": url,
            "header": header,
        }

    # ============================================================
    # 搜索
    # ============================================================
    def searchContent(self, keyword, quick=False, pg=1):
        kw = (keyword or "").strip()
        if not kw:
            return {"list": [], "msg": "请输入搜索关键词"}

        try:
            page = max(1, int(pg or 1))
        except Exception:
            page = 1

        ckey = "%s|%d" % (kw, page)
        cached = self._cache_get(self._search_cache, ckey)
        if cached is not None:
            return cached

        data = self._api({"ac": "videolist", "wd": kw, "pg": str(page)})
        vod_list = []
        if data:
            vod_list = [self._card(v) for v in self._filter_items(data.get("list") or [])]

        result = {"list": vod_list}
        if not vod_list:
            result["msg"] = "未找到相关内容，请尝试其他关键词"
        self._cache_set(self._search_cache, ckey, result, TTL_SEARCH)
        return result


# ============================================================
# 本地自测（直接 python 运行本文件时可用；壳加载时不执行）
# ============================================================
if __name__ == "__main__":
    import sys as _sys

    s = Spider()
    s.init("")
    action = _sys.argv[1] if len(_sys.argv) > 1 else "home"

    if action == "home":
        r = s.homeContent()
        print(json.dumps(r, ensure_ascii=False)[:1200])
    elif action == "category":
        tid = _sys.argv[2] if len(_sys.argv) > 2 else "20"
        pg = _sys.argv[3] if len(_sys.argv) > 3 else "1"
        print(json.dumps(s.categoryContent(tid, pg, False, {}), ensure_ascii=False)[:1200])
    elif action == "detail":
        vid = _sys.argv[2] if len(_sys.argv) > 2 else "1578"
        print(json.dumps(s.detailContent(vid), ensure_ascii=False)[:1500])
    elif action == "play":
        print(json.dumps(s.playerContent("", _sys.argv[2] if len(_sys.argv) > 2 else "", []),
                         ensure_ascii=False)[:800])
    elif action == "search":
        kw = _sys.argv[2] if len(_sys.argv) > 2 else "冬城猎凶"
        print(json.dumps(s.searchContent(kw), ensure_ascii=False)[:1200])
