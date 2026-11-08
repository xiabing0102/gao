# -*- coding: utf-8 -*-
# 遮天法·极道帝兵·万法归一·SOTVLA6·终极聚合版
# 本命帝兵: 吞天魔罐 | 境界: 四极境·道宫境·轮海境 | 规范等级: S
# 适配: TVBox / 影视仓 / 猫影视 / 宝盒 / 蜂蜜 / 影壳 / FongMi / OK影视
# 架构: 9源MacCMS聚合 + 14层播放器解析 + 智能筛选器

import sys
import re
import json
import base64
import html
import threading
import time
from urllib.parse import quote, unquote, urljoin, urlparse

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def homeContent(self, filter): pass
        def homeVideoContent(self): pass
        def categoryContent(self, tid, pg, filter, extend): pass
        def detailContent(self, ids): pass
        def playerContent(self, flag, id, vipFlags=None): pass
        def searchContent(self, key, quick, pg="1"): pass
        def isVideoFormat(self, url): return False
        def manualVideoCheck(self): return False
        def localProxy(self, param): pass

try:
    import requests
    requests.packages.urllib3.disable_warnings()
except ImportError:
    requests = None


class Spider(BaseSpider):
    def __init__(self):
        super().__init__()
        self.host = "https://www.sotvla6.cc"
        self.name = "ZheTian_SOTVLA6_v6"
        self.cms = "v8"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Referer": self.host + "/",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
        }
        self.s = requests.Session() if requests else None
        if self.s:
            self.s.headers.update(self.headers)
            self.s.verify = False
        self._cache = {}
        self._cache_lock = threading.Lock()

        # ========================================================
        # 极道帝兵·采集源矩阵 (9源已验证)
        # ========================================================
        self._sources = [
            {"type_id": "1", "type_name": "量子资源", "api": "http://cj.lziapi.com/api.php/provide/vod/", "enabled": True},
            {"type_id": "2", "type_name": "樱花资源", "api": "https://m3u8.apiyhzy.com/api.php/provide/vod/", "enabled": True},
            {"type_id": "3", "type_name": "光速资源", "api": "https://api.guangsuapi.com/api.php/provide/vod/", "enabled": True},
            {"type_id": "4", "type_name": "百度资源", "api": "https://api.apibdzy.com/api.php/provide/vod/", "enabled": True},
            {"type_id": "5", "type_name": "闪电资源", "api": "http://sdzyapi.com/api.php/provide/vod/", "enabled": True},
            {"type_id": "6", "type_name": "红牛资源", "api": "https://www.hongniuzy2.com/api.php/provide/vod/", "enabled": True},
            {"type_id": "7", "type_name": "暴风资源", "api": "https://bfzyapi.com/api.php/provide/vod/", "enabled": True},
            {"type_id": "8", "type_name": "非凡资源", "api": "http://ffzy5.tv/api.php/provide/vod/", "enabled": True},
            {"type_id": "9", "type_name": "量子影视", "api": "http://cj.lziapi.com/api.php/provide/vod/from/lzm3u8/", "enabled": True},
        ]

        # ========================================================
        # 万法归一·解析接口矩阵
        # ========================================================
        self._parsers = [
            "https://jx.jsonplayer.com/player/?url=",
            "https://jx.aidup.com/?url=",
            "https://jx.m3u8.tv/jiexi/?url=",
            "https://jx.playerjy.com/?url=",
            "https://jx.777jiexi.com/player/?url=",
            "https://jx.bozrc.com:4433/player/?url=",
        ]

        # ========================================================
        # 天道法则·分类映射
        # ========================================================
        self._type_map = {
            "1": "电影",
            "2": "电视剧",
            "3": "综艺",
            "4": "动漫",
            "6": "短剧",
        }

        # ========================================================
        # 天道法则·筛选器配置
        # ========================================================
        self._filters = {
            "1": [
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"},
                    {"n": "2009", "v": "2009"}, {"n": "2008", "v": "2008"}, {"n": "2007", "v": "2007"},
                    {"n": "2006", "v": "2006"}, {"n": "2005", "v": "2005"}, {"n": "2004", "v": "2004"},
                    {"n": "2003", "v": "2003"}, {"n": "2002", "v": "2002"}, {"n": "2001", "v": "2001"},
                    {"n": "2000", "v": "2000"},
                ]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "中国大陆", "v": "中国大陆"}, {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "泰国", "v": "泰国"}, {"n": "印度", "v": "印度"},
                    {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"},
                    {"n": "俄罗斯", "v": "俄罗斯"}, {"n": "意大利", "v": "意大利"}, {"n": "西班牙", "v": "西班牙"},
                    {"n": "加拿大", "v": "加拿大"}, {"n": "澳大利亚", "v": "澳大利亚"}, {"n": "其他", "v": "其他"},
                ]},
            ],
            "2": [
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"},
                    {"n": "2009", "v": "2009"}, {"n": "2008", "v": "2008"}, {"n": "2007", "v": "2007"},
                    {"n": "2006", "v": "2006"}, {"n": "2005", "v": "2005"}, {"n": "2004", "v": "2004"},
                    {"n": "2003", "v": "2003"}, {"n": "2002", "v": "2002"}, {"n": "2001", "v": "2001"},
                    {"n": "2000", "v": "2000"},
                ]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "中国大陆", "v": "中国大陆"}, {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "泰国", "v": "泰国"}, {"n": "印度", "v": "印度"},
                    {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"},
                    {"n": "俄罗斯", "v": "俄罗斯"}, {"n": "意大利", "v": "意大利"}, {"n": "西班牙", "v": "西班牙"},
                    {"n": "加拿大", "v": "加拿大"}, {"n": "澳大利亚", "v": "澳大利亚"}, {"n": "其他", "v": "其他"},
                ]},
            ],
            "3": [
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"},
                    {"n": "2009", "v": "2009"}, {"n": "2008", "v": "2008"}, {"n": "2007", "v": "2007"},
                    {"n": "2006", "v": "2006"}, {"n": "2005", "v": "2005"}, {"n": "2004", "v": "2004"},
                    {"n": "2003", "v": "2003"}, {"n": "2002", "v": "2002"}, {"n": "2001", "v": "2001"},
                    {"n": "2000", "v": "2000"},
                ]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "中国大陆", "v": "中国大陆"}, {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "泰国", "v": "泰国"}, {"n": "印度", "v": "印度"},
                    {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"},
                    {"n": "俄罗斯", "v": "俄罗斯"}, {"n": "意大利", "v": "意大利"}, {"n": "西班牙", "v": "西班牙"},
                    {"n": "加拿大", "v": "加拿大"}, {"n": "澳大利亚", "v": "澳大利亚"}, {"n": "其他", "v": "其他"},
                ]},
            ],
            "4": [
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"},
                    {"n": "2009", "v": "2009"}, {"n": "2008", "v": "2008"}, {"n": "2007", "v": "2007"},
                    {"n": "2006", "v": "2006"}, {"n": "2005", "v": "2005"}, {"n": "2004", "v": "2004"},
                    {"n": "2003", "v": "2003"}, {"n": "2002", "v": "2002"}, {"n": "2001", "v": "2001"},
                    {"n": "2000", "v": "2000"},
                ]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "中国大陆", "v": "中国大陆"}, {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "泰国", "v": "泰国"}, {"n": "印度", "v": "印度"},
                    {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"},
                    {"n": "俄罗斯", "v": "俄罗斯"}, {"n": "意大利", "v": "意大利"}, {"n": "西班牙", "v": "西班牙"},
                    {"n": "加拿大", "v": "加拿大"}, {"n": "澳大利亚", "v": "澳大利亚"}, {"n": "其他", "v": "其他"},
                ]},
            ],
            "6": [
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"},
                    {"n": "2009", "v": "2009"}, {"n": "2008", "v": "2008"}, {"n": "2007", "v": "2007"},
                    {"n": "2006", "v": "2006"}, {"n": "2005", "v": "2005"}, {"n": "2004", "v": "2004"},
                    {"n": "2003", "v": "2003"}, {"n": "2002", "v": "2002"}, {"n": "2001", "v": "2001"},
                    {"n": "2000", "v": "2000"},
                ]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "中国大陆", "v": "中国大陆"}, {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "泰国", "v": "泰国"}, {"n": "印度", "v": "印度"},
                    {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"},
                    {"n": "俄罗斯", "v": "俄罗斯"}, {"n": "意大利", "v": "意大利"}, {"n": "西班牙", "v": "西班牙"},
                    {"n": "加拿大", "v": "加拿大"}, {"n": "澳大利亚", "v": "澳大利亚"}, {"n": "其他", "v": "其他"},
                ]},
            ],
        }

        # ========================================================
        # 心魔过滤·广告关键词
        # ========================================================
        self.AD_KEYWORDS = [
            "ad", "ads", "advert", "preroll", "片头", "广告",
            "/gg/", "banner", "promo", "casino", "博彩", "充值"
        ]

    # ============================================================
    # 基础神通·网络请求
    # ============================================================
    def _fetch(self, url, retry=3, timeout=15):
        if not self.s:
            return ""
        for i in range(retry):
            try:
                r = self.s.get(url, timeout=timeout)
                r.raise_for_status()
                r.encoding = "utf-8"
                return r.text
            except Exception:
                if i == retry - 1:
                    return ""
                time.sleep(1)
        return ""

    def _fetch_json(self, url, retry=3, timeout=10):
        text = self._fetch(url, retry, timeout)
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            return None

    def _post(self, url, data=None, retry=3):
        if not self.s:
            return ""
        for i in range(retry):
            try:
                r = self.s.post(url, data=data, timeout=15)
                r.encoding = "utf-8"
                return r.text
            except Exception:
                if i == retry - 1:
                    return ""
                time.sleep(1)
        return ""

    # ============================================================
    # 基础神通·文本处理
    # ============================================================
    def _clean_text(self, text):
        if not text:
            return ""
        text = html.unescape(str(text))
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _fix_url(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        if url.startswith("http"):
            return url
        return self.host + "/" + url

    def _fix_pic(self, pic_url):
        return self._fix_url(pic_url) if pic_url else ""

    def _is_video(self, url):
        return any(ext in url.lower() for ext in [".m3u8", ".mp4", ".flv", ".ts", ".mkv"])

    def _guess_type(self, type_name):
        t = type_name.lower() if type_name else ""
        if "电影" in t or "片" in t:
            return "1"
        if "剧" in t or "电视" in t:
            return "2"
        if "综艺" in t or "真人秀" in t or "秀" in t:
            return "3"
        if "动漫" in t or "动画" in t or "番" in t:
            return "4"
        if "短剧" in t:
            return "6"
        return "2"

    # ============================================================
    # 天道接口·TVBox标准
    # ============================================================
    def init(self, extend=""):
        if extend and extend.startswith("http"):
            self.host = extend.rstrip("/")
            self.headers["Referer"] = self.host + "/"
            if self.s:
                self.s.headers.update({"Referer": self.host + "/"})

    def getName(self):
        return self.name

    def isVideoFormat(self, url):
        return self._is_video(url)

    def manualVideoCheck(self):
        return False

    # ============================================================
    # 天道接口·本地代理
    # ============================================================
    def localProxy(self, param):
        try:
            url = unquote(param.get("url", ""))
            if not url.startswith("http"):
                return [404, "text/plain", b"not found"]
            r = self.s.get(url, headers={
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/",
            }, timeout=20)
            ct = r.headers.get("Content-Type", "application/octet-stream")
            return [200, ct, r.content]
        except Exception:
            return [500, "text/plain", b"error"]

    # ============================================================
    # 首页·分类列表 + 筛选器
    # ============================================================
    def homeContent(self, filter):
        classes = []
        for tid, tname in self._type_map.items():
            classes.append({"type_id": tid, "type_name": tname})
        return {"class": classes, "filters": self._filters}

    # ============================================================
    # 首页·推荐视频
    # ============================================================
    def homeVideoContent(self):
        for src in self._sources:
            if not src.get("enabled"):
                continue
            try:
                url = src["api"].rstrip("/") + "/?ac=detail&pagesize=30"
                data = self._fetch_json(url, timeout=10)
                if data and data.get("list"):
                    return {"list": self._format_list(data["list"], src["type_name"])}
            except Exception:
                continue
        return {"list": []}

    # ============================================================
    # 分类·内容列表 (支持筛选器)
    # ============================================================
    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}
        all_videos = []

        year = extend.get("year", "") if extend else ""
        area = extend.get("area", "") if extend else ""

        for src in self._sources:
            if not src.get("enabled"):
                continue
            try:
                api_url = src["api"].rstrip("/") + "/?ac=detail&t=%s&pg=%s&pagesize=24" % (tid, pg)
                if year:
                    api_url += "&year=" + quote(year)
                if area:
                    api_url += "&area=" + quote(area)
                data = self._fetch_json(api_url, timeout=10)
                if data and data.get("list"):
                    videos = self._format_list(data["list"], src["type_name"])
                    all_videos.extend(videos)
            except Exception:
                continue

        seen = set()
        unique = []
        for v in all_videos:
            key = v.get("vod_name", "") + v.get("vod_remarks", "")
            if key and key not in seen:
                seen.add(key)
                unique.append(v)

        result["list"] = unique[:48]
        result["pagecount"] = 999 if len(unique) >= 24 else int(pg)
        result["total"] = len(unique)
        return result

    # ============================================================
    # 详情·影片信息
    # ============================================================
    def detailContent(self, ids):
        try:
            vid = ids[0] if isinstance(ids, list) else ids
            if "@@" in str(vid):
                src_name, real_id = vid.split("@@", 1)
                source = next((s for s in self._sources if s["type_name"] == src_name), None)
                if source:
                    return self._get_detail_from_source(source, real_id)

            for src in self._sources:
                if not src.get("enabled"):
                    continue
                try:
                    url = src["api"].rstrip("/") + "/?ac=detail&ids=" + quote(str(vid))
                    data = self._fetch_json(url, timeout=10)
                    if data and data.get("list") and len(data["list"]) > 0:
                        return self._format_detail(data["list"][0], src["type_name"])
                except Exception:
                    continue

            return {"list": []}
        except Exception:
            return {"list": []}

    def _get_detail_from_source(self, source, vid):
        try:
            url = source["api"].rstrip("/") + "/?ac=detail&ids=" + quote(str(vid))
            data = self._fetch_json(url, timeout=10)
            if data and data.get("list") and len(data["list"]) > 0:
                return self._format_detail(data["list"][0], source["type_name"])
            return {"list": []}
        except Exception:
            return {"list": []}

    def _format_detail(self, item, source_name):
        vod_id = str(item.get("vod_id", ""))
        vod_name = self._clean_text(item.get("vod_name", "未知"))
        vod_pic = self._fix_pic(item.get("vod_pic", ""))
        vod_year = str(item.get("vod_year", ""))
        vod_area = item.get("vod_area", "")
        vod_actor = item.get("vod_actor", "")
        vod_director = item.get("vod_director", "")
        vod_remarks = item.get("vod_remarks", "")
        vod_content = self._clean_text(item.get("vod_content", ""))

        play_from = item.get("vod_play_from", "")
        play_url = item.get("vod_play_url", "")

        sources = []
        play_urls = []

        if play_from and play_url:
            from_list = play_from.split("$$$")
            url_list = play_url.split("$$$")
            for i, fname in enumerate(from_list):
                if i < len(url_list):
                    sources.append(fname.strip() or ("线路%d" % (i+1)))
                    play_urls.append(url_list[i].strip())
        else:
            sources.append(source_name)
            play_urls.append(play_url or "")

        unique_id = "%s@@%s" % (source_name, vod_id)

        return {
            "list": [{
                "vod_id": unique_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_year": vod_year,
                "vod_area": vod_area,
                "vod_actor": vod_actor,
                "vod_director": vod_director,
                "vod_remarks": vod_remarks,
                "vod_content": vod_content,
                "vod_play_from": "$$$".join(sources),
                "vod_play_url": "$$$".join(play_urls),
            }]
        }

    # ============================================================
    # 极道帝兵·14层播放器解析
    # ============================================================
    def playerContent(self, flag, id, vipFlags=None):
        try:
            if self._is_video(id):
                return {
                    "parse": 0,
                    "url": id,
                    "header": json.dumps({
                        "Referer": self.host + "/",
                        "User-Agent": self.headers["User-Agent"],
                    }),
                }

            if "$" in id:
                parts = id.split("$")
                if len(parts) >= 2:
                    real_url = parts[-1].strip()
                    if self._is_video(real_url):
                        return self._build_result(real_url)
                    id = real_url

            if id.startswith("/") or (not self._is_video(id) and id.startswith("http")):
                html_text = self._fetch(id) if id.startswith("http") else self._fetch(self.host + id)
                if html_text:
                    # 第1层: mip-iframe src参数提取
                    m = re.search(
                        r'<mip-iframe[^>]+src=["\'][^"\']*url=([^"\'\s>]+)["\'\s>]',
                        html_text
                    )
                    if m:
                        real_url = unquote(m.group(1))
                        if real_url.startswith("http") and self._is_video(real_url):
                            return self._build_result(real_url)

                    # 第2层: 标准iframe src
                    m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html_text)
                    if m:
                        iframe_src = self._fix_url(m.group(1))
                        if self._is_video(iframe_src):
                            return self._build_result(iframe_src, referer=id)
                        iframe_html = self._fetch(iframe_src)
                        if iframe_html:
                            m2 = re.search(r'(https?://[^\s"<>]+\.m3u8[^\s"<>]*)', iframe_html)
                            if m2:
                                return self._build_result(m2.group(1), referer=iframe_src)

                    # 第3层: 直接匹配m3u8
                    m = re.search(r'(https?://[^\s"<>]+\.m3u8[^\s"<>]*)', html_text)
                    if m:
                        return self._build_result(m.group(1))

                    # 第4层: 直接匹配mp4
                    m = re.search(r'(https?://[^\s"<>]+\.mp4[^\s"<>]*)', html_text)
                    if m:
                        return self._build_result(m.group(1))

                    # 第5层: player_xxxx变量
                    m = re.search(r'var\s+(player_\w+)\s*=\s*(\{.*?\});', html_text, re.S)
                    if m:
                        try:
                            data = json.loads(m.group(2).replace("\\/", "/"))
                            url = data.get("url", "")
                            if url:
                                return self._build_result(url)
                        except Exception:
                            pass

                    # 第6层: video标签
                    m = re.search(r'<video[^>]*src=["\']([^"\']+)["\']', html_text, re.I)
                    if m:
                        return self._build_result(m.group(1))

                    # 第7层: source标签
                    m = re.search(r'<source[^>]*src=["\']([^"\']+)["\']', html_text, re.I)
                    if m:
                        return self._build_result(m.group(1))

                    # 第8层: var url/src
                    m = re.search(r'var\s+(?:url|src|videoUrl)\s*=\s*["\']([^"\']+)["\']', html_text)
                    if m:
                        return self._build_result(m.group(1))

                    # 第9层: Base64编码URL
                    m = re.search(r'["\']([A-Za-z0-9+/=]{50,})["\']', html_text)
                    if m:
                        try:
                            decoded = base64.b64decode(m.group(1)).decode("utf-8")
                            if decoded.startswith("http") and self._is_video(decoded):
                                return self._build_result(decoded)
                        except Exception:
                            pass

                    # 第10层: location.href跳转
                    m = re.search(r'location\.href\s*=\s*["\']([^"\']+)["\']', html_text)
                    if m:
                        return self._build_result(m.group(1))

                    # 第11层: meta refresh
                    m = re.search(r'<meta[^>]+refresh[^>]+url=([^"\']+)', html_text, re.I)
                    if m:
                        return self._build_result(m.group(1))

                    # 第12层: eval混淆标记嗅探
                    m = re.search(r'eval\((.*?)\)', html_text, re.S)
                    if m:
                        return {"parse": 1, "url": id, "header": ""}

                    # 第13层: 通用URL提取
                    m = re.search(r'(https?://[^\s"<>]+\.(?:m3u8|mp4|flv))', html_text)
                    if m:
                        return self._build_result(m.group(1))

            # 第14层: 解析接口兜底
            parser_url = self._parsers[0] + quote(id, safe="")
            return {
                "parse": 1,
                "url": parser_url,
                "header": json.dumps({
                    "Referer": self.host + "/",
                    "User-Agent": self.headers["User-Agent"],
                }),
            }
        except Exception:
            return {"parse": 0, "url": id, "header": ""}

    def _build_result(self, url, referer=None):
        return {
            "parse": 0,
            "url": url,
            "header": json.dumps({
                "Referer": referer or self.host + "/",
                "User-Agent": self.headers["User-Agent"],
            }),
        }

    # ============================================================
    # 搜索·聚合搜索
    # ============================================================
    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}
        all_results = []

        for src in self._sources:
            if not src.get("enabled"):
                continue
            try:
                url = src["api"].rstrip("/") + "/?ac=detail&wd=" + quote(key) + "&pg=" + pg
                data = self._fetch_json(url, timeout=10)
                if data and data.get("list"):
                    videos = self._format_list(data["list"], src["type_name"])
                    all_results.extend(videos)
            except Exception:
                continue

        seen = set()
        unique = []
        for v in all_results:
            key_str = v.get("vod_name", "") + v.get("vod_remarks", "")
            if key_str and key_str not in seen:
                seen.add(key_str)
                unique.append(v)

        result["list"] = unique
        result["pagecount"] = 999 if len(unique) >= 24 else int(pg)
        result["total"] = len(unique)
        return result

    # ============================================================
    # 工具·数据格式化
    # ============================================================
    def _format_list(self, items, source_name):
        results = []
        for item in items:
            try:
                vod_id = str(item.get("vod_id", ""))
                vod_name = self._clean_text(item.get("vod_name", "未知"))
                vod_pic = self._fix_pic(item.get("vod_pic", ""))
                vod_remarks = item.get("vod_remarks", item.get("vod_serial", ""))
                unique_id = "%s@@%s" % (source_name, vod_id)
                results.append({
                    "vod_id": unique_id,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": "[%s] %s" % (source_name, vod_remarks) if vod_remarks else source_name,
                })
            except Exception:
                continue
        return results

    def _clean_m3u8(self, text, base_url=""):
        if not text:
            return ""
        lines = text.splitlines()
        cleaned = []
        skip_next = False
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            if any(kw in line_stripped.lower() for kw in self.AD_KEYWORDS):
                skip_next = True
                continue
            if skip_next and line_stripped.startswith("#EXTINF"):
                skip_next = False
                continue
            if not line_stripped.startswith("#") and not line_stripped.startswith("http"):
                if base_url:
                    line = urljoin(base_url, line_stripped)
            cleaned.append(line)
        return "\n".join(cleaned)
