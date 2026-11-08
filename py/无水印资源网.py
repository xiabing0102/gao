#!/usr/bin/python
# -*- coding: utf-8 -*-
import json, requests
from urllib.parse import quote
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "无水印资源网"

    def init(self, extend=""):
        self.host = "https://api.wsyzy.net"
        self.api = self.host + "/api.php/provide/vod/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": self.host + "/"
        }
        self.categories = [
            {"type_id": "6", "type_name": "动作片"},
            {"type_id": "7", "type_name": "喜剧片"},
            {"type_id": "8", "type_name": "爱情片"},
            {"type_id": "9", "type_name": "科幻片"},
            {"type_id": "10", "type_name": "恐怖片"},
            {"type_id": "11", "type_name": "剧情片"},
            {"type_id": "12", "type_name": "战争片"},
            {"type_id": "20", "type_name": "纪录片"},
            {"type_id": "39", "type_name": "动画片"},
            {"type_id": "62", "type_name": "4K电影"},
            {"type_id": "70", "type_name": "邵氏电影"},
            {"type_id": "71", "type_name": "Netflix电影"},
            {"type_id": "13", "type_name": "国产剧"},
            {"type_id": "14", "type_name": "欧美剧"},
            {"type_id": "15", "type_name": "韩剧"},
            {"type_id": "16", "type_name": "日剧"},
            {"type_id": "17", "type_name": "港剧"},
            {"type_id": "18", "type_name": "台剧"},
            {"type_id": "19", "type_name": "泰剧"},
            {"type_id": "23", "type_name": "海外剧"},
            {"type_id": "72", "type_name": "Netflix自制剧"},
            {"type_id": "25", "type_name": "大陆综艺"},
            {"type_id": "26", "type_name": "日韩综艺"},
            {"type_id": "27", "type_name": "港台综艺"},
            {"type_id": "28", "type_name": "欧美综艺"},
            {"type_id": "47", "type_name": "演唱会"},
            {"type_id": "29", "type_name": "国产动漫"},
            {"type_id": "30", "type_name": "日韩动漫"},
            {"type_id": "31", "type_name": "欧美动漫"},
            {"type_id": "44", "type_name": "港台动漫"},
            {"type_id": "45", "type_name": "海外动漫"},
            {"type_id": "63", "type_name": "有声动漫"},
            {"type_id": "64", "type_name": "女频恋爱"},
            {"type_id": "65", "type_name": "反转爽剧"},
            {"type_id": "66", "type_name": "古装仙侠"},
            {"type_id": "67", "type_name": "年代穿越"},
            {"type_id": "68", "type_name": "脑洞悬疑"},
            {"type_id": "69", "type_name": "现代都市"},
            {"type_id": "73", "type_name": "擦边短剧"},
            {"type_id": "76", "type_name": "漫剧"},
            {"type_id": "56", "type_name": "港台三级"},
            {"type_id": "57", "type_name": "韩国伦理"},
            {"type_id": "58", "type_name": "西方伦理"},
            {"type_id": "59", "type_name": "日本伦理"},
            {"type_id": "60", "type_name": "两性课堂"},
            {"type_id": "61", "type_name": "写真热舞"}
        ]

    def _get(self, url):
        try:
            r = requests.get(url, headers=self.headers, timeout=15)
            r.encoding = r.apparent_encoding or "utf-8"
            return r.json()
        except:
            return {}

    def _parse_list(self, data):
        items = []
        for v in data.get("list", []):
            items.append({
                "vod_id": str(v.get("vod_id", "")),
                "vod_name": v.get("vod_name", ""),
                "vod_pic": v.get("vod_pic", ""),
                "vod_remarks": v.get("vod_remarks", "")
            })
        return items

    def homeContent(self, filter):
        data = self._get(self.api + "?ac=list")
        return {"class": self.categories, "list": self._parse_list(data), "filters": {}}

    def categoryContent(self, tid, pg, filter, extend):
        data = self._get(f"{self.api}?ac=list&t={tid}&pg={pg}")
        return {
            "page": int(pg),
            "pagecount": int(data.get("pagecount", 1) or 1),
            "limit": int(data.get("limit", 20) or 20),
            "total": int(data.get("total", 0) or 0),
            "list": self._parse_list(data)
        }

    def detailContent(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        result = {"list": []}
        for vid in ids:
            data = self._get(f"{self.api}?ac=detail&ids={vid}")
            for v in data.get("list", []):
                result["list"].append({
                    "vod_id": str(v.get("vod_id", "")),
                    "vod_name": v.get("vod_name", ""),
                    "vod_pic": v.get("vod_pic", ""),
                    "vod_play_from": v.get("vod_play_from", ""),
                    "vod_play_url": v.get("vod_play_url", "")
                })
        return result

    def searchContent(self, key, quick, pg="1"):
        data = self._get(f"{self.api}?ac=detail&wd={quote(key)}&pg={pg}")
        return {"list": self._parse_list(data), "page": int(pg)}

    def playerContent(self, flag, id, vipFlags):
        return {"parse": 0, "url": id, "header": json.dumps(self.headers)}