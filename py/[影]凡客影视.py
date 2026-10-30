#!/usr/bin/python
# -*- coding: utf-8 -*-
import base64
import json
import random
import re
import time
from urllib.parse import urljoin
import requests
from base.spider import Spider


def _tbl():
    p = q = 1
    sb = [0] * 256
    while True:
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0)
        q ^= q << 1
        q ^= q << 2
        q ^= q << 4
        q &= 0xFF
        if q & 0x80:
            q ^= 0x09
        x = q ^ ((q << 1 | q >> 7) & 0xFF) ^ ((q << 2 | q >> 6) & 0xFF) ^ ((q << 3 | q >> 5) & 0xFF) ^ ((q << 4 | q >> 4) & 0xFF)
        sb[p] = (x ^ 0x63) & 0xFF
        if p == 1:
            break
    sb[0] = 0x63
    ib = [0] * 256
    for i, v in enumerate(sb):
        ib[v] = i
    return sb, ib


_SB, _IB = _tbl()


def _xt(a):
    return ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else (a << 1) & 0xFF


def _mul(a, b):
    r = 0
    while b:
        if b & 1:
            r ^= a
        a = _xt(a)
        b >>= 1
    return r & 0xFF


def _keys(k):
    w = [list(k[i * 4:i * 4 + 4]) for i in range(4)]
    rc = 1
    for i in range(4, 44):
        t = list(w[i - 1])
        if i % 4 == 0:
            t = t[1:] + t[:1]
            t = [_SB[x] for x in t]
            t[0] ^= rc
            rc = _xt(rc)
        w.append([w[i - 4][j] ^ t[j] for j in range(4)])
    return w


def _ark(s, w, r):
    for c in range(4):
        for j in range(4):
            s[c * 4 + j] ^= w[r * 4 + c][j]


def _eblk(b, w):
    s = list(b)
    _ark(s, w, 0)
    for rnd in range(1, 11):
        s = [_SB[x] for x in s]
        s = [s[4 * (((i // 4) + (i % 4)) % 4) + (i % 4)] for i in range(16)]
        if rnd != 10:
            n = [0] * 16
            for c in range(4):
                a = s[c * 4:c * 4 + 4]
                n[c * 4] = _xt(a[0]) ^ _mul(a[1], 3) ^ a[2] ^ a[3]
                n[c * 4 + 1] = a[0] ^ _xt(a[1]) ^ _mul(a[2], 3) ^ a[3]
                n[c * 4 + 2] = a[0] ^ a[1] ^ _xt(a[2]) ^ _mul(a[3], 3)
                n[c * 4 + 3] = _mul(a[0], 3) ^ a[1] ^ a[2] ^ _xt(a[3])
            s = n
        _ark(s, w, rnd)
    return bytes(s)


def _dblk(b, w):
    s = list(b)
    _ark(s, w, 10)
    for rnd in range(9, -1, -1):
        s = [s[4 * (((i // 4) - (i % 4)) % 4) + (i % 4)] for i in range(16)]
        s = [_IB[x] for x in s]
        _ark(s, w, rnd)
        if rnd:
            n = [0] * 16
            for c in range(4):
                a = s[c * 4:c * 4 + 4]
                n[c * 4] = _mul(a[0], 14) ^ _mul(a[1], 11) ^ _mul(a[2], 13) ^ _mul(a[3], 9)
                n[c * 4 + 1] = _mul(a[0], 9) ^ _mul(a[1], 14) ^ _mul(a[2], 11) ^ _mul(a[3], 13)
                n[c * 4 + 2] = _mul(a[0], 13) ^ _mul(a[1], 9) ^ _mul(a[2], 14) ^ _mul(a[3], 11)
                n[c * 4 + 3] = _mul(a[0], 11) ^ _mul(a[1], 13) ^ _mul(a[2], 9) ^ _mul(a[3], 14)
            s = n
    return bytes(s)


def _aes_enc(d, k):
    n = 16 - len(d) % 16
    d = d + bytes([n]) * n
    try:
        from Crypto.Cipher import AES
        return AES.new(k, AES.MODE_ECB).encrypt(d)
    except Exception:
        w = _keys(k)
        return b"".join(_eblk(d[i:i + 16], w) for i in range(0, len(d), 16))


def _aes_dec(d, k):
    try:
        from Crypto.Cipher import AES
        o = AES.new(k, AES.MODE_ECB).decrypt(d)
    except Exception:
        w = _keys(k)
        o = b"".join(_dblk(d[i:i + 16], w) for i in range(0, len(d), 16))
    return o[:-o[-1]] if o and 0 < o[-1] <= 16 else o


CLASSES = [("6", "电影", "movie"), ("5", "电视剧", "tv"), ("9", "短剧", "short_tv"), ("7", "动漫", "comic"), ("4", "综艺", "zy"), ("8", "纪录片", "jlp"), ("11", "电影解说", "js")]
TAGS = {
    "6": [("喜剧片", "299"), ("爱情片", "302"), ("动作片", "308"), ("剧情片", "313"), ("惊悚片", "304"), ("犯罪片", "318"), ("恐怖片", "319"), ("冒险片", "320"), ("科幻片", "327"), ("奇幻片", "330"), ("悬疑片", "338"), ("战争片", "337"), ("灾难片", "334"), ("动画电影", "333"), ("网络电影", "329"), ("歌舞片", "357"), ("经典片", "361"), ("同性片", "355"), ("男男电影", "297"), ("百合电影", "354")],
    "5": [("欧美剧", "295"), ("国产剧", "296"), ("韩剧", "325"), ("日剧", "312"), ("泰剧", "311"), ("港剧", "324"), ("台剧", "314"), ("新马剧", "342"), ("其他剧", "310"), ("男男", "345"), ("百合", "315")],
    "9": [("逆袭", "300"), ("甜宠", "301"), ("重生", "309"), ("穿越", "321"), ("都市", "322"), ("虐恋", "331"), ("民国", "332"), ("架空", "335"), ("现代", "339"), ("强者", "340"), ("职场", "341"), ("萌宝", "344"), ("年代", "346"), ("复仇", "347"), ("古代", "348"), ("校园", "349"), ("宫廷", "352"), ("乡村", "353"), ("神豪", "360"), ("古装", "372")],
    "7": [("日本动漫", "307"), ("国产动漫", "326"), ("欧美动漫", "323"), ("港台动漫", "362"), ("韩国动漫", "369"), ("男男动漫", "343"), ("百合动漫", "371"), ("耽美", "317"), ("美少女", "366"), ("其他动漫", "359")],
    "4": [("国产综艺", "316"), ("欧美综艺", "303"), ("韩国综艺", "328"), ("港台综艺", "336"), ("日本综艺", "356"), ("新马泰综艺", "364"), ("耽美综艺", "370"), ("电视直播", "358"), ("其他综艺", "365")],
    "8": [("纪录片", "306")],
    "11": [("电影解说", "305"), ("流行", "298")],
}
LANGS = [("国语", "1"), ("粤语", "2"), ("英语", "3"), ("韩语", "4"), ("日语", "5"), ("法语", "6"), ("泰语", "7"), ("其他语", "8")]
ORDERS = [("最新", "new"), ("最近更新", "last_update"), ("最热", "hot")]


class Spider(Spider):
    def getName(self):
        return "凡客影视"

    def init(self, extend=""):
        self.name = "凡客影视"
        self.host = "https://fktv.me"
        self.api = self.host + "/ysapi"
        self.key = b"9ed1a661a6ab787a"
        self.ua = "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        self.headers = {"User-Agent": self.ua, "Referer": self.host + "/", "Origin": self.host, "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9"}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.did = "".join(random.choice("abcdef0123456789") for _ in range(32))
        self.classes = [{"type_id": c[0], "type_name": c[1]} for c in CLASSES]
        self.pos = {c[0]: c[2] for c in CLASSES}
        self.filters = {}
        for c in CLASSES:
            self.filters[c[0]] = [
                {"key": "tag_id", "name": "类型", "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for n, v in TAGS.get(c[0], [])]},
                {"key": "year", "name": "年份", "value": [{"n": "全部", "v": ""}] + [{"n": str(y), "v": str(y)} for y in range(2026, 2016, -1)]},
                {"key": "language", "name": "语言", "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for n, v in LANGS]},
                {"key": "order", "name": "排序", "value": [{"n": n, "v": v} for n, v in ORDERS]},
            ]

    def _post(self, ep, data=None):
        body = {"deviceId": self.did, "token": "", "domain": self.host.split("//")[-1], "referer": "", "user_agent": self.ua, "shareCode": "", "channel": "", "ip": "", "data": data or {}}
        h = dict(self.headers)
        h.update({"version": "1.0", "deviceType": "pc", "time": time.strftime("%Y-%m-%d %H:%M:%S"), "shareCode": "", "channel": "", "ip": "", "Content-Type": "application/octet-stream"})
        try:
            pl = base64.b64encode(_aes_enc(json.dumps(body, ensure_ascii=False).encode("utf-8"), self.key))
            r = self.session.post(self.api + "/" + ep.lstrip("/"), data=pl, headers=h, timeout=20)
            t = (r.text or "").strip()
            if not t:
                return None
            o = json.loads(t) if t[0] in "{[" else json.loads(_aes_dec(base64.b64decode(t), self.key).decode("utf-8", "ignore"))
            if o.get("status") != "y":
                print("[%s] 错误: %s 接口返回 %s" % (self.name, ep, o.get("error")))
                return None
            return o.get("data")
        except Exception as e:
            print("[%s] 错误: %s 请求失败 - %s" % (self.name, ep, e))
            return None

    def _ext(self, extend):
        if isinstance(extend, dict):
            return extend
        if isinstance(extend, str) and extend.strip().startswith("{"):
            try:
                return json.loads(extend)
            except Exception:
                return {}
        return {}

    def _pic(self, x):
        for k in ("img_y_source", "img_x_source", "img_y", "img_x", "img"):
            u = (x.get(k) or "").strip()
            if u and not u.endswith(".bnc"):
                return u if u.startswith("http") else urljoin(self.host + "/", u)
        return ""

    def _clean(self, t):
        return re.sub(r"[\s$#]+", " ", re.sub(r"<[^>]+>", " ", str(t or ""))).strip()

    def _vod(self, x):
        sc = (x.get("score") or "").strip()
        rm = ("%s分" % sc) if sc and sc not in ("0.00", "0") else (x.get("release_at") or "")
        return {"vod_id": x.get("id") or "", "vod_name": self._clean(x.get("name")), "vod_pic": self._pic(x), "vod_year": x.get("release_at") or "", "vod_remarks": rm}

    def _list(self, items):
        out = []
        seen = set()
        for x in items or []:
            try:
                vid = x.get("id")
                if not vid or vid in seen or not x.get("name"):
                    continue
                seen.add(vid)
                out.append(self._vod(x))
            except Exception:
                continue
        return out

    def _page(self, tid, pg, ext, kw=""):
        try:
            pg = int(str(pg) or "1")
        except Exception:
            pg = 1
        pg = max(pg, 1)
        d = {"order": (ext.get("order") or "new").strip() or "new", "page": pg, "page_size": 30}
        if kw:
            d["keywords"] = kw
        tid = str(tid or "")
        if tid:
            d["cat_id"] = tid
            if self.pos.get(tid):
                d["position"] = self.pos[tid]
        for k in ("tag_id", "year", "language", "area"):
            v = str(ext.get(k) or "").strip()
            if v:
                d[k] = v
        r = self._post("movie/search", d) or {}
        vl = self._list(r.get("data"))
        try:
            pc = int(r.get("last_page") or 1)
        except Exception:
            pc = pg
        try:
            lm = int(r.get("page_size") or 30)
        except Exception:
            lm = 30
        try:
            tt = int(r.get("total") or len(vl))
        except Exception:
            tt = len(vl)
        print("[%s] 列表 tid=%s pg=%s 命中 %d 条 共 %d 页" % (self.name, tid or kw, pg, len(vl), pc))
        return {"list": vl, "page": pg, "pagecount": max(pc, pg), "limit": lm, "total": tt}

    def homeContent(self, filter):
        return {"class": self.classes, "filters": self.filters, "list": self._list(self._post("movie/rank", {}))}

    def homeVideoContent(self):
        return {"list": self._list(self._post("movie/rank", {}))}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            return self._page(tid, pg, self._ext(extend))
        except Exception as e:
            print("[%s] 错误: 分类爬取失败 - %s" % (self.name, e))
            return self._empty(pg)

    def _empty(self, pg):
        try:
            n = max(int(str(pg) or "1"), 1)
        except Exception:
            n = 1
        return {"list": [], "page": n, "pagecount": n, "limit": 30, "total": 0}

    def searchContent(self, key, quick, pg="1"):
        try:
            return self._page("", pg, {}, kw=str(key or "").strip())
        except Exception as e:
            print("[%s] 错误: 搜索失败 - %s" % (self.name, e))
            return self._empty(pg)

    def detailContent(self, ids):
        try:
            vid = str(ids[0]).split("|")[0]
            d = self._post("movie/detail", {"id": vid})
            if not d:
                return {"list": []}
            eps = [x for x in (d.get("links") or []) if x.get("id")]
            if not eps and d.get("link_id"):
                eps = [{"id": d.get("link_id"), "name": "正片"}]
            lines = [x for x in (d.get("play_links") or []) if x.get("m3u8_url") or x.get("id")]
            if not lines:
                lines = [{"id": "line1", "name": "线路1"}]
            froms, urls = [], []
            for i, ln in enumerate(lines):
                lid = ln.get("id") or ("line%d" % (i + 1))
                froms.append(self._clean(ln.get("name")) or lid)
                urls.append("#".join("%s$%s|%s|%s" % (self._clean(e.get("name")) or str(j + 1), vid, e.get("id"), lid) for j, e in enumerate(eps)))
            print("[%s] 详情 %s 线路 %d 剧集 %d" % (self.name, self._clean(d.get("name")), len(froms), len(eps)))
            return {"list": [{
                "vod_id": vid,
                "vod_name": self._clean(d.get("name")),
                "vod_pic": self._pic(d),
                "type_name": self._clean(d.get("categories") or d.get("child_title")),
                "vod_year": d.get("release_at") or "",
                "vod_area": self._clean(d.get("area")),
                "vod_lang": self._clean(d.get("language")),
                "vod_remarks": ("共%d集" % len(eps)) if len(eps) > 1 else (("%s分" % d.get("score")) if d.get("score") else ""),
                "vod_actor": self._clean(d.get("actor")),
                "vod_director": self._clean(d.get("director")),
                "vod_content": self._clean(d.get("description")),
                "vod_play_from": "$$$".join(froms),
                "vod_play_url": "$$$".join(urls),
            }]}
        except Exception as e:
            print("[%s] 错误: 详情解析失败 - %s" % (self.name, e))
            return {"list": []}

    def _probe_media(self, u, hdr):
        if not u or not u.startswith("http"):
            return False
        try:
            r = self.session.get(u, headers=hdr, timeout=15, stream=True)
            if r.status_code != 200:
                r.close()
                return False
            ct = (r.headers.get("Content-Type") or "").lower()
            head = next(r.iter_content(256), b"") or b""
            r.close()
            if "#EXTM3U" in head.decode("utf-8", "ignore"):
                return True
            return any(k in ct for k in ("video", "mp4", "mpegurl", "octet-stream"))
        except Exception:
            return False

    def playerContent(self, flag, id, vipFlags=None):
        hdr = {"User-Agent": self.ua, "Referer": self.host + "/", "Origin": self.host}
        try:
            p = str(id or "").split("|")
            if p[0].startswith("http"):
                return {"parse": 0, "playUrl": "", "url": p[0], "header": hdr}
            vid = p[0]
            lid = p[1] if len(p) > 1 else ""
            line = p[2] if len(p) > 2 else ""
            d = self._post("movie/detail", {"id": vid, "link_id": lid} if lid else {"id": vid}) or {}
            pls = d.get("play_links") or []
            pick = next((x for x in pls if x.get("id") == line), None) or next((x for x in pls if self._clean(x.get("name")) == str(flag or "")), None)
            cand = []
            for x in ([pick] if pick else []) + pls:
                for k in ("m3u8_url", "hevc_m3u8_url", "preview_m3u8_url"):
                    v = (x or {}).get(k) or ""
                    if v and v not in cand:
                        cand.append(v)
            if d.get("m3u8_url_source"):
                cand.append(d["m3u8_url_source"])
            u = ""
            for c in cand:
                c = c if c.startswith("http") else urljoin(self.host + "/", c)
                if self._probe_media(c, hdr):
                    u = c
                    break
            if not u and cand:
                u = cand[0] if cand[0].startswith("http") else urljoin(self.host + "/", cand[0])
            print("[%s] 播放 %s -> %s" % (self.name, flag, u[:60]))
            return {"parse": 0, "playUrl": "", "url": u, "header": hdr}
        except Exception as e:
            print("[%s] 错误: 播放解析失败 - %s" % (self.name, e))
            return {"parse": 0, "playUrl": "", "url": "", "header": hdr}

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(m3u8|mp4|flv|mkv|avi|ts)(\?|$)", str(url or "")))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [200, "text/plain", ""]

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass