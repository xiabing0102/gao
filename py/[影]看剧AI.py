#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
看剧AI（kanju.ai）影视源（T4）
=================================
站点: https://kanju.ai  （AI 会话式影视平台，Vite SPA）
数据: 全部走 /v1/ JSON API，请求需 HMAC-SHA256 签名（密钥硬编码在前端 JS）

接口映射:
  homeContent        -> GET /v1/feed/home        首页榜单信息流（sections -> cards）
  homeVideoContent   -> GET /v1/feed/home        同上，合并去重取 60 条
  categoryContent    -> GET /v1/browse/catalog   分类浏览  kind=电影/剧集/短剧/动漫/综艺/纪录片/体育
  searchContent      -> GET /v1/suggest          搜索建议（过滤无 variant_id 条目）
  detailContent      -> GET /v1/catalog/{id}            详情
                        GET /v1/catalog/{id}/episodes   剧集全量（limit/offset 分页, 48/页）
  playerContent      -> GET /v1/playback/resolve/{ep_token} -> line_options 取 m3u8 直链

播放链路: 剧集 token(YJ-xxx) -> resolve 返回 26 条线路,
          跳过需登录的官方 R 线路(resolve_ticket)与 resolve:// 票据,
          取 url_kind=m3u8 的第三方直链, 实测 #EXTM3U 门禁后以 parse:0 直出。

已知限制:
  * 官方 1080P 线路需登录（resolve-line 返回 401 playback_user_session_required），本源自动跳过。
  * CDN 直链带时效, playerContent 每次实时 resolve, 不做缓存复用。
  * 封面使用百度 gimg 图床, 若无法访问自动还原 img.baipiaozhe.com 源站地址。
  * 多季剧仅取默认（selected/default）variant 的剧集。
"""

import hashlib
import hmac
import json
import os
import re
import time
from urllib.parse import urlencode, urljoin, urlparse, quote

import requests
from base.spider import Spider

# 前端 JS（assets/movie-card-runtime-*.js）硬编码的签名密钥, 站点轮换时需同步更新
_SIGN_KEY = "557d0e4ae929f438da6bd84412374e6086b8af09b3fed54bf22601d5bf8c54a0"

_KIND_NAMES = [
    ("series", "剧集"),
    ("movie", "电影"),
    ("short_drama", "短剧"),
    ("anime", "动漫"),
    ("variety", "综艺"),
    ("documentary", "纪录片"),
    ("sports", "体育"),
]


class Spider(Spider):
    def getName(self):
        return "看剧AI"

    def init(self, extend=""):
        self.name = "看剧AI"
        self.host = "https://kanju.ai"
        self.key = _SIGN_KEY
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Referer": self.host + "/",
            "Origin": self.host,
        }
        self.categories = [
            {"type_id": tid, "type_name": name}
            for tid, name in _KIND_NAMES
        ]
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        # extend 可覆盖 API 域名, 例如 extend="https://kanju.ai"
        ext = (extend or "").strip().rstrip("/")
        if ext.startswith("http"):
            self.host = ext
            self.headers["Referer"] = ext + "/"
            self.headers["Origin"] = ext
            self.session.headers.update(self.headers)

    # ---------- 签名与请求 ----------
    def _sign(self, method, path, params=None):
        qs = urlencode(params or {})
        pq = path + ("?" + qs if qs else "")
        ts = str(int(time.time() * 1000))
        nonce = os.urandom(16).hex()
        msg = method + "\n" + pq + "\n" + ts + "\n" + nonce
        sig = hmac.new(self.key.encode(), msg.encode(), hashlib.sha256).hexdigest()
        return pq, ts, nonce, sig

    def _api(self, method, path, params=None, body=None):
        pq, ts, nonce, sig = self._sign(method, path, params)
        url = self.host + pq
        headers = {
            "Accept": "application/json",
            "x-ai-movie-timestamp": ts,
            "x-ai-movie-nonce": nonce,
            "x-ai-movie-signature": sig,
        }
        try:
            if body is None:
                r = self.session.get(url, headers=headers, timeout=20,
                                     verify=False, proxies=self.session.proxies or None)
            else:
                headers["Content-Type"] = "application/json"
                r = self.session.post(url, headers=headers, data=json.dumps(body),
                                      timeout=20, verify=False,
                                      proxies=self.session.proxies or None)
            if r.status_code != 200:
                return {}
            return r.json()
        except Exception:
            return {}

    # ---------- 工具 ----------
    def _cover(self, url):
        url = urljoin(self.host + "/", url or "")
        try:
            # gimg0.baidu.com/gimg/app=2001&n=0&...&src=img.baipiaozhe.com/xxx
            # （参数可能位于 path 或 query，统一用正则提取 src 还原源站图）
            if "gimg" in urlparse(url).netloc and "/gimg" in urlparse(url).path:
                m = re.search(r"(?:[?&/]|^)src=([^&\"'\s]+)", url)
                if m:
                    src = m.group(1)
                    if src and not src.startswith("http"):
                        return "https://" + src
        except Exception:
            pass
        return url

    def _is_media(self, url):
        return urlparse(url).scheme in ("http", "https") and bool(
            re.search(r"\.(?:m3u8|mp4)(?:$|[?#])", urlparse(url).path, re.I))

    def _probe_media(self, url):
        """真直链门禁: 只放行实测可拉的媒体地址（m3u8 必须含 #EXTM3U）。"""
        if not self._is_media(url):
            return ""
        try:
            hdrs = {**self.headers, "Range": "bytes=0-4095", "Accept": "*/*"}
            r = self.session.get(url, headers=hdrs, timeout=15, verify=False,
                                 stream=True, proxies=self.session.proxies or None)
            data = next(r.iter_content(4096), b"")
            if not r.ok:
                return ""
            ctype = (r.headers.get("Content-Type") or "").lower()
            final = r.url
            if re.search(r"\.m3u8(?:$|[?#])", urlparse(final).path, re.I):
                return final if b"#EXTM3U" in data else ""
            if "video/" in ctype or data[4:12].find(b"ftyp") >= 0:
                return final
            return ""
        except Exception:
            return ""

    def _item(self, c):
        vid = str(c.get("id") or c.get("variant_id") or "")
        name = c.get("title") or c.get("normalized_title") or vid
        return {
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": self._cover(c.get("poster_url") or ""),
            "vod_remarks": c.get("remarks") or "",
        }

    # ---------- 六接口 ----------
    def homeContent(self, filter):
        return {"class": self.categories, "list": self._home_list(20), "filters": {}}

    def homeVideoContent(self):
        return {"list": self._home_list(60)}

    def _home_list(self, cap):
        d = self._api("GET", "/v1/feed/home")
        out, seen = [], set()
        for sec in d.get("sections") or []:
            for c in sec.get("cards") or []:
                vid = str(c.get("id") or "")
                if not vid or vid in seen:
                    continue
                seen.add(vid)
                out.append(self._item(c))
                if len(out) >= cap:
                    return out
        return out

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if str(pg).isdigit() else 1
        d = self._api("GET", "/v1/browse/catalog",
                      {"kind": str(tid), "page": str(page), "limit": "20"})
        pag = d.get("pagination") or {}
        cards = d.get("cards") or []
        total = int(pag.get("total") or 0)
        limit = int(pag.get("limit") or 20)
        pagecount = page
        if total and limit:
            pagecount = (total + limit - 1) // limit
        elif pag.get("has_more"):
            pagecount = page + 1
        return {
            "page": page,
            "pagecount": pagecount,
            "limit": limit,
            "total": total,
            "list": [self._item(c) for c in cards],
        }

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        d = self._api("GET", "/v1/suggest", {"query": str(key), "limit": "20"})
        out, seen = [], set()
        for s in d.get("suggestions") or []:
            t = s.get("target") or {}
            vid = t.get("variant_id")
            if not vid or vid in seen:
                continue
            seen.add(vid)
            out.append({
                "vod_id": vid,
                "vod_name": s.get("label") or t.get("title") or vid,
                "vod_pic": self._cover(t.get("poster_url") or ""),
                "vod_remarks": s.get("subtitle") or "",
            })
            if len(out) >= 20:
                break
        return {"list": out, "page": page}

    def detailContent(self, ids):
        out = []
        for vid in ids if isinstance(ids, list) else [ids]:
            vid = str(vid).strip()
            if not vid:
                continue
            d = self._api("GET", "/v1/catalog/" + quote(vid))
            if not d:
                continue
            name = d.get("title") or d.get("normalized_title") or vid
            urls = []
            seen = set()
            for e in self._episodes(vid):
                tok = e.get("token") or e.get("id") or ""
                label = (e.get("title") or "").strip()
                if not label:
                    label = "第%s集" % e.get("sort_number", "")
                label = label.replace("#", " ").replace("$", " ")
                if not tok or tok in seen:
                    continue
                seen.add(tok)
                urls.append(label + "$" + tok)
            genres = " ".join(d.get("genres") or [])
            out.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": self._cover(d.get("poster_url") or ""),
                "vod_remarks": d.get("remarks") or "",
                "vod_year": str(d.get("year") or ""),
                "vod_area": d.get("area") or "",
                "vod_type": genres[:80],
                "vod_actor": " ".join(d.get("actors") or [])[:200],
                "vod_director": " ".join(d.get("directors") or [])[:60],
                "vod_content": (d.get("description") or "")[:800],
                "vod_play_from": "看剧AI" if urls else "",
                "vod_play_url": "#".join(urls),
            })
        return {"list": out}

    def _episodes(self, vid):
        eps, offset = [], 0
        for _ in range(12):
            d = self._api("GET", "/v1/catalog/" + quote(vid) + "/episodes",
                          {"limit": "48", "offset": str(offset)})
            items = d.get("episodes") or []
            eps.extend(items)
            pag = d.get("episode_pagination") or {}
            if not pag.get("has_more") or not items:
                break
            offset = offset + len(items)
        return eps

    def playerContent(self, flag, id, vipFlags):
        tok = str(id or "").strip()
        if not tok:
            return {"parse": 1, "url": ""}
        d = self._api("GET", "/v1/playback/resolve/" + quote(tok))
        picks = []
        for lo in d.get("line_options") or []:
            u = str(lo.get("url") or "")
            kind = str(lo.get("url_kind") or "")
            # 官方 R 等票据线路需登录（resolve-line 401），跳过
            if kind == "resolve_ticket" or u.startswith("resolve://"):
                continue
            if u.startswith("http") and self._is_media(u):
                picks.append(u)
        url = ""
        for u in picks[:5]:
            url = self._probe_media(u)
            if url:
                break
        return {
            "parse": 0 if url else 1,
            "url": url,
            "header": json.dumps(self.headers),
        }