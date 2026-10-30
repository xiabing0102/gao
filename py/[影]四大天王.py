# -*- coding: utf-8 -*-
"""
四大官源 · 采集之王 整合播放源
首页 / 分类 / 搜索 = 四大官源（腾爱优芒：腾讯/爱奇艺/优酷/芒果TV/B站）
点选视频进详情时，保留官源原始线路（走解析），并追加采集之王聚合线路
播放逻辑完全沿用原始四大官源：m3u8/mp4 直连，其余 jx=1 走解析
"""
import re
import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout

try:
    import requests as _requests
    _HAS_REQUESTS = True
except Exception:
    _requests = None
    _HAS_REQUESTS = False

try:
    from base.spider import Spider as _BaseSpider
except Exception:
    class _BaseSpider:
        pass


def _log(*args):
    try:
        print("腾爱优芒聚合", *args)
    except Exception:
        pass


def _enc(value):
    return urllib.parse.quote(str(value), safe="!'()*-._~")


_CATEGORY = {
    "1": ("qq", "腾讯视频"),
    "2": ("qiyi", "爱奇艺"),
    "3": ("youku", "优酷视频"),
    "4": ("mgtv", "芒果TV"),
    "5": ("bilibili", "B站"),
}
_KEY_TO_NUM = {v[0]: k for k, v in _CATEGORY.items()}

# 采集之王 34 路源（仅用于详情聚合播放线路）
SOURCES = [
    {"key": "iqiyi", "name": "奇艺资源", "api": "https://iqiyizyapi.com/api.php/provide/vod"},
    {"key": "hdzyk", "name": "优质资源", "api": "https://api.yyzy-tv.vip/inc/apijson.php?ac=list"},
    {"key": "dyttzy", "name": "天堂资源", "api": "https://caiji.dyttzyapi.com/api.php/provide/vod"},
    {"key": "lzi", "name": "量子资源", "api": "https://cj.lziapi.com/api.php/provide/vod"},
    {"key": "ruyi", "name": "如意资源", "api": "https://cj.rycjapi.com/api.php/provide/vod"},
    {"key": "bfzy", "name": "暴风资源", "api": "https://bfzyapi.com/api.php/provide/vod"},
    {"key": "ffzy", "name": "非凡资源", "api": "https://ffzy5.tv/api.php/provide/vod"},
    {"key": "zy360", "name": "360资源", "api": "https://360zy.com/api.php/provide/vod"},
    {"key": "jisu", "name": "极速资源", "api": "https://jszyapi.com/api.php/provide/vod"},
    {"key": "zuid", "name": "最大资源", "api": "https://api.zuidapi.com/api.php/provide/vod"},
    {"key": "ty", "name": "天涯资源", "api": "https://tyyszyapi.com/api.php/provide/vod"},
    {"key": "hhzy", "name": "火狐资源", "api": "https://hhzyapi.com/api.php/provide/vod"},
    {"key": "myzy", "name": "猫眼资源", "api": "https://api.maoyanapi.top/api.php/provide/vod"},
    {"key": "hnzy", "name": "红牛资源", "api": "https://www.hongniuzy2.com/api.php/provide/vod"},
    {"key": "hyzy", "name": "虎牙资源", "api": "https://www.huyaapi.com/api.php/provide/vod"},
    {"key": "uku", "name": "优酷资源", "api": "https://api.ukuapi88.com/api.php/provide/vod"},
    {"key": "guangsu", "name": "光速资源", "api": "https://api.guangsuapi.com/api.php/provide/vod"},
    {"key": "xinlang", "name": "新浪资源", "api": "https://api.xinlangapi.com/xinlangapi.php/provide/vod"},
    {"key": "yhzy", "name": "樱花资源", "api": "https://m3u8.apiyhzy.com/api.php/provide/vod"},
    {"key": "nnzy", "name": "牛牛资源", "api": "https://api.niuniuzy.me/api.php/provide/vod"},
    {"key": "baiduyun", "name": "百度资源", "api": "https://api.apibdzy.com/api.php/provide/vod"},
    {"key": "subo", "name": "速播资源", "api": "https://subocaiji.com/api.php/provide/vod"},
    {"key": "jinying", "name": "金鹰资源", "api": "https://jinyingzy.com/api.php/provide/vod"},
    {"key": "piaoling", "name": "飘零资源", "api": "https://p2100.net/api.php/provide/vod"},
    {"key": "modu", "name": "魔都资源", "api": "https://www.mdzyapi.com/api.php/provide/vod"},
    {"key": "xgzy", "name": "西瓜资源", "api": "https://caiji.xgzyapi.com/api.php/provide/vod"},
    {"key": "dzzy", "name": "大众资源", "api": "https://cdn.dzzyapi.com/api.php/provide/vod"},
    {"key": "wsyzy", "name": "无水印资源", "api": "https://api.wsyzy.net/api.php/provide/vod"},
    {"key": "mtzy", "name": "茅台资源", "api": "https://caiji.maotaizy.cc/api.php/provide/vod"},
    {"key": "xsd", "name": "闪电资源", "api": "https://xsd.sdzyapi.com/api.php/provide/vod/"},
    {"key": "sdzy", "name": "速度资源", "api": "https://sdzyapi.com/api.php/provide/vod"},
    {"key": "suoni", "name": "索尼资源", "api": "https://suoniapi.com/api.php/provide/vod"},
    {"key": "dbzy", "name": "豆瓣资源", "api": "https://caiji.dbzy5.com/api.php/provide/vod"},
    {"key": "wujin", "name": "无尽资源", "api": "https://api.wujinapi.cc/api.php/provide/vod"},
]

AGGREGATE_MAX_LINES = 20     # ★ 稍微放宽最大线路数，避免被截断
AGG_SOURCE_TIMEOUT = 5       # ★ 单源超时（秒）
AGG_TOTAL_TIMEOUT = 8        # ★ 聚合整体硬截止（秒）


def _same_name(a, b):
    def norm(s):
        s = re.sub(r"[\s·•：:，,。！？!?（）()【】\[\]]", "", str(s or "")).lower()
        s = re.sub(r"(国语|粤语|日语|英语|韩语|韩语中|中文字|国语版|中文字幕|英语原|原声)", "", s)
        s = re.sub(r"(高清版|超清|蓝光|720p|1080p|4k|HDR|4K)", "", s)
        s = re.sub(r"(完整版|全集|正片|高清)", "", s)
        s = re.sub(r"(第一季|第二季|第三季|第四季|第五季|第六季|第[一二三四五六七八九十]季|季)", "", s)
        s = re.sub(r"(电影|电视剧|剧集|动画|动漫|剧|版|部)", "", s)
        s = re.sub(r"(我的|网飞|Netflix|网飞版|Netflix版|官方)", "", s)
        s = re.sub(r"^第?[一二三四五六七八九十\d]+[章节集]?$", "", s)
        return s
    x, y = norm(a), norm(b)
    if not x or not y:
        return False
    return x in y or y in x


class Spider(_BaseSpider):
    name = "腾爱优芒聚合"

    def init(self, extend=""):
        _log("init ->", extend)
        self.host = "http://cj.tianwe.cn"
        self.header = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/150.0.0.0 Safari/537.36"),
        }
        self.timeout = 10
        if _HAS_REQUESTS:
            self.session = _requests.Session()
            self.session.headers.update(self.header)
        self.by_key = {s["key"]: s for s in SOURCES}
        self.detail_cache = {}

    def getName(self):
        return self.name

    def destroy(self):
        pass

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        pass

    def localProxy(self, param):
        return None

    def _http_get(self, url, timeout=None):
        to = timeout if timeout else getattr(self, "timeout", 15)
        try:
            if _HAS_REQUESTS:
                sess = getattr(self, "session", None) or _requests
                r = sess.get(url, timeout=to, verify=False)
                r.encoding = "utf-8"
                return r.text
            import urllib.request
            req = urllib.request.Request(url, headers=self.header)
            with urllib.request.urlopen(req, timeout=to) as resp:
                data = resp.read()
                try:
                    return data.decode("utf-8")
                except Exception:
                    return data.decode("latin-1")
        except Exception as exc:
            _log("myfetch err ", exc)
            return ""

    def _get_json(self, url):
        try:
            return json.loads(self._http_get(url))
        except Exception:
            return None

    @staticmethod
    def _to_key(tid):
        if tid is None:
            return None
        s = str(tid).strip()
        if s in _CATEGORY:
            return _CATEGORY[s][0]
        if s in _KEY_TO_NUM:
            return s
        return s

    def homeContent(self, filter=False):
        try:
            classes = [
                {"type_id": tid, "type_pid": "0", "type_name": name}
                for tid, (_key, name) in _CATEGORY.items()
            ]
            result = {"class": classes, "list": []}
            if filter:
                type_filter = {
                    "key": "class", "name": "类型",
                    "value": [
                        {"n": "全部", "v": ""}, {"n": "电视剧", "v": "2"},
                        {"n": "电影", "v": "1"}, {"n": "动漫", "v": "4"},
                        {"n": "综艺", "v": "3"}, {"n": "少儿", "v": "5"},
                        {"n": "纪录片", "v": "6"}, {"n": "短剧", "v": "7"},
                    ],
                }
                year_filter = {
                    "key": "year", "name": "年份",
                    "value": [
                        {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"},
                        {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"},
                        {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                        {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"},
                        {"n": "2019", "v": "2019"}, {"n": "2018", "v": "2018"},
                        {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"},
                        {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"},
                        {"n": "2013", "v": "2013"}, {"n": "2012", "v": "2012"},
                        {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"},
                        {"n": "更早", "v": "2009"},
                    ],
                }
                filters = {}
                for c in classes:
                    filters[c["type_id"]] = [type_filter, year_filter]
                result["filters"] = filters
            return result
        except Exception as exc:
            _log("homeContent err", exc)
            return {"class": [], "list": []}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        extend = extend or {}
        key = self._to_key(tid) or "qq"
        try:
            page = int(pg) if pg else 1
        except Exception:
            page = 1

        params = ["from=" + key, "ac=detail", "limit=24", "pg=" + str(page)]
        t = extend.get("class") or "2"
        params.append("t=" + t)
        if extend.get("year"):
            params.append("year=" + _enc(extend["year"]))

        url = self.host + "/api.php/provide/vod/?" + "&".join(params)
        _log("api category url ->", url)

        data = self._get_json(url)
        if not data:
            return {"list": [], "page": page, "pagecount": 1, "limit": 0,
                    "total": 0}

        vod_list = []
        if isinstance(data.get("list"), list):
            vod_list = [
                {
                    "vod_id": key + "$" + str(v.get("vod_id", "")),
                    "vod_name": v.get("vod_name", ""),
                    "vod_pic": v.get("vod_pic", ""),
                    "vod_remarks": v.get("vod_remarks", ""),
                }
                for v in data["list"]
            ]

        pc = data.get("pagecount") or 1
        try:
            pc = int(pc)
        except Exception:
            pc = 1

        return {
            "list": vod_list,
            "page": page,
            "pagecount": pc,
            "limit": len(vod_list),
            "total": pc * len(vod_list) if vod_list else 0,
        }

    def searchContent(self, key, quick, pg="1"):
        if not key:
            return {"list": []}
        url = (self.host + "/api.php/provide/vod/?ac=detail&wd=" +
               _enc(key) + "&pg=" + str(pg))
        _log("api searchUrl:", url)

        data = self._get_json(url)
        if not data:
            return {"list": [], "page": str(pg), "pagecount": 1}

        vod_list = []
        if isinstance(data.get("list"), list):
            vod_list = [
                {
                    "vod_id": str(v.get("vod_id", "")),
                    "vod_name": v.get("vod_name") or v.get("name") or "",
                    "vod_pic": v.get("vod_pic") or v.get("pic") or "",
                    "vod_remarks": v.get("vod_remarks") or "",
                }
                for v in data["list"]
                if v.get("vod_id")
            ]

        pc = data.get("pagecount") or 1
        try:
            pc = int(pc)
        except Exception:
            pc = 1
        return {"list": vod_list, "page": str(pg), "pagecount": pc}

    def _cj_get(self, source, timeout=AGG_SOURCE_TIMEOUT, **params):
        try:
            api = source["api"].split("?")[0]
            sep = "&" if "?" in api else "?"
            full = api + sep + urllib.parse.urlencode(params)
            text = self._http_get(full, timeout=timeout)
            if text:
                data = json.loads(text)
                if isinstance(data, dict):
                    return data
            return {}
        except Exception:
            return {}

    def _collect_lines(self, src, vod, play_froms, play_urls):
        src_name = src.get("name", src.get("key", ""))
        if src_name in play_froms:
            return
        url_groups = [x.strip() for x in str(vod.get("vod_play_url", "") or "").split("$$$") if x.strip()]
        episodes = []
        seen = set()
        for url_group in url_groups:
            if not url_group:
                continue
            for ep in url_group.split("#"):
                parts = ep.split("$")
                if len(parts) < 2:
                    continue
                ep_name = parts[0]
                ep_url = parts[-1].strip()
                if not ep_url:
                    continue
                mark = ep_name.lower()
                if mark in seen:
                    continue
                seen.add(mark)
                episodes.append(f"{ep_name}${ep_url}")
        if not episodes:
            return
        play_froms.append(src_name)
        play_urls.append("#".join(episodes))

    def _fetch_matches(self, source, name):
        try:
            d1 = self._cj_get(source, timeout=AGG_SOURCE_TIMEOUT, ac="detail", wd=name)
            if not d1 or not d1.get("list"):
                return None
            for v in d1["list"]:
                if _same_name(v.get("vod_name", ""), name) and v.get("vod_play_url"):
                    return {"list": [v]}
        except Exception:
            pass
        return None

    def _deduplicate_playlists(self, play_froms, play_urls):
        unique_froms = []
        unique_urls = []
        seen_names = set()
        seen_groups = set()
        for pf, pu in zip(play_froms, play_urls):
            n = (pf or "").lower()
            u = (pu or "").lower()
            if not n or not u:
                continue
            if n in seen_names or u in seen_groups:
                continue
            seen_names.add(n)
            seen_groups.add(u)
            unique_froms.append(pf)
            unique_urls.append(pu)
        return unique_froms, unique_urls

    def _aggregate_play_lines(self, name, max_count=AGGREGATE_MAX_LINES):
        hits = []
        with ThreadPoolExecutor(max_workers=len(SOURCES)) as executor:
            futures = {executor.submit(self._fetch_matches, s, name): s
                       for s in SOURCES}
            try:
                for fut in as_completed(futures, timeout=AGG_TOTAL_TIMEOUT):
                    try:
                        d = fut.result()
                    except Exception:
                        continue
                    if d and d.get("list"):
                        hits.append((futures[fut], d["list"][0]))
            except FuturesTimeout:
                _log("aggregate timeout, got", len(hits), "hits")

        play_froms, play_urls = [], []
        for src, v in hits:
            self._collect_lines(src, v, play_froms, play_urls)

        play_froms, play_urls = self._deduplicate_playlists(play_froms, play_urls)
        return play_froms[:max_count], play_urls[:max_count]

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vid = str(ids)
        if isinstance(ids, (list, tuple)):
            vid = str(ids[0])
        parts = vid.split("$", 1)
        raw_id = parts[-1].strip()
        guan_key = parts[0] if len(parts) > 1 else ""

        url = (self.host + "/api.php/provide/vod/?" +
               "&".join(["ac=detail", "ids=" + raw_id]))
        _log("detailurl", url)

        data = self._get_json(url)
        if not data:
            return {"list": []}

        vod_list = []
        if isinstance(data.get("list"), list):
            for item in data["list"]:
                if not item.get("vod_id"):
                    continue
                name = item.get("vod_name", "")
                guan_from = str(item.get("vod_play_from", "") or "")
                guan_url = str(item.get("vod_play_url", "") or "")

                if guan_from and guan_url:
                    froms_arr = [x.strip() for x in guan_from.replace("，", ",").split("$$$") if x.strip()]
                    urls_arr = [x.strip() for x in guan_url.split("$$$") if x.strip()]
                    matched = []
                    matched_urls = []
                    for fa, ua in zip(froms_arr, urls_arr):
                        chn = None
                        for _num, (_key, _cname) in _CATEGORY.items():
                            if _key == fa:
                                chn = _cname
                                break
                        if chn:
                            matched.append(chn)
                            matched_urls.append(ua)
                    if guan_key:
                        target_name = None
                        for _num, (_key, _cname) in _CATEGORY.items():
                            if _key == guan_key:
                                target_name = _cname
                                break
                        if target_name and target_name in matched:
                            idx = matched.index(target_name)
                            matched = [matched[idx]]
                            matched_urls = [matched_urls[idx]]

                    guan_from = "$$$".join(matched) if matched else ""
                    guan_url = "$$$".join(matched_urls) if matched_urls else ""

                # 同步聚合：命中缓存直接用，否则现场跑（封顶 8s）
                cj_froms, cj_urls = [], []
                if name:
                    # 缓存键名也微调一下，防止旧版 ac=list 的缓存干扰
                    agg_key = "agg_v2|" + name
                    cached = self.detail_cache.get(agg_key)
                    if cached is not None:
                        cj_froms, cj_urls = cached
                    else:
                        cj_froms, cj_urls = self._aggregate_play_lines(name)
                        self.detail_cache[agg_key] = (cj_froms, cj_urls)

                if guan_from and guan_url:
                    if cj_froms:
                        item["vod_play_from"] = guan_from + "$$$" + "$$$".join(cj_froms)
                        item["vod_play_url"] = guan_url + "$$$" + "$$$".join(cj_urls)
                    else:
                        item["vod_play_from"] = guan_from
                        item["vod_play_url"] = guan_url
                elif cj_froms:
                    item["vod_play_from"] = "$$$".join(cj_froms)
                    item["vod_play_url"] = "$$$".join(cj_urls)
                else:
                    item["vod_play_from"] = ""
                    item["vod_play_url"] = ""

                vod_list.append({
                    "vod_id": (guan_key + "$" + str(item.get("vod_id", ""))
                               if guan_key else str(item.get("vod_id", ""))),
                    "vod_name": item.get("vod_name", ""),
                    "vod_pic": item.get("vod_pic", ""),
                    "vod_remarks": item.get("vod_remarks", ""),
                    "vod_year": item.get("vod_year", ""),
                    "type_name": item.get("type_name", ""),
                    "vod_area": item.get("vod_area", ""),
                    "vod_lang": item.get("vod_lang", ""),
                    "vod_content": item.get("vod_content", ""),
                    "vod_play_from": item.get("vod_play_from", ""),
                    "vod_play_url": item.get("vod_play_url", ""),
                })

        return {"list": vod_list}

    def playerContent(self, flag, id, vipFlags):
        _log("开始获取播放地址: ", id)
        try:
            if self._is_direct(id):
                return {"parse": 0, "url": id,
                        "header": dict(self.header), "playUrl": ""}
            return {"jx": 1, "parse": 1, "url": id,
                    "header": dict(self.header), "playUrl": ""}
        except Exception as exc:
            _log("play失败: ", exc)

        return {"jx": 1, "parse": 1, "url": id,
                "header": dict(self.header), "playUrl": ""}

    def _is_direct(self, url):
        s = str(url)
        return any(k in s for k in ("m3u8", "mp4"))
