# -*- coding: utf-8 -*-
"""
目标站: 323影视 (323433ssdfd.top)
版本: V4.5 - 修复播放失败
V4.5 更新:
  [修复] 1. 解码响应兼容 code=1 与 code=200
  [修复] 2. 屏蔽线路改为仅严格匹配 from_code（避免误杀）
  [修复] 3. 解码结果自动识别 mp4/m3u8 并返回 format
  [修复] 4. _parse_protobuf 支持 wire type 1/5，不再中途 break
  [修复] 5. 兜底返回空 url 而不是原始编码 id（避免 TVBox 外部解析）
  [修复] 6. 解码结果支持 JSON / URL-encoded / 纯直链 三态
"""

import re
import sys
import os
import json
import time
import hashlib
import urllib.parse
import urllib.request

sys.path.append('..')
from base.spider import Spider as SpiderBase


class Spider(SpiderBase):
    name = "323影视"

    RENAME_MAP = {
        "CO4K": "4K专线",
        "co": "CO蓝光",
        "YYNB": "YY蓝光",
        "NBY": "NB蓝光",
        "qsvip": "青山蓝光",
        "BBA": "BB蓝光",
    }

    # 只在 from_code 上严格匹配（避免误杀）
    BLOCK_CODES = {"PO", "PO蓝光", "POBL", "PO4K"}

    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass
        self.extend = extend
        self.site_url = "https://323433ssdfd.top"
        self.api_base = self.site_url + "/api.php/web"
        self.timeout = 15
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site_url + '/',
            'Accept': 'application/json',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'X-Client': '8f3d2a1c7b6e5d4c9a0b1f2e3d4c5b6a',
            'web-sign': 'ddtvf65f3a83d6d9ad6f',
        }
        self.categories = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "剧集"},
            {"type_id": "3", "type_name": "动漫"},
            {"type_id": "4", "type_name": "综艺"},
        ]
        self._finger = "WF-2c064bc5b3400788f31b848849bc3a60f835423ba2dfe69d7ea93974c216e4f2"
        self._app_id = "com.web.player"
        self._app_sk = "WEB-50a8e9c84a1dc05669a692ded99a2dac46527229e607a7be15db88dbc59059d1"
        self._app_v = "1"
        self._nonce = "00000000000000000000000000000000"

    def getName(self):
        return "323影视"

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|flv|avi|mkv|wmv|ts)(\?|$)', url, re.I))

    def manualVideoCheck(self):
        return True

    # ---------- 屏蔽判断：仅按代码严格匹配 ----------
    def _is_blocked(self, from_code, show_name=""):
        code = (from_code or "").strip().upper()
        if not code:
            return False
        if code in self.BLOCK_CODES:
            return True
        # 避免 "CO4K" 里含 "O" 这类误杀，只在整段相同或前缀为 PO 时判定
        for kw in self.BLOCK_CODES:
            if code == kw or code.startswith(kw + "_") or code.startswith(kw + "-"):
                return True
        return False

    # ---------- Protobuf ----------
    @staticmethod
    def _encode_varint(value):
        result = bytearray()
        value = int(value)
        while value > 0x7f:
            result.append((value & 0x7f) | 0x80)
            value >>= 7
        result.append(value & 0x7f)
        return bytes(result)

    @classmethod
    def _encode_string_field(cls, field_num, value):
        encoded = value.encode('utf-8') if isinstance(value, str) else value
        tag = (field_num << 3) | 2
        return cls._encode_varint(tag) + cls._encode_varint(len(encoded)) + encoded

    @classmethod
    def _encode_varint_field(cls, field_num, value):
        tag = (field_num << 3) | 0
        return cls._encode_varint(tag) + cls._encode_varint(value)

    @staticmethod
    def _parse_protobuf(data):
        offset = 0
        fields = {}
        total = len(data)
        while offset < total:
            # 读 tag
            tag = 0
            shift = 0
            while offset < total and data[offset] & 0x80:
                tag |= (data[offset] & 0x7f) << shift
                shift += 7
                offset += 1
            if offset >= total:
                break
            tag |= data[offset] << shift
            offset += 1

            field_num = tag >> 3
            wire_type = tag & 0x07

            if wire_type == 0:  # varint
                value = 0
                shift = 0
                while offset < total and data[offset] & 0x80:
                    value |= (data[offset] & 0x7f) << shift
                    shift += 7
                    offset += 1
                if offset < total:
                    value |= data[offset] << shift
                    offset += 1
                fields[field_num] = value
            elif wire_type == 2:  # length-delimited
                field_len = 0
                shift = 0
                while offset < total and data[offset] & 0x80:
                    field_len |= (data[offset] & 0x7f) << shift
                    shift += 7
                    offset += 1
                if offset < total:
                    field_len |= data[offset] << shift
                    offset += 1
                raw = data[offset:offset + field_len]
                offset += field_len
                try:
                    fields[field_num] = raw.decode('utf-8')
                except Exception:
                    fields[field_num] = raw
            elif wire_type == 1:  # fixed64
                offset += 8
            elif wire_type == 5:  # fixed32
                offset += 4
            else:
                # 未知 wire type，尝试跳过
                break
        return fields

    # ---------- 签名 ----------
    def _generate_signature(self, timestamp_ms):
        sign_str = "finger={}&id={}&nonce={}&sk={}&time={}&v={}".format(
            self._finger, self._app_id, self._nonce, self._app_sk, timestamp_ms, self._app_v
        )
        return hashlib.sha256(sign_str.encode('utf-8')).hexdigest().upper()

    def _build_decode_request(self, play_url, from_str):
        timestamp_ms = int(time.time() * 1000)
        signature = self._generate_signature(timestamp_ms)
        proto = b""
        proto += self._encode_string_field(1, play_url)
        proto += self._encode_string_field(2, from_str)
        proto += self._encode_varint_field(3, timestamp_ms)
        proto += self._encode_string_field(4, self._nonce)
        proto += self._encode_string_field(5, signature)
        proto += self._encode_string_field(6, self._app_id)
        proto += self._encode_varint_field(7, int(self._app_v))
        return proto

    # ---------- HTTP ----------
    def _api_get(self, path, params=None):
        url = self.api_base + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        try:
            resp = self.fetch(url, headers=self.headers, timeout=self.timeout)
            if resp is not None:
                text = None
                if hasattr(resp, 'text'):
                    text = resp.text
                elif hasattr(resp, 'content'):
                    c = resp.content
                    text = c.decode('utf-8') if isinstance(c, (bytes, bytearray)) else str(c)
                elif isinstance(resp, (bytes, bytearray)):
                    text = resp.decode('utf-8')
                elif isinstance(resp, str):
                    text = resp
                if text:
                    return json.loads(text)
        except Exception as e:
            print("[323影视] fetch 失败: {} -> {}".format(path, e))

        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print("[323影视] API请求失败: {} -> {}".format(path, e))
        return None

    def _http_post_binary(self, url, data, headers=None):
        req_headers = headers or {}
        try:
            req = urllib.request.Request(url, data=data, headers=req_headers, method='POST')
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read()
        except Exception as e:
            print("[323影视] urllib POST 失败: {}".format(e))
        return None

    # ---------- 解码 ----------
    def _decode_url(self, play_url, from_str):
        if not play_url or not from_str:
            return None
        try:
            proto = self._build_decode_request(play_url, from_str)
            decode_url = self.api_base + "/decode/url"
            decode_headers = {
                'Content-Type': 'application/x-protobuf',
                'Accept': 'application/x-protobuf, */*',
                'X-Client': self.headers['X-Client'],
                'web-sign': self.headers['web-sign'],
                'User-Agent': self.headers['User-Agent'],
                'Referer': self.site_url + '/',
                'Origin': self.site_url,
            }
            resp_data = self._http_post_binary(decode_url, proto, decode_headers)
            if not resp_data:
                print("[323影视] 解码API无响应")
                return None

            # 兼容 JSON 响应
            if resp_data.lstrip()[:1] in (b'{', b'['):
                try:
                    j = json.loads(resp_data.decode('utf-8', errors='replace'))
                    code = j.get("code")
                    if code in (1, 200, "1", "200"):
                        return j.get("data") or j.get("url") or ""
                    print("[323影视] JSON 解码失败: {}".format(j.get("msg")))
                    return None
                except Exception:
                    pass

            # protobuf 响应
            resp_fields = self._parse_protobuf(resp_data)
            code = resp_fields.get(1)
            data_field = resp_fields.get(3)

            # 兼容 1 / 200 / 字符串
            if (code in (1, 200, "1", "200")) and data_field:
                if isinstance(data_field, bytes):
                    data_field = data_field.decode('utf-8', errors='replace')
                return data_field

            msg = resp_fields.get(2, "")
            if isinstance(msg, bytes):
                msg = msg.decode('utf-8', errors='replace')
            print("[323影视] 解码失败: code={}, msg={}".format(code, msg))
        except Exception as e:
            print("[323影视] 解码异常: {}".format(e))
        return None

    # ---------- 工具 ----------
    @staticmethod
    def _clean_html(text):
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'&[a-z]+;', ' ', text)
        return text.strip()

    @staticmethod
    def _format_area(vod_area):
        if not vod_area:
            return ""
        if isinstance(vod_area, list):
            return ",".join(str(a) for a in vod_area)
        return str(vod_area)

    @staticmethod
    def _format_class(vod_class):
        if not vod_class:
            return ""
        if isinstance(vod_class, list):
            return ",".join(str(c) for c in vod_class)
        return str(vod_class)

    @staticmethod
    def _format_video_list(items):
        videos = []
        for item in items:
            vod_id = str(item.get("vod_id", ""))
            if not vod_id:
                continue
            videos.append({
                "vod_id": vod_id,
                "vod_name": item.get("vod_name", ""),
                "vod_pic": item.get("vod_pic", ""),
                "vod_remarks": item.get("vod_remarks", ""),
                "vod_year": str(item.get("vod_year", "")),
                "vod_area": Spider._format_area(item.get("vod_area")),
                "vod_actor": item.get("vod_actor", ""),
                "vod_director": item.get("vod_director", ""),
                "vod_type": Spider._format_class(item.get("vod_class")),
                "vod_score": str(item.get("vod_douban_score", "")),
            })
        return videos

    # ---------- TVBox 接口 ----------
    def homeContent(self, filter=False):
        result = {"class": self.categories, "list": [], "filters": {}}
        data = self._api_get("/index/home")
        if not data or data.get("code") != 200:
            return result
        home_data = data.get("data", {})
        cats = home_data.get("categories", [])
        if cats:
            self.categories = [
                {"type_id": str(c["type_id"]), "type_name": c["type_name"]}
                for c in cats
            ]
            result["class"] = self.categories
        videos = []
        seen = set()
        for cat in cats:
            for v in cat.get("videos", []):
                vid = str(v.get("vod_id", ""))
                if vid and vid not in seen:
                    seen.add(vid)
                    videos.append({
                        "vod_id": vid,
                        "vod_name": v.get("vod_name", ""),
                        "vod_pic": v.get("vod_pic", ""),
                        "vod_remarks": v.get("vod_remarks", ""),
                    })
        result["list"] = videos[:30]
        return result

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg) if pg else 1
        type_name = ""
        for c in self.categories:
            if str(c["type_id"]) == str(tid):
                type_name = c["type_name"]
                break
        if not type_name:
            return {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}

        params = {"type_name": type_name, "page": page, "sort": "hits"}
        if extend:
            if extend.get("class"):
                params["class"] = extend["class"]
            if extend.get("area"):
                params["area"] = extend["area"]
            if extend.get("year"):
                params["year"] = extend["year"]

        data = self._api_get("/filter/vod", params)
        empty_result = {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}
        if not data or data.get("code") != 200:
            return empty_result
        items = data.get("data", [])
        if not isinstance(items, list):
            return empty_result
        videos = self._format_video_list(items)
        has_more = len(items) >= 18
        return {
            "list": videos,
            "page": page,
            "pagecount": page + 1 if has_more else page,
            "limit": len(videos),
            "total": len(videos),
        }

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        if not vid:
            return {"list": []}
        data = self._api_get("/vod/get_detail", {"vod_id": str(vid)})
        if not data or data.get("code") != 200:
            return {"list": []}
        items = data.get("data", [])
        if not items or not isinstance(items, list):
            return {"list": []}

        vod = items[0]
        vodplayer = data.get("vodplayer", [])
        play_from_raw = vod.get("vod_play_from", "")
        play_url_raw = vod.get("vod_play_url", "")

        player_info = {}
        if isinstance(vodplayer, list):
            for p in vodplayer:
                from_code = p.get("from", "")
                if from_code:
                    player_info[from_code] = {
                        "show": p.get("show", "") or from_code,
                        "decode_status": str(p.get("decode_status", "1")),
                        "sort": float(p.get("sort", "0")) if p.get("sort") else 0,
                    }

        if play_from_raw and "$$$" in play_from_raw:
            from_codes_raw = [c.strip() for c in play_from_raw.split("$$$")]
        else:
            from_codes_raw = [play_from_raw.strip()] if play_from_raw else []

        if play_url_raw and "$$$" in play_url_raw:
            url_groups_raw = play_url_raw.split("$$$")
        else:
            url_groups_raw = [play_url_raw] if play_url_raw else []

        n = max(len(from_codes_raw), len(url_groups_raw))
        from_codes_raw += [""] * (n - len(from_codes_raw))
        url_groups_raw += [""] * (n - len(url_groups_raw))

        enabled_lines = []
        for i, from_code in enumerate(from_codes_raw):
            if not from_code:
                continue
            info = player_info.get(from_code, {})
            show_name_tmp = info.get("show", from_code)
            if self._is_blocked(from_code, show_name_tmp):
                print("[323影视] 屏蔽线路: code={}, show={}".format(from_code, show_name_tmp))
                continue
            decode_status = info.get("decode_status", "1")
            sort_val = info.get("sort", 0)
            url_group = url_groups_raw[i] if i < len(url_groups_raw) else ""
            enabled_lines.append({
                "from_code": from_code,
                "show": info.get("show", from_code),
                "decode_status": decode_status,
                "sort": sort_val,
                "url_group": url_group,
            })

        enabled_lines.sort(key=lambda x: (x["decode_status"] != "1", -x["sort"]))
        has_enabled = any(l["decode_status"] == "1" for l in enabled_lines)
        if has_enabled:
            enabled_lines = [l for l in enabled_lines if l["decode_status"] == "1"]

        display_parts = []
        url_parts = []
        for line in enabled_lines:
            show_name = self.RENAME_MAP.get(line["from_code"]) or \
                        self.RENAME_MAP.get(line["show"]) or line["show"]
            display_parts.append(show_name)
            url_parts.append(line["url_group"])

        vod_play_from = "$$$".join(display_parts)
        vod_play_url = "$$$".join(url_parts)
        content = self._clean_html(vod.get("vod_content", ""))

        result_vod = {
            "vod_id": str(vod.get("vod_id", vid)),
            "vod_name": vod.get("vod_name", ""),
            "vod_pic": vod.get("vod_pic", ""),
            "vod_content": content,
            "vod_year": str(vod.get("vod_year", "")),
            "vod_area": self._format_area(vod.get("vod_area")),
            "vod_actor": vod.get("vod_actor", ""),
            "vod_director": vod.get("vod_director", ""),
            "vod_remarks": vod.get("vod_remarks", ""),
            "vod_class": self._format_class(vod.get("vod_class")),
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url,
        }
        return {"list": [result_vod]}

    def searchContent(self, key, quick=False, pg="1"):
        page = int(pg) if pg else 1
        data = self._api_get("/search/index", {"wd": key, "page": page, "limit": 15})
        if not data or data.get("code") != 200:
            return {"list": [], "page": page, "pagecount": 1}
        items = data.get("data", [])
        if not isinstance(items, list):
            return {"list": [], "page": page, "pagecount": 1}
        videos = self._format_video_list(items)
        pagecount = page + 1 if len(items) >= 15 else page
        return {"list": videos, "page": page, "pagecount": pagecount}

    def _resolve_from_code(self, flag):
        if not flag:
            return ""
        flag = flag.strip()
        if "@@" in flag:
            return flag.split("@@")[-1].strip()
        for code, name in self.RENAME_MAP.items():
            if flag == name:
                return code
        return flag

    @staticmethod
    def _detect_format(url):
        low = url.lower()
        if ".m3u8" in low:
            return "application/vnd.apple.mpegurl"
        if ".mp4" in low:
            return "video/mp4"
        if ".flv" in low:
            return "video/x-flv"
        if ".ts" in low:
            return "video/mp2t"
        return ""

    def playerContent(self, flag, id, vipFlags=None):
        raw_id = (id or "").strip()

        # 已是直链，直接播放
        if raw_id and re.match(r'^https?://', raw_id, re.I):
            fmt = self._detect_format(raw_id)
            ret = {
                "parse": 0,
                "url": raw_id,
                "header": {
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": self.site_url + "/",
                }
            }
            if fmt:
                ret["format"] = fmt
            return ret

        from_code = self._resolve_from_code(flag)

        if self._is_blocked(from_code, flag):
            print("[323影视] 拒绝播放已屏蔽线路: flag={}, code={}".format(flag, from_code))
            return {"parse": 0, "url": "", "header": {}}

        print("[323影视] 播放: flag={}, from_code={}, id_head={}".format(
            flag, from_code, raw_id[:80]))

        # 主路径：解码
        if raw_id and from_code:
            decoded_url = self._decode_url(raw_id, from_code)
            if decoded_url:
                # 1) JSON 包裹
                if decoded_url.lstrip().startswith("{"):
                    try:
                        j = json.loads(decoded_url)
                        decoded_url = j.get("url") or j.get("data") or ""
                    except Exception:
                        pass

                # 2) URL-encoded 直链，循环 unquote 最多 2 次
                for _ in range(3):
                    if re.match(r'^https?://', decoded_url or "", re.I):
                        break
                    try:
                        new_url = urllib.parse.unquote(decoded_url)
                        if new_url == decoded_url:
                            break
                        decoded_url = new_url
                    except Exception:
                        break

                if re.match(r'^https?://', decoded_url or "", re.I):
                    fmt = self._detect_format(decoded_url)
                    ret = {
                        "parse": 0,
                        "url": decoded_url,
                        "header": {
                            "User-Agent": self.headers["User-Agent"],
                            "Referer": self.site_url + "/",
                        }
                    }
                    if fmt:
                        ret["format"] = fmt
                    print("[323影视] 解码成功: {}".format(decoded_url[:120]))
                    return ret

                print("[323影视] 解码结果非URL: {}".format((decoded_url or "")[:200]))

        # 兜底：不再返回编码 id（TVBox 会拿去外部解析必然失败）
        print("[323影视] 播放失败，返回空 url")
        return {
            "parse": 0,
            "url": "",
            "header": {
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.site_url + "/",
            }
        }

    def localProxy(self, param):
        return None