# -*- coding: utf-8 -*-
#!/usr/bin/python
"""
北斗影院 TVBox / T4 Python Spider
修订版：
- 保留原站点的 /v/、/p/ 路由
- 完整解析多线路播放列表
- 支持 order/type/area/year 多维筛选
- 列表/详情/搜索分页字段完整
- 播放解析支持 playerFrame、相对 URL、转义 URL、常见 JS/JSON 播放字段及多层 iframe
- 不伪造最终媒体地址：动态播放器无法从静态 HTML 得到媒体地址时，返回正确播放器入口给壳端
"""

import re
import json
import html as html_lib
import base64
import time
import threading
from urllib.parse import quote, urljoin, urlparse, unquote

try:
    import requests
except ImportError:
    requests = None

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def __init__(self):
            self.extend = {}
        def init(self, extend=""):
            self.extend = extend


class Spider(BaseSpider):
    site_name = "北斗影院"

    DOMAIN_CANDIDATES = [
        "http://www.bdjmcc.com",
        "https://www.bdjmcc.com",
        "http://bdjmcc.com",
        "https://bdjmcc.com",
    ]

    # 当前站点实际导航
    categories = [
        {"type_id": "A051pCM47kBg2", "type_name": "连续剧"},
        {"type_id": "A1sQHJp3ggh3P", "type_name": "电影"},
        {"type_id": "A2yIcGx03608i", "type_name": "动漫"},
        {"type_id": "A1U43X24bwf2t", "type_name": "综艺"},
    ]

    # 站点没有 /list/tid/order/type/area/year 多维路由。
    # 子类是独立 type_id（国产剧/喜剧等），筛选「类型」应切换到对应 tid。
    SUBTYPE_DRAMA = [
        ("", "全部"),
        ("A0hLbxS3mdi9Z", "国产剧"),
        ("A3acP230qrYEa", "港台剧"),
        ("A26NqI80kYj9l", "欧美剧"),
        ("A0IzOAf2AnMYc", "韩国剧"),
        ("A3CGBFG0fQSp3", "日本剧"),
        ("A1Orj7n0sv4s5", "泰国剧"),
        ("A3yycoq1C7ZVU", "其他剧"),
    ]
    SUBTYPE_MOVIE = [
        ("", "全部"),
        ("A2ZwOUA4eaYwf", "喜剧"),
        ("A0mXwMh43XY4p", "动作"),
        ("A3Meq3k0Tezgj", "爱情"),
        ("A4SXB0s2ndOVj", "恐怖"),
        ("A2f8itP1Ia8Rv", "犯罪"),
        ("A1AuA9U0K1cOR", "剧情"),
        ("A44AxE519ugB7", "奇幻"),
        ("A2GmV6c1gqj6w", "战争"),
        ("A0TO2z91gaOAS", "悬疑"),
        ("A4I8WCO4HYvub", "动画"),
        ("A1ZGNwH3MCXg7", "科幻"),
        ("A2Uk44v27gayS", "其他片"),
    ]
    SUBTYPE_ANIME = [
        ("", "全部"),
        ("A2BaAhN0y27Zr", "国漫"),
        ("A0OBiZu0aFUwF", "日漫"),
        ("A3HSVeV2PEdwr", "其他动漫"),
    ]
    SUBTYPE_VARIETY = [
        ("", "全部"),
        ("A1jf2kl0SLzeU", "国产综艺"),
        ("A4gUjzB24vEsg", "港澳综艺"),
        ("A1nDwua2qYC8K", "日韩综艺"),
        ("A2t6Hri39mDKQ", "其他综艺"),
    ]


    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.extend = {}
        self.base_url = self.DOMAIN_CANDIDATES[0]
        self.session = None
        self.header = {}
        self._cache = {}          # url -> (timestamp, text)
        self._cache_ttl = 30.0
        self._last_request = {}
        self._request_gap = 1.2
        self._request_lock = threading.Lock()
        self._play_diag = []
        # T4 在解析失败时可能短时间重复调用 playerContent；
        # 缓存最终结果/失败结果，避免同一个播放页被反复请求。
        self._play_result_cache = {}
        self._play_result_ttl = 45.0
        self._play_failure_cache = {}
        self._play_failure_ttl = 20.0
        self._play_cache_lock = threading.Lock()

    # ------------------------------------------------------------------
    # 基础
    # ------------------------------------------------------------------

    def init(self, extend=""):
        self.extend = extend

        seed = ""
        if isinstance(extend, dict):
            seed = str(extend.get("siteUrl") or extend.get("host") or "").strip()
        elif isinstance(extend, str):
            s = extend.strip()
            if s.startswith("http"):
                seed = s

        self.base_url = seed.rstrip("/") if seed else self.DOMAIN_CANDIDATES[0]

        # 关键：站点桌面 UA 下 /p/ 播放页不输出 playerFrame，
        # 只有移动 UA 才嵌入第三方播放器（langfeng888 等）。
        self.header = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/16.6 Mobile/15E148 Safari/604.1"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                      "image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.base_url + "/",
        }

        # 优先 curl_cffi；播放器域名对 TLS 指纹敏感。
        # 注意：impersonate chrome 与移动 UA 混用时，仍以 header UA 为准。
        if cffi_requests:
            try:
                self.session = cffi_requests.Session(impersonate="chrome122")
                self.session.headers.update(self.header)
            except Exception:
                self.session = None
        if self.session is None and requests:
            try:
                self.session = requests.Session()
                self.session.headers.update(self.header)
            except Exception:
                self.session = None

    def getName(self):
        return self.site_name

    def getDependence(self, *args):
        return ""

    def manualVideoCheck(self):
        return False

    def isVideoFormat(self, url):
        u = str(url or "").lower()
        if any(
            x in u
            for x in (
                ".m3u8", ".mp4", ".mkv", ".flv", ".ts",
                ".mov", ".webm", ".m4v"
            )
        ):
            return True
        # 抖音/头条等 CDN 直链常无扩展名，但路径含 video/tos 或 douyinvod
        if re.search(
            r'(?:douyinvod|byteicdn|byteimg|tos-cn-v-|ixigua|v\d+-show\.)',
            u,
        ):
            return True
        if "/video/tos/" in u or "/media/" in u:
            return True
        return False

    def localProxy(self, param, *args):
        return [404, "text/plain", ""]

    def _fix(self, u, base=None):
        if not u:
            return ""
        u = html_lib.unescape(str(u)).strip()
        u = u.replace("\\/", "/").replace("\\u0026", "&")
        base = (base or self.base_url).strip()
        parsed = urlparse(base)
        origin = ""
        if parsed.scheme and parsed.netloc:
            origin = parsed.scheme + "://" + parsed.netloc

        if u.startswith("//"):
            return (parsed.scheme or "https") + ":" + u
        if u.startswith("http://") or u.startswith("https://"):
            return u
        if u.startswith("/"):
            return (origin or self.base_url.rstrip("/")) + u
        return urljoin(base if base.endswith("/") else base + "/", u)

    def _clean(self, s):
        if not s:
            return ""
        s = html_lib.unescape(str(s))
        s = re.sub(r"<[^>]+>", "", s)
        return re.sub(r"\s+", " ", s).strip()

    def _json_obj(self, value):
        if isinstance(value, dict):
            return value
        if not isinstance(value, str):
            return {}
        try:
            return json.loads(value)
        except Exception:
            pass
        return {}

    # ------------------------------------------------------------------
    # 请求
    # ------------------------------------------------------------------

    def _candidate_urls(self, url):
        """低频模式下只返回当前目标，避免一次失败触发多域名连打。
        第三方播放器/CDN 永远保持原域名；站点入口由 init() 指定。
        """
        if not url:
            return []
        return [url]

    def _classify_http_failure(self, status, body_len=0):
        """返回可读诊断：反爬/服务端异常/空响应/未知。"""
        try:
            code = int(status)
        except Exception:
            code = 0
        if code in (401, 403):
            return "可能是访问控制/反爬或鉴权失败"
        if code == 429:
            return "疑似限流/请求过频"
        if 500 <= code <= 599:
            return "服务端5xx异常，可能是临时拦截或上游异常"
        if code == 200 and not body_len:
            return "HTTP 200 但响应为空，可能是播放器风控/异常响应"
        return "HTTP请求失败"

    def _play_log(self, level, message, **extra):
        try:
            item = {"level": level, "message": message, **extra}
            self._play_diag.append(item)
            if len(self._play_diag) > 80:
                self._play_diag = self._play_diag[-80:]
            print("[北斗播放][%s] %s %s" % (
                level, message, json.dumps(extra, ensure_ascii=False)))
        except Exception:
            pass

    def _throttle(self, target):
        try:
            host = (urlparse(target).netloc or "").lower()
            if not host:
                return
            with self._request_lock:
                now = time.monotonic()
                wait = self._request_gap - (now - self._last_request.get(host, 0.0))
                if wait > 0:
                    time.sleep(wait)
                    now = time.monotonic()
                self._last_request[host] = now
        except Exception:
            pass

    def _cache_get(self, target):
        try:
            item = self._cache.get(target)
            if not item:
                return ""
            ts, text = item
            if time.monotonic() - ts <= self._cache_ttl:
                self._play_log("CACHE", "命中短期缓存", url=target)
                return text
            self._cache.pop(target, None)
        except Exception:
            pass
        return ""

    def _cache_put(self, target, text):
        try:
            self._cache[target] = (time.monotonic(), text)
        except Exception:
            pass

    def _request_cache_key(self, method, url, data=None):
        """请求缓存键必须包含方法和参数，避免不同播放 token 命中同一缓存。"""
        try:
            payload = json.dumps(data or {}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            payload = str(data or "")
        return "%s %s %s" % (str(method or "GET").upper(), url, payload)

    def _post(self, url, data=None, referer=None, timeout=15):
        if not url:
            return ""
        cache_key = self._request_cache_key("POST", url, data)
        cached = self._cache_get(cache_key)
        if cached:
            return cached
        self._throttle(url)
        h = dict(self.header)
        req_referer = referer or self.header.get("Referer") or (self.base_url + "/")
        h["Referer"] = req_referer
        try:
            thost = (urlparse(url).netloc or "").lower()
            rhost = (urlparse(req_referer).netloc or "").lower()
            if thost and rhost and thost != rhost:
                h.setdefault("Origin", "%s://%s" % (
                    urlparse(req_referer).scheme or "http", rhost))
                h.setdefault("Sec-Fetch-Site", "cross-site")
                h.setdefault("Sec-Fetch-Mode", "cors")
                h.setdefault("Sec-Fetch-Dest", "empty")
        except Exception:
            pass
        payload = dict(data) if isinstance(data, dict) else {}
        send_json = bool(payload.pop("__bd_json__", False))
        if send_json:
            h["Content-Type"] = "application/json; charset=UTF-8"
        self._play_log("REQUEST", "POST 播放接口", url=url, timeout=timeout, json=send_json)
        if not self.session:
            self._play_log("REQUEST_FAIL", "没有可用 Session", url=url)
            return ""
        try:
            if send_json:
                r = self.session.post(url, json=payload, headers=h, timeout=timeout,
                                      verify=False, allow_redirects=True)
            else:
                r = self.session.post(url, data=payload, headers=h, timeout=timeout,
                                      verify=False, allow_redirects=True)
            status = int(getattr(r, "status_code", 0) or 0)
            text = getattr(r, "text", "") or ""
            final_url = str(getattr(r, "url", "") or "")
            if final_url and final_url != url:
                self._play_log("REDIRECT", "POST发生跳转", from_url=url, to_url=final_url, status=status)
            if status == 200 and text.strip():
                self._cache_put(cache_key, text)
                self._play_log("RESPONSE", "POST 成功", url=url, status=status, length=len(text))
                return text
            if status in (403, 429):
                self._play_log("BLOCK", "疑似反爬/限流", url=url, status=status, length=len(text))
            elif status >= 500:
                self._play_log("HTTP", "服务器 5xx，偏向上游服务异常", url=url, status=status, length=len(text))
            elif status == 200:
                self._play_log("EMPTY", "HTTP 200 但响应为空", url=url)
            else:
                self._play_log("HTTP", "POST 返回非预期状态", url=url, status=status, length=len(text))
        except Exception as exc:
            msg = str(exc)
            self._play_log("TIMEOUT" if ("timeout" in msg.lower() or "timed out" in msg.lower()) else "REQUEST_FAIL",
                           "POST 请求异常", url=url, error=msg[:180])
        return ""

    def _get(self, url, referer=None, timeout=15):
        if not url:
            return ""
        for target in self._candidate_urls(url):
            cached = self._cache_get(target)
            if cached:
                return cached
            self._throttle(target)
            h = dict(self.header)
            req_referer = referer or self.header.get("Referer") or (self.base_url + "/")
            h["Referer"] = req_referer
            # 第三方播放器属于正常的跨站 iframe 请求：保留来源上下文，
            # 但不做无限重试/UA轮换等反爬规避。
            try:
                thost = (urlparse(target).netloc or "").lower()
                rhost = (urlparse(req_referer).netloc or "").lower()
                if thost and rhost and thost != rhost:
                    h.setdefault("Origin", "%s://%s" % (
                        urlparse(req_referer).scheme or "http", rhost))
                    h.setdefault("Sec-Fetch-Site", "cross-site")
                    h.setdefault("Sec-Fetch-Mode", "cors")
                    h.setdefault("Sec-Fetch-Dest", "empty")
                else:
                    h.setdefault("Sec-Fetch-Site", "same-origin")
                    h.setdefault("Sec-Fetch-Mode", "cors")
            except Exception:
                pass
            self._play_log("REQUEST", "GET 请求", url=target, referer=req_referer, timeout=timeout)
            if self.session:
                try:
                    r = self.session.get(target, headers=h, timeout=timeout,
                                         verify=False, allow_redirects=True)
                    status = int(getattr(r, "status_code", 0) or 0)
                    text = getattr(r, "text", "") or ""
                    final_url = str(getattr(r, "url", "") or "")
                    if final_url and final_url != target:
                        self._play_log("REDIRECT", "GET发生跳转", from_url=target, to_url=final_url, status=status)
                    if status == 200 and text.strip():
                        self._cache_put(target, text)
                        self._play_log("RESPONSE", "GET 成功", url=target,
                                       status=status, length=len(text))
                        return text
                    if status in (403, 429):
                        self._play_log("BLOCK", "疑似反爬/限流", url=target,
                                       status=status, length=len(text))
                    elif status >= 500:
                        self._play_log("HTTP", "服务器 5xx，偏向上游服务异常",
                                       url=target, status=status, length=len(text))
                    elif status == 200:
                        self._play_log("EMPTY", "HTTP 200 但响应为空", url=target)
                    else:
                        self._play_log("HTTP", "GET 返回非预期状态", url=target,
                                       status=status, length=len(text))
                except Exception as exc:
                    msg = str(exc)
                    self._play_log("TIMEOUT" if ("timeout" in msg.lower() or "timed out" in msg.lower()) else "REQUEST_FAIL",
                                   "GET 请求异常", url=target, error=msg[:180])
            elif self.session is None:
                try:
                    import ssl, urllib.request
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    req = urllib.request.Request(target, headers=h)
                    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                        status = int(getattr(resp, "status", 200) or 200)
                        raw = resp.read()
                    text = raw.decode("utf-8", errors="replace") if raw else ""
                    if status == 200 and text.strip():
                        self._cache_put(target, text)
                        self._play_log("RESPONSE", "urllib GET 成功", url=target,
                                       status=status, length=len(text))
                        return text
                    self._play_log("EMPTY" if not text.strip() else "HTTP",
                                   "urllib GET 无有效内容", url=target,
                                   status=status, length=len(text))
                except Exception as exc:
                    msg = str(exc)
                    self._play_log("TIMEOUT" if ("timeout" in msg.lower() or "timed out" in msg.lower()) else "REQUEST_FAIL",
                                   "urllib GET 异常", url=target, error=msg[:180])
        return ""

    # ------------------------------------------------------------------
    # 列表
    # ------------------------------------------------------------------

    def parse_video_list(self, source):
        """解析分类/首页影视卡片。

        原站列表结构改版时，不能只依赖某一种 class 或属性顺序。
        这里按“详情路由 -> 卡片标题 -> 图片 -> 备注”的优先级做多层兜底。
        """
        if not source:
            return []

        source = html_lib.unescape(str(source))
        source = source.replace("\\/", "/").replace("\\u0026", "&")
        source = source.replace("\\u002F", "/")
        result = []
        seen = set()

        def add_item(token, block, whole=""):
            token = str(token or "").strip()
            if not token or token in seen:
                return

            # 允许站点后续把 token 扩展为短横线/下划线形式。
            if not re.match(r"^[A-Za-z0-9_-]+$", token):
                return

            whole = whole or block or ""
            block = block or ""
            title = ""

            # 1. 当前 <a> 自身 title / data-title / aria-label
            for attr in ("title", "data-title", "aria-label"):
                m = re.search(
                    r'\b' + re.escape(attr) +
                    r'\s*=\s*["\']([^"\']+)["\']',
                    whole,
                    re.I,
                )
                if m:
                    title = self._clean(m.group(1))
                    if title:
                        break

            # 2. 图片 alt/title
            if not title:
                for attr in ("alt", "title"):
                    m = re.search(
                        r'\b' + re.escape(attr) +
                        r'\s*=\s*["\']([^"\']+)["\']',
                        block,
                        re.I,
                    )
                    if m:
                        title = self._clean(m.group(1))
                        if title:
                            break

            # 3. 常见标题节点
            if not title:
                m = re.search(
                    r'<(?:div|span|p|h[1-6])\b[^>]*class\s*=\s*'
                    r'["\'][^"\']*(?:title|name|vod-name|module-card-name|'
                    r'module-item-title|module-poster-item-title)[^"\']*'
                    r'["\'][^>]*>([\s\S]*?)</(?:div|span|p|h[1-6])>',
                    block,
                    re.I,
                )
                if m:
                    title = self._clean(m.group(1))

            # 4. 文本兜底
            if not title:
                txt = self._clean(block)
                # 去掉明显的按钮/状态噪声
                txt = re.sub(r'^(播放|详情|更新|HD|4K)\s*', '', txt, flags=re.I)
                if txt:
                    title = txt[:100]

            if not title:
                return

            pic = ""
            # 图片优先级：懒加载属性 > src
            for attr in (
                "data-original", "data-src", "data-lazy",
                "data-url", "data-image", "src"
            ):
                m = re.search(
                    r'\b' + re.escape(attr) +
                    r'\s*=\s*["\']([^"\']+)["\']',
                    block,
                    re.I,
                )
                if m:
                    candidate = self._fix(m.group(1))
                    if candidate and not candidate.startswith("data:image"):
                        pic = candidate
                        break

            remarks = ""
            m = re.search(
                r'class\s*=\s*["\'][^"\']*'
                r'(?:note|remarks|status|badge|fddpull-rigfht|'
                r'module-item-note|module-item-text|module-card-text)'
                r'[^"\']*["\'][^>]*>([\s\S]*?)</',
                block,
                re.I,
            )
            if m:
                remarks = self._clean(m.group(1))

            seen.add(token)
            result.append({
                "vod_id": token,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remarks,
            })

        # A. 标准 <a href="/v/TOKEN.html">...</a>
        patterns = [
            re.compile(
                r'<a\b[^>]*\bhref\s*=\s*["\']'
                r'(?:https?://[^"\']+)?/v/([A-Za-z0-9_-]+)'
                r'(?:\.html)?(?:/)?(?:[?#][^"\']*)?'
                r'["\'][^>]*>([\s\S]{0,3000}?)</a>',
                re.I,
            ),
            # B. 属性顺序/懒加载改版：data-href / data-url
            re.compile(
                r'<a\b[^>]*\b(?:data-href|data-url)\s*=\s*["\']'
                r'(?:https?://[^"\']+)?/v/([A-Za-z0-9_-]+)'
                r'(?:\.html)?(?:/)?(?:[?#][^"\']*)?'
                r'["\'][^>]*>([\s\S]{0,3000}?)</a>',
                re.I,
            ),
        ]

        for pattern in patterns:
            for m in pattern.finditer(source):
                add_item(m.group(1), m.group(2), m.group(0))

        # C. 某些主题把卡片标题放在 <a> 外部。
        #    扫描常见卡片容器中的 /v/ 链接，再从容器内部找标题/图片。
        if not result:
            container_pat = re.compile(
                r'<(?:li|div|article)\b[^>]*class\s*=\s*["\'][^"\']*'
                r'(?:module-item|module-card-item|module-poster-item|'
                r'module-card|vodlist-item|video-item|stui-vodlist__box)'
                r'[^"\']*["\'][^>]*>([\s\S]{0,6000}?)</(?:li|div|article)>',
                re.I,
            )
            for cm in container_pat.finditer(source):
                block = cm.group(1)
                vm = re.search(
                    r'(?:href|data-href|data-url)\s*=\s*["\']'
                    r'(?:https?://[^"\']+)?/v/([A-Za-z0-9_-]+)'
                    r'(?:\.html)?(?:[?#][^"\']*)?["\']',
                    block,
                    re.I,
                )
                if vm:
                    add_item(vm.group(1), block, vm.group(0))

        # D0. 任意 href/data-url 属性兜底提取 /v/ 详情链接。
        if not result:
            generic = re.compile(
                r'(?:href|data-href|data-url|data-link)\s*=\s*["\']'
                r'([^"\']*?/v/[A-Za-z0-9_-]+(?:\.html)?/?(?:[?#][^"\']*)?)["\']',
                re.I,
            )
            for gm in generic.finditer(source):
                tm = re.search(r'/v/([A-Za-z0-9_-]+)', gm.group(1), re.I)
                if tm:
                    pos = max(0, gm.start() - 1200)
                    block = source[pos:gm.end() + 2500]
                    add_item(tm.group(1), block, gm.group(0))

        # D. HTML 被脚本序列化成 JSON 时，至少从字符串中恢复 /v/TOKEN。
        #    只在常规 HTML 没解析到结果时启用，避免误把脚本中的 ID 当卡片。
        if not result:
            candidates = []
            for m in re.finditer(
                r'["\']((?:https?:)?//[^"\']+)?/v/([A-Za-z0-9_-]+)'
                r'(?:\.html)?(?:[?#][^"\']*)?["\']',
                source,
                re.I,
            ):
                token = m.group(2)
                if token not in candidates:
                    candidates.append(token)

            for token in candidates:
                # 在 token 附近取有限窗口，避免跨越整页串错标题。
                pos = source.find("/v/" + token)
                window = source[max(0, pos - 800): pos + 2200]
                add_item(token, window, window)

        return result

    # ------------------------------------------------------------------
    # 筛选
    # ------------------------------------------------------------------

    def _filter_values(self, pairs):
        return [{"n": n, "v": v} for v, n in pairs]

    def _filter_defs(self, tid=None, source=None):
        """站点无 order/area/year 路由；类型筛选切换到真实子分类 type_id。"""
        tid = str(tid or "")
        if tid == "A1sQHJp3ggh3P":
            types = self.SUBTYPE_MOVIE
        elif tid == "A2yIcGx03608i":
            types = self.SUBTYPE_ANIME
        elif tid == "A1U43X24bwf2t":
            types = self.SUBTYPE_VARIETY
        else:
            types = self.SUBTYPE_DRAMA
        return {tid: [
            {"key": "type", "name": "类型", "value": self._filter_values(types)},
        ]}

    def _extract_page_filters(self, tid, source):
        """从当前分类页的真实 /list/tid/... 链接反推各筛选项。
        路由形态由原源确认是 order/type/area/year/page；不再凭空制造选项。
        """
        if not source or not tid:
            return []
        tid_raw = str(tid).strip("/")
        tid = re.escape(tid_raw)
        links = []
        pat = re.compile(
            r'<a\b[^>]*\bhref\s*=\s*["\']([^"\']*/list/' + tid +
            r'/[^"\']+)["\'][^>]*>([\s\S]{0,300}?)</a>', re.I)
        for m in pat.finditer(source):
            href = html_lib.unescape(m.group(1))
            label = self._clean(m.group(2))
            if not label or label in ("上一页", "下一页", "首页", "尾页"):
                continue
            if "/list/" not in href:
                continue
            path = urlparse(self._fix(href, self.base_url)).path.strip("/").split("/")
            try:
                i = next(i for i, x in enumerate(path) if x == urlparse(self.base_url).path.strip("/"))
            except StopIteration:
                i = -1
            # 不依赖 origin/path 的定位，直接找 tid。
            try:
                j = path.index(tid_raw)
            except ValueError:
                continue
            rest = path[j + 1:]
            if len(rest) < 4:
                continue
            vals = rest[:5]
            vals[-1] = re.sub(r'\.html$', '', vals[-1], flags=re.I)
            if not vals[-1].isdigit():
                continue
            if len(vals) == 4:
                vals = [vals[0], vals[1], vals[2], "", vals[3]]
            links.append((label, vals))
        # select/option 形式：直接读取 name/id 对应的筛选键。
        select_items = []
        for sm in re.finditer(r'<select\b([^>]*)>([\s\S]*?)</select>', source, re.I):
            attrs, body = sm.group(1), sm.group(2)
            km = re.search(r'\b(?:name|id|data-key)=["\']([^"\']+)', attrs, re.I)
            if not km:
                continue
            raw_key = km.group(1).lower()
            key = next((k for k in ("order", "type", "area", "year") if k in raw_key), "")
            if not key:
                continue
            for om in re.finditer(r'<option\b[^>]*\bvalue=["\']([^"\']*)["\'][^>]*>([\s\S]{0,100}?)</option>', body, re.I):
                val, label = om.group(1).strip(), self._clean(om.group(2))
                if label:
                    select_items.append((key, val, label))
        if select_items:
            grouped = {}
            for key, val, label in select_items:
                grouped.setdefault(key, []).append((val, label))
            names = {"order":"排序", "type":"类型", "area":"国家/地区", "year":"年份"}
            return [{"key": key, "name": names[key], "value": self._filter_values(vals)}
                    for key, vals in grouped.items()]

        if not links:
            return []

        # 找到当前第一页的基准组合；通常最后一项是页码.
        base = None
        for label, vals in links:
            if vals[-1] == "1":
                base = vals
                if label in ("全部", "按时间", "最新", "默认"):
                    break
        if base is None:
            base = links[0][1]

        groups = {0: [], 1: [], 2: [], 3: []}
        for label, vals in links:
            if vals == base:
                continue
            diff = [i for i in range(4) if vals[i] != base[i]]
            if len(diff) == 1 and label not in ("1", "2", "3", "4", "5"):
                groups[diff[0]].append((vals[diff[0]], label))

        names = ["排序", "类型", "国家/地区", "年份"]
        keys = ["order", "type", "area", "year"]
        out = []
        for idx, key in enumerate(keys):
            items = [("", "全部")]
            seen = {""}
            for value, label in groups[idx]:
                if value in seen:
                    continue
                seen.add(value)
                items.append((value, label))
            # 动态页明确有该组才显示；否则使用兜底。
            if len(items) > 1:
                out.append({"key": key, "name": names[idx], "value": self._filter_values(items)})
        if out:
            return out
        return []

    def _parse_extend(self, extend):
        if isinstance(extend, dict):
            return extend
        if isinstance(extend, str):
            s = extend.strip()
            if not s:
                return {}
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
            out = {}
            for part in s.split("&"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    out[k.strip()] = v.strip()
            return out
        return {}

    def _build_category_url(self, tid, page, extend=None):
        """只使用 /list/{type_id}/{page}.html。

        筛选里的 type 若是真实子分类 ID，则切换 list 目标，
        不再拼不存在的 order/type/area/year 路径（会 404 再回退成同一页）。
        """
        ex = self._parse_extend(extend)
        page = int(page) if str(page).isdigit() else 1
        type_val = str(ex.get("type") or ex.get("tid") or "").strip()
        target = str(tid or "").strip("/")
        if type_val and re.match(r"^[A-Za-z0-9_-]+$", type_val):
            target = type_val
        return f"{self.base_url}/list/{target}/{page}.html"

    # ------------------------------------------------------------------
    # 首页
    # ------------------------------------------------------------------

    def homeContent(self, filter=None, *args):
        page = self._get(self.base_url + "/")
        filters = {}
        for c in self.categories:
            tid = c["type_id"]
            src = page if tid == self.categories[0]["type_id"] else self._get(f"{self.base_url}/list/{tid}/1.html")
            filters.update(self._filter_defs(tid, src))
        return {
            "class": self.categories,
            "list": self.parse_video_list(page)[:30],
            "filters": filters,
        }

    def homeVideoContent(self):
        # 推荐页没有单独 API 时直接使用首页内容
        return {
            "list": self.parse_video_list(
                self._get(self.base_url + "/")
            )[:30]
        }

    # ------------------------------------------------------------------
    # 分类
    # ------------------------------------------------------------------

    def categoryContent(self, tid, pg, filter=None, extend=None, *args):
        try:
            page = int(pg) if pg else 1
        except Exception:
            page = 1

        tid = str(tid or "").strip("/")

        # 某些 T4 壳把筛选 JSON 放在 filter 而不是 extend
        if (
            not extend
            and filter
            and filter not in (True, False, 0, 1)
        ):
            extend = filter

        url = self._build_category_url(tid, page, extend)
        source = self._get(url)
        videos = self.parse_video_list(source)

        # 只有请求本身失败才回退；真正的筛选结果为空必须保持为空，避免“筛选摆设”。
        if not source and extend:
            fallback = f"{self.base_url}/list/{tid}/{page}.html"
            source = self._get(fallback)
            videos = self.parse_video_list(source)

        pagecount = self._pagecount(source, page, videos)

        return {
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            # total 不能用 pagecount * limit 猜测。
            # 否则解析失败时会出现“24 部内容”但实际列表为空的假数据。
            "total": len(videos),
            "list": videos,
        }

    def _pagecount(self, source, current, videos):
        nums = []

        if source:
            for x in re.findall(r'(?:/list/[^"\']*/|page/)(\d+)(?:\.html|/)?', source, re.I):
                try:
                    nums.append(int(x))
                except Exception:
                    pass

            # 常见分页 href
            for x in re.findall(r'href=["\'][^"\']*[?&]page=(\d+)', source, re.I):
                try:
                    nums.append(int(x))
                except Exception:
                    pass

        if nums:
            return max([current] + nums)

        # 没有分页器时只能保守推断
        if len(videos) >= 20:
            return current + 1

        return max(current, 1)

    # ------------------------------------------------------------------
    # 详情 / 播放列表
    # ------------------------------------------------------------------

    def detailContent(self, ids, *args):
        if not ids:
            return {"list": []}

        if isinstance(ids, str):
            ids = [ids]

        output = []

        for item in ids:
            token = str(item or "").strip()

            if token.startswith("http://") or token.startswith("https://"):
                m = re.search(r"/v/([A-Za-z0-9_-]+)\.html", token, re.I)
                if m:
                    token = m.group(1)
                else:
                    continue
            else:
                token = token.strip("/")
                if token.lower().startswith("v/"):
                    token = token[2:]

            if not re.match(r"^[A-Za-z0-9_-]+$", token):
                continue

            detail_url = f"{self.base_url}/v/{token}.html"
            source = self._get(detail_url)
            if not source:
                continue

            title = token

            m = re.search(
                r'<h1\b[^>]*>([\s\S]*?)</h1>',
                source,
                re.I,
            )
            if m:
                title = self._clean(m.group(1))

            if not title:
                m = re.search(
                    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
                    source,
                    re.I,
                )
                if m:
                    title = self._clean(m.group(1))

            pic = ""
            m = re.search(
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
                source,
                re.I,
            )
            if m:
                pic = self._fix(m.group(1))

            # 简介：剧情介绍面板 / 简介标签 / meta
            content = ""
            m = re.search(
                r'id=["\']desc["\'][\s\S]{0,80}?'
                r'(?:剧情介绍|简介)[\s\S]{0,400}?'
                r'<p\b[^>]*class=["\'][^"\']*aaas[^"\']*["\'][^>]*>'
                r'([\s\S]*?)</p>',
                source,
                re.I,
            )
            if m:
                content = self._clean(m.group(1))
            if not content:
                m = re.search(
                    r'(?:剧情介绍|详情简介)[\s\S]{0,300}?'
                    r'<p\b[^>]*>([\s\S]*?)</p>',
                    source,
                    re.I,
                )
                if m:
                    content = self._clean(m.group(1))
            if not content:
                m = re.search(
                    r'简介[：:]\s*</span>\s*([\s\S]{0,800}?)(?:</div>|</p>|<span)',
                    source,
                    re.I,
                )
                if m:
                    content = self._clean(m.group(1))
            if not content:
                m = re.search(
                    r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\']([^"\']+)',
                    source,
                    re.I,
                )
                if m:
                    content = self._clean(m.group(1))
            # 去掉站点尾巴
            if content:
                content = re.sub(
                    r'(在线播放地址|北斗影院提供)[^\s]*.*$',
                    '',
                    content,
                ).strip()

            def _meta_field(*names):
                for name in names:
                    mm = re.search(
                        r'(?:<span[^>]*>\s*)?' + re.escape(name) +
                        r'\s*[：:]\s*(?:</span>)?\s*([^<\n]{1,120})',
                        source,
                        re.I,
                    )
                    if mm:
                        val = self._clean(mm.group(1))
                        if val and val not in ("未知", "内详", "/"):
                            return val
                return ""

            year = _meta_field("年份", "上映", "年代")
            area = _meta_field("地区", "国家", "产地")
            remarks = _meta_field("状态", "更新", "备注")
            if not remarks:
                # 列表备注常见角标
                mm = re.search(
                    r'class=["\'][^"\']*(?:note|remarks|badge|aecccdfg)[^"\']*["\'][^>]*>'
                    r'([\s\S]*?)</',
                    source,
                    re.I,
                )
                if mm:
                    remarks = self._clean(mm.group(1))

            # 线路名称：严格来自播放组按钮
            line_names = re.findall(
                r'<button\b[^>]*class=["\'][^"\']*'
                r'playlist-group-btn[^"\']*["\'][^>]*>'
                r'([\s\S]*?)</button>',
                source,
                re.I,
            )
            line_names = [self._clean(x) for x in line_names if self._clean(x)]

            # 分集同时支持 title/aria-label/文本
            ep_pattern = re.compile(
                r'<a\b[^>]*'
                r'href=["\'](/p/' + re.escape(token) +
                r'/(\d+)/(\d+)\.html)["\'][^>]*'
                r'>([\s\S]*?)</a>',
                re.I,
            )

            groups = {}

            for m in ep_pattern.finditer(source):
                href = m.group(1)
                sid = m.group(2)
                nid = m.group(3)
                block = m.group(4)

                ep_name = ""

                tm = re.search(
                    r'\btitle=["\']([^"\']+)["\']',
                    m.group(0),
                    re.I,
                )
                if tm:
                    ep_name = self._clean(tm.group(1))

                if not ep_name:
                    am = re.search(
                        r'\baria-label=["\']([^"\']+)["\']',
                        m.group(0),
                        re.I,
                    )
                    if am:
                        ep_name = self._clean(am.group(1))

                if not ep_name:
                    ep_name = self._clean(block)

                if not ep_name:
                    ep_name = "第%s集" % nid

                groups.setdefault(sid, []).append(
                    (int(nid), ep_name, self._fix(href))
                )

            # 兜底：如果上面的格式因 HTML 属性顺序变化没匹配，
            # 从播放列表 pane 中抓 /p/token/sid/nid
            if not groups:
                fallback = re.compile(
                    r'href=["\'](/p/' + re.escape(token) +
                    r'/(\d+)/(\d+)\.html)["\']',
                    re.I,
                )
                for m in fallback.finditer(source):
                    href, sid, nid = m.group(1), m.group(2), m.group(3)
                    groups.setdefault(sid, []).append(
                        (int(nid), "第%s集" % nid, self._fix(href))
                    )

            # 按 sid 数值排序；每条线路内部按集数排序
            def sid_key(x):
                try:
                    return int(x)
                except Exception:
                    return 999999

            play_from = []
            play_url = []

            for index, sid in enumerate(sorted(groups.keys(), key=sid_key)):
                episodes = groups[sid]

                # 去重并稳定排序
                unique = {}
                for nid, ep_name, ep_url in episodes:
                    unique[nid] = (ep_name, ep_url)

                items = []
                for nid in sorted(unique):
                    ep_name, ep_url = unique[nid]
                    items.append(f"{ep_name}${ep_url}")

                if not items:
                    continue

                if index < len(line_names):
                    line_name = line_names[index]
                else:
                    line_name = "线路%s" % (index + 1)

                play_from.append(line_name)
                play_url.append("#".join(items))

            output.append({
                "vod_id": token,
                "vod_name": title,
                "vod_pic": pic,
                "vod_year": year,
                "vod_area": area,
                "vod_remarks": remarks,
                "vod_content": content,
                "vod_play_from": "$$$".join(play_from),
                "vod_play_url": "$$$".join(play_url),
            })

        return {"list": output}

    # ------------------------------------------------------------------
    # 播放解析
    # ------------------------------------------------------------------

    def _unwrap_nested_media(self, url):
        """解包 byteimg / 代理壳把真实 m3u8 塞进 ?url= 的写法。

        例: https://p3-tt.byteimg.com/...?url=https://xxx.com/index.m3u8
        → https://xxx.com/index.m3u8
        """
        if not url:
            return ""
        u = str(url).strip()
        # 多轮解包，防止双重编码
        for _ in range(3):
            m = re.search(
                r'[?&](?:url|src|file|video|playurl|play_url|media)=((?:https?|HTTPS?)(?::|%3A)(?:/|%2F){2}[^&\'"\s<>]+)',
                u,
                re.I,
            )
            if not m:
                break
            inner = unquote(m.group(1)).replace("\\/", "/")
            if self.isVideoFormat(inner) or re.search(r'\.(?:m3u8|mp4|flv|mkv)(?:\?|$)', inner, re.I):
                u = inner
                continue
            # 内层仍可能是壳
            if inner.startswith("http"):
                u = inner
                continue
            break
        return u

    def _extract_media_url(self, text, base):
        """只从已经拿到的 HTML/JS/JSON 中提取显式媒体 URL。"""
        if not text:
            return ""

        text = html_lib.unescape(str(text))
        text = text.replace("\\/", "/").replace("\\u0026", "&").replace("\\u003A", ":")
        try:
            text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)
        except Exception:
            pass

        # 0. 优先拆 ?url= 嵌套媒体（非非/无极云 iframe 常见）
        for m in re.finditer(
            r'[?&](?:url|src|file|video|playurl)=((?:https?|HTTPS?)(?::|%3A)(?:/|%2F){2}[^&\'"\s<>]+)',
            text,
            re.I,
        ):
            inner = unquote(m.group(1)).replace("\\/", "/")
            if self.isVideoFormat(inner) or re.search(r'\.(?:m3u8|mp4|flv|mkv)(?:\?|$)', inner, re.I):
                return self._fix(inner, base)

        # 1. 显式绝对媒体 URL（跳过明显的壳域名，避免把 byteimg?url=m3u8 当最终地址）
        patterns = [
            r'https?://[^"\'\s<>\\]+?\.m3u8(?:\?[^"\'\s<>\\]*)?',
            r'https?://[^"\'\s<>\\]+?\.mp4(?:\?[^"\'\s<>\\]*)?',
            r'https?://[^"\'\s<>\\]+?\.flv(?:\?[^"\'\s<>\\]*)?',
            r'https?://[^"\'\s<>\\]+?\.mkv(?:\?[^"\'\s<>\\]*)?',
        ]

        for pat in patterns:
            for m in re.finditer(pat, text, re.I):
                raw = m.group(0)
                # 若整段是壳+内嵌，优先内嵌
                unwrapped = self._unwrap_nested_media(raw)
                candidate = self._fix(unwrapped or raw, base)
                # 丢弃纯壳：byteimg/obj 且路径本身不是媒体
                low = candidate.lower()
                if "byteimg.com" in low and not re.search(r'\.(?:m3u8|mp4|flv|mkv)(?:\?|$)', low):
                    continue
                if self.isVideoFormat(candidate) or re.search(r'\.(?:m3u8|mp4|flv|mkv)(?:\?|$)', low):
                    return candidate

        # 先求值静态播放器变量：const url = atob("...")、
        # const src = decodeURIComponent("...")、const file = base + "/a.m3u8"。
        # 这一步能覆盖“媒体地址不直接出现在源码文本里”的常见写法。
        try:
            static_values = self._js_static_values(text, base)
            for key, value in static_values.items():
                if str(key).startswith("__") or isinstance(value, dict):
                    continue
                candidate = self._fix(unquote(str(value)), base)
                if self.isVideoFormat(candidate):
                    return candidate
        except Exception:
            pass

        # 协议相对地址、URL 编码后的媒体地址
        for m in re.finditer(r'["\\\']((?://)[^"\\\'\\s<>]+?\\.(?:m3u8|mp4|flv|mkv)(?:\\?[^"\\\'\\s<>]*)?)', text, re.I):
            candidate = self._fix(m.group(1), base)
            if self.isVideoFormat(candidate):
                return candidate
        for m in re.finditer(r'(?:https?%3A%2F%2F|https?://)[^"\\\'\\s<>]+', text, re.I):
            try:
                candidate = unquote(m.group(0)).replace("\\/","/")
            except Exception:
                candidate = m.group(0)
            candidate = self._fix(candidate, base)
            if self.isVideoFormat(candidate):
                return candidate

        # URL 被整体 percent-encode 时，前面的绝对 URL 正则无法命中。
        for m in re.finditer(r"https?%3A%2F%2F[^\"\\'\s<>]+", text, re.I):
            candidate = self._fix(unquote(m.group(0)).replace("\\/", "/"), base)
            if self.isVideoFormat(candidate):
                return candidate

        # 某些播放器直接把媒体 URL 作为 base64 文本输出。只接受解码后
        # 明确是 http(s) 媒体地址的结果，避免误把普通长字符串当媒体。
        for m in re.finditer(r"(?<![A-Za-z0-9+/=])([A-Za-z0-9+/]{24,}={0,2})(?![A-Za-z0-9+/=])", text):
            try:
                token = m.group(1)
                decoded = base64.b64decode(token + "=" * ((4 - len(token) % 4) % 4), validate=False).decode("utf-8", "ignore")
                if re.match(r"https?://", decoded, re.I) and self.isVideoFormat(decoded):
                    return self._fix(decoded, base)
            except Exception:
                continue

        # 2. 常见播放器变量
        var_patterns = [
            r'\b(?:url|src|file|source|playUrl|playurl|videoUrl|video_url|'
            r'play_url|m3u8|mediaUrl|media_url)\s*[:=]\s*["\']([^"\']+)["\']',
            r'\b(?:url|src|file|source)\s*[:=]\s*`([^`]+)`',
        ]

        for pat in var_patterns:
            for m in re.finditer(pat, text, re.I):
                candidate = self._fix(unquote(m.group(1)), base)
                if self.isVideoFormat(candidate):
                    return candidate

        # 3. JSON 字符串中可能包着媒体地址
        for key in (
            "url", "src", "file", "source", "playUrl",
            "playurl", "videoUrl", "video_url", "play_url",
            "m3u8", "mediaUrl", "media_url",
        ):
            pat = (
                r'["\']' + re.escape(key) +
                r'["\']\s*:\s*["\']([^"\']+)["\']'
            )
            m = re.search(pat, text, re.I)
            if m:
                candidate = self._fix(unquote(m.group(1)), base)
                if self.isVideoFormat(candidate):
                    return candidate

        # 4. video/source 标签
        for pat in (
            r'<source\b[^>]*src=["\']([^"\']+)["\']',
            r'<video\b[^>]*src=["\']([^"\']+)["\']',
        ):
            m = re.search(pat, text, re.I)
            if m:
                candidate = self._fix(unquote(m.group(1)), base)
                if self.isVideoFormat(candidate):
                    return candidate

        # 5. 播放器初始化对象：player/setup/video.js 等常见写法。
        #    这些地址经常不是简单的 url=，而是 file/src/url 嵌在对象里。
        for pat in (
            r'\b(?:file|src|url|source|playlist)\s*:\s*["\']([^"\']+)["\']',
            r'\b(?:file|src|url|source|playlist)\s*:\s*`([^`]+)`',
        ):
            for m in re.finditer(pat, text, re.I):
                value = unquote(m.group(1).replace("\\/", "/").replace("&amp;", "&"))
                candidate = self._fix(value, base)
                if self.isVideoFormat(candidate):
                    return candidate

        # 6. location/window.location 重定向到媒体地址。
        for pat in (
            r'\b(?:window\.)?location(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
            r'\b(?:window\.)?location\.replace\s*\(\s*["\']([^"\']+)["\']',
            r'\b(?:window\.)?location\.assign\s*\(\s*["\']([^"\']+)["\']',
        ):
            for m in re.finditer(pat, text, re.I):
                candidate = self._fix(unquote(m.group(1)), base)
                if self.isVideoFormat(candidate):
                    return candidate

        # 7. meta refresh / 常见重定向标签。
        mm = re.search(r'<meta\b[^>]*http-equiv=["\']refresh["\'][^>]*content=["\'][^"\']*url=([^"\']+)', text, re.I)
        if mm:
            candidate = self._fix(unquote(mm.group(1).strip()), base)
            if self.isVideoFormat(candidate):
                return candidate

        # 8. HTML/JS/JSON 中的裸媒体路径，例如 /media/xxx.m3u8。
        for m in re.finditer(
            r'["\']((?:/|\.{0,2}/)[^"\']+\.(?:m3u8|mp4|flv|mkv|webm|m4v)(?:\?[^"\']*)?)["\']',
            text, re.I
        ):
            candidate = self._fix(unquote(m.group(1)), base)
            if self.isVideoFormat(candidate):
                return candidate

        return ""

    def _extract_iframe(self, text, base):
        if not text:
            return ""

        # playerFrame 优先
        patterns = [
            r'<iframe\b[^>]*\bid=["\']playerFrame["\'][^>]*\bsrc=["\']([^"\']+)',
            r'<iframe\b[^>]*\bsrc=["\']([^"\']+)["\'][^>]*\bid=["\']playerFrame["\']',
            r'<iframe\b[^>]*\bsrc=["\']([^"\']+)["\']',
        ]

        for pat in patterns:
            m = re.search(pat, text, re.I)
            if m:
                return self._fix(m.group(1), base)

        # document.write('<iframe src="...">') / JS 字符串里生成 iframe。
        # 这是静态还原，不执行 DOM。
        for pat in (
            r'<iframe[^>]+src=["\']([^"\']+)["\']',
            r'iframe[^>]+src\s*=\s*["\']([^"\']+)["\']',
        ):
            m = re.search(pat, html_lib.unescape(str(text)), re.I)
            if m:
                return self._fix(m.group(1), base)
        return ""

    def _play_result(self, url, referer, parse=0, click="", jx=0, play_url=""):
        """构造 T4/FongMi 兼容播放结果。

        注意：抖音/头条 CDN（douyinvod 等）对 Referer 有 ACL，
        带上 langfeng / 站点 Referer 会 403 返回 HTML，
        壳端就会报 Failed to recognize file format。
        """
        media = str(url or "").strip()
        thost = ""
        try:
            thost = (urlparse(media).netloc or "").lower()
        except Exception:
            pass

        # 默认桌面/通用 UA 更利于部分 m3u8 CDN；抖音系用移动也可
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
        headers = {
            "User-Agent": ua,
            "Accept": "*/*",
        }

        is_douyin = bool(re.search(
            r"(?:douyinvod|byteicdn|byteimg|tos-cn-v-|ixigua|"
            r"v\d+-(?:show|cold|cold\d*|ktv)\.|zjcdn|bilivideo)",
            thost,
        )) or ("/video/tos/" in media)

        is_m3u8_cdn = bool(re.search(
            r"(?:ffzy|ppqrrs|m3u8|hls|playback)",
            thost + media,
            re.I,
        )) or media.lower().endswith(".m3u8") or ".m3u8?" in media.lower()

        if is_douyin:
            # 抖音 CDN：空 Referer 或 douyin 本域可通过；禁止带第三方 Referer
            headers["User-Agent"] = (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/16.6 Mobile/15E148 Safari/604.1"
            )
            headers["Referer"] = "https://www.douyin.com/"
            # 不设 Origin，避免跨域鉴权失败
        elif is_m3u8_cdn:
            # 常见切片站：用站点作 Referer 有时反而 403，优先空 / 同源
            headers["Referer"] = "https://%s/" % (thost or "www.bdjmcc.com")
            headers["Origin"] = "https://%s" % (thost or "www.bdjmcc.com")
        else:
            ref = referer or self.base_url + "/"
            headers["Referer"] = ref
            try:
                rhost = (urlparse(ref).netloc or "").lower()
                if thost and rhost and thost != rhost:
                    headers["Origin"] = "%s://%s" % (
                        urlparse(ref).scheme or "http", rhost)
            except Exception:
                pass

        result = {
            "parse": parse,
            "jx": int(jx or 0),
            "playUrl": play_url or "",
            "url": media,
            "header": headers,
        }
        if click:
            result["click"] = click
        return result

    def _extract_script_urls(self, text, base):
        if not text:
            return []
        out, seen = [], set()
        for m in re.finditer(r'<script\b[^>]*\bsrc\s*=\s*["\']([^"\']+)', text, re.I):
            u = self._fix(m.group(1), base)
            if u and u not in seen:
                seen.add(u); out.append(u)
        # 部分打包器在 HTML 内通过 import("./xxx.js") / import ... from "..."
        # 动态加载播放器模块。只跟随明确的 JS 模块地址。
        for pat in (
            r'\bimport\s*\(\s*["\']([^"\']+\.m?js(?:\?[^"\']*)?)["\']\s*\)',
            r'\bimport\s+[^;]+?\s+from\s+["\']([^"\']+\.m?js(?:\?[^"\']*)?)["\']',
            r'\b(?:document\.createElement\(["\']script["\']\)|script)\.src\s*=\s*["\']([^"\']+\.m?js(?:\?[^"\']*)?)["\']',
            r'document\.write\s*\(\s*["\'][^"\']*<script[^>]+src=["\']([^"\']+\.m?js(?:\?[^"\']*)?)["\']',
            r'\.setAttribute\s*\(\s*["\']src["\']\s*,\s*["\']([^"\']+\.m?js(?:\?[^"\']*)?)["\']',
        ):
            for m in re.finditer(pat, text, re.I):
                u = self._fix(m.group(1), base)
                if u and u not in seen:
                    seen.add(u); out.append(u)
        # import(moduleVariable) / import(`./chunk-${name}.js`)：
        # 只跟随可静态求值的模块地址。
        try:
            values = self._js_static_values(text, base)
        except Exception:
            values = {}
        for m in re.finditer(r'\bimport\s*\(\s*([^\)]+)\s*\)', text, re.I):
            u = self._resolve_js_expr(m.group(1), values, base)
            if u and re.search(r'\.m?js(?:\?|$)', u, re.I):
                u = self._fix(u, base)
                if u and u not in seen:
                    seen.add(u); out.append(u)

        # modulepreload / preload 的 JS 模块也可能是播放器真正入口。
        for pat in (
            r'<link\b[^>]*\b(?:rel=["\'](?:modulepreload|preload)["\'][^>]*\b)?href=["\']([^"\']+\.m?js(?:\?[^"\']*)?)',
            r'<link\b[^>]*href=["\']([^"\']+\.m?js(?:\?[^"\']*)?)["\'][^>]*\brel=["\'](?:modulepreload|preload)["\']',
        ):
            for m in re.finditer(pat, text, re.I):
                u = self._fix(m.group(1), base)
                if u and u not in seen:
                    seen.add(u); out.append(u)
        return out

    def _dynamic_v_value(self, page_url):
        try:
            q = urlparse(page_url).query
            for k, v in __import__('urllib.parse', fromlist=['parse_qsl']).parse_qsl(q, keep_blank_values=True):
                if k.lower() in ('v', 'id', 'token', 'vid', 'url') and v:
                    return v
        except Exception:
            pass
        return ''

    def _js_static_values(self, text, page_url):
        """读取播放器源码里可静态确定的字符串变量，不执行 JS。"""
        values = {}
        try:
            q = dict(__import__('urllib.parse', fromlist=['parse_qsl']).parse_qsl(
                urlparse(page_url).query, keep_blank_values=True
            ))
            for k in ('v', 'id', 'token', 'vid', 'url'):
                if q.get(k):
                    values[k] = q[k]
        except Exception:
            pass
        # var/let/const name = 'literal' / "literal" / `literal`
        pat = re.compile(
            r'\b(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*(["\'`])([\s\S]*?)\2\s*;?',
            re.I
        )
        for m in pat.finditer(text or ''):
            values[m.group(1)] = self._decode_static_js_string(m.group(3))
        # 两轮解析简单变量表达式，例如：const api = base + '/play?v=' + v。
        # 只接受已知变量/字符串，不执行任意 JS。
        for _ in range(2):
            changed = False
            for em in re.finditer(r'\b(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*([^;\n]{1,700})', text or '', re.I):
                name, expr = em.group(1), em.group(2).strip()
                if name in values:
                    continue
                val = self._resolve_js_expr(expr, values, page_url)
                if not val or re.search(r'[A-Za-z_$][\w$]*', val) and not (val.startswith(('http://','https://','/')) or '?' in val or '&' in val):
                    continue
                values[name] = val
                changed = True
            if not changed:
                break
        # 常见播放器把 POST 参数先放进对象：
        # const payload = {v: v, id: id, token: token};
        # 这里保存一个可静态展开的对象，供 fetch/axios/XHR 使用。
        for om in re.finditer(
            r'\b(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*\{([\s\S]{0,1600}?)\}\s*;?',
            text or '', re.I
        ):
            obj = {}
            for km in re.finditer(r'(["\']?)([A-Za-z_$][\w$-]*)\1\s*:\s*([^,}]+)', om.group(2)):
                raw_val = km.group(3).strip()
                quoted = len(raw_val) >= 2 and raw_val[0] in "\"'`" and raw_val[-1] == raw_val[0]
                val = raw_val.strip('"\'`')
                if val in values and not quoted:
                    val = str(values[val])
                elif re.match(r'^[A-Za-z_$][\w$]*$', val) and val not in values and not quoted:
                    continue
                obj[km.group(2)] = val
            if obj:
                values['__obj_' + om.group(1)] = obj
                values[om.group(1)] = obj
        # 常见对象属性赋值：cfg.api = '/api/play' / cfg['api'] = '/api/play'。
        # 播放器打包代码经常先建立配置对象，再从属性取接口地址。
        # 只保存明确的静态字符串，不执行任意 JS。
        for pm in re.finditer(
            r'([A-Za-z_$][\w$]*)\s*(?:\.([A-Za-z_$][\w$]*)|\[\s*[\"\']([^\"\']+)[\"\']\s*\])\s*=\s*([\"\'])([^\"\']+)\4',
            text or '', re.I
        ):
            obj_name = pm.group(1)
            prop = pm.group(2) or pm.group(3)
            val = self._decode_static_js_string(pm.group(5))
            if prop and val:
                values[obj_name + '.' + prop] = val

        # cfg.api 在调用表达式中的轻量解析。
        for m in re.finditer(r'([A-Za-z_$][\w$]*)\.([A-Za-z_$][\w$]*)', text or ''):
            key = m.group(1) + '.' + m.group(2)
            if key in values:
                values[m.group(0)] = values[key]

        # 常见对象属性：const cfg = {api:'/api/play', endpoint:'/api'}。
        # 这里只保存纯字符串属性，避免执行任意 JS。
        for om in re.finditer(r'([A-Za-z_$][\w$]*)\s*[:=]\s*(["\'])(https?://[^"\']+|/[^"\']+)\2', text or '', re.I):
            values[om.group(1)] = om.group(3)
        # 静态 atob('...') 结果；同时保存可直接展开的结果。
        for m in re.finditer(r'atob\(\s*(["\'])([A-Za-z0-9+/=_-]{8,})\1\s*\)', text or '', re.I):
            try:
                decoded = base64.b64decode(m.group(2) + '===', validate=False).decode('utf-8', 'ignore')
                values['__atob_' + m.group(2)] = decoded
            except Exception:
                pass
        # eval(atob('...')) / Function(atob('...')) 这类播放器常用于隐藏
        # API 配置。这里只把可静态还原的源码加入变量表，不执行它。
        for m in re.finditer(r'(?:eval|Function)\(\s*atob\(\s*(["\'])([A-Za-z0-9+/=_-]{8,})\1\s*\)\s*\)', text or '', re.I):
            try:
                decoded = base64.b64decode(m.group(2) + '===', validate=False).decode('utf-8', 'ignore')
                values['__decoded_script_' + m.group(2)] = decoded
            except Exception:
                pass
        return values

    def _decode_static_js_string(self, value):
        """解码播放器源码中可静态还原的字符串，不执行 JavaScript。"""
        if value is None:
            return ''
        out = str(value).strip()
        try:
            out = bytes(out, 'utf-8').decode('unicode_escape')
        except Exception:
            pass
        try:
            out = unquote(out)
        except Exception:
            pass
        return out.replace('\\/', '/').replace('\\u0026', '&')

    def _resolve_simple_js_value(self, expr, values):
        """解析低风险、纯静态 JS 值。"""
        if expr is None:
            return ''
        raw = str(expr).strip().rstrip(';')
        if len(raw) >= 2 and raw[0] in "'\"`" and raw[-1] == raw[0]:
            return self._decode_static_js_string(raw[1:-1])
        if re.match(r'^[A-Za-z_$][\w$]*$', raw) and raw in values:
            return values[raw]
        m = re.match(r'(?:decodeURIComponent|unescape)\(\s*([A-Za-z_$][\w$]*|[\"\'][^\"\']*[\"\'])\s*\)$', raw, re.I)
        if m:
            v = self._resolve_simple_js_value(m.group(1), values)
            try:
                return unquote(str(v))
            except Exception:
                return v
        m = re.match(r'atob\(\s*([A-Za-z_$][\w$]*|[\"\'][^\"\']+[\"\'])\s*\)$', raw, re.I)
        if m:
            v = self._resolve_simple_js_value(m.group(1), values)
            try:
                return base64.b64decode(str(v) + '===', validate=False).decode('utf-8', 'ignore')
            except Exception:
                return ''
        m = re.match(r'String\.fromCharCode\(([^)]{1,500})\)$', raw, re.I)
        if m:
            try:
                return ''.join(chr(int(x.strip(), 0)) for x in m.group(1).split(','))
            except Exception:
                return ''
        m = re.match(r'(.+?)\.split\(\s*[\"\']\s*[\"\']\s*\)\.reverse\(\)\.join\(\s*[\"\']\s*[\"\']\s*\)$', raw, re.I)
        if m:
            v = self._resolve_simple_js_value(m.group(1), values)
            return v[::-1] if isinstance(v, str) else ''
        return ''

    def _resolve_js_expr(self, expr, values, base_url=None):
        """解析最常见的静态 URL 表达式：'/api' + '?v=' + v。"""
        if not expr:
            return ''
        expr = expr.strip().rstrip(';')
        # 模板字符串：${v} / ${id}
        if len(expr) >= 2 and expr[0] == '`' and expr[-1] == '`':
            body = expr[1:-1]
            body = re.sub(
                r'\$\{\s*([A-Za-z_$][\w$]*)\s*\}',
                lambda m: str(values.get(m.group(1), '')),
                body,
            )
            return body
        # new URL('/api/play', location.origin).href/toString() 是播放器
        # 很常见的模块化写法；这里仅解析静态首参数，不执行 JS。
        m = re.match(r'new\s+URL\(\s*([^,]+)\s*,\s*(?:window\.)?location\.origin\s*\)\s*(?:\.href|\.toString\(\))?$', expr, re.I)
        if m:
            first = self._resolve_js_expr(m.group(1), values, base_url)
            if first:
                try:
                    return urljoin(base_url or self.base_url, first)
                except Exception:
                    return first
        parts = re.split(r'\s*\+\s*', expr)
        out = []
        for part in parts:
            part = part.strip()
            if len(part) >= 2 and part[0] in "\"'`" and part[-1] == part[0]:
                out.append(self._decode_static_js_string(part[1:-1]))
                continue
            simple = self._resolve_simple_js_value(part, values)
            if simple:
                out.append(str(simple))
                continue
            if part in values:
                out.append(str(values[part]))
                continue
            # URLSearchParams 常见单值写法
            m = re.match(r'encodeURIComponent\(\s*([A-Za-z_$][\w$]*)\s*\)', part, re.I)
            if m and m.group(1) in values:
                out.append(quote(str(values[m.group(1)]), safe=''))
                continue
            out.append(part)
        result = ''.join(out).replace('\\/', '/')
        return result

    def _extract_request_urls(self, text, base):
        """提取静态 JS 中明确写出的 fetch/XHR/axios/jQuery 请求地址。"""
        if not text:
            return []
        text = html_lib.unescape(str(text)).replace("\\/", "/").replace("\\u0026", "&")
        values = self._js_static_values(text, base)
        found, seen = [], set()
        def add(value):
            if not value:
                return
            value = str(value).strip().strip("'\"`")
            if not value:
                return
            value = self._fix(value, base)
            if value not in seen:
                seen.add(value)
                found.append(value)
        patterns = [
            r"fetch\s*\(\s*['\"]([^'\"]+)['\"]",
            r"fetch\s*\(\s*`([^`]+)`",
            r"\.open\s*\(\s*['\"](?:GET|POST)['\"]\s*,\s*['\"]([^'\"]+)['\"]",
            r"\.open\s*\(\s*['\"](?:GET|POST)['\"]\s*,\s*`([^`]+)`",
            r"axios\s*\.\s*(?:get|post)\s*\(\s*['\"]([^'\"]+)['\"]",
            r"axios\s*\.\s*(?:get|post)\s*\(\s*`([^`]+)`",
            r"\$\s*\.\s*(?:get|post)\s*\(\s*['\"]([^'\"]+)['\"]",
            r"\$\s*\.\s*(?:get|post)\s*\(\s*`([^`]+)`",
            r"\burl\s*:\s*['\"]([^'\"]+)['\"]",
            r"\burl\s*:\s*`([^`]+)`",
        ]
        for pat in patterns:
            for m in re.finditer(pat, text, re.I):
                add(m.group(1))
        # fetch(api + '?v=...') / axios.get(api + ...) 在变量展开后，
        # 继续抓取调用括号中的完整字符串表达式。
        for m in re.finditer(r'\b(?:fetch|axios\.(?:get|post)|\$\.(?:get|post))\s*\(\s*([^,\)]{1,500})', text, re.I):
            value = self._resolve_js_expr(m.group(1), values, base)
            if value:
                add(value)
        for m in re.finditer(r"['\"]((?:/|https?://)[^'\"\s<>]{2,300})['\"]", text, re.I):
            v = m.group(1)
            low = v.lower()
            if any(k in low for k in ('api','play','video','media','source','stream','m3u8','player','url')):
                add(v)
        return found

    def _extract_request_calls(self, text, base):
        calls = []
        if not text:
            return calls
        values = self._js_static_values(text, base)
        # fetch(...)：按调用窗口提取 method/body，避免 headers 等嵌套对象截断匹配。
        for m in re.finditer(r'fetch\s*\(\s*([^,\)]+)', text, re.I):
            expr = m.group(1)
            window = text[m.start():m.start() + 2200]
            if not re.search(r'\bmethod\s*[:=]\s*["\']POST["\']', window, re.I):
                continue
            endpoint = self._fix(self._resolve_js_expr(expr, values, base), base)
            data = {}
            jm = re.search(r'JSON\.stringify\s*\(\s*\{([\s\S]{0,1200}?)\}\s*\)', window, re.I)
            if jm:
                for km in re.finditer(r'["\']?([A-Za-z0-9_-]+)["\']?\s*:\s*([^,}]+)', jm.group(1)):
                    val = km.group(2).strip().strip('"\'`')
                    data[km.group(1)] = str(values.get(val, val))
            else:
                # JSON.stringify(payload) / JSON.stringify(params)
                vm = re.search(r'JSON\.stringify\s*\(\s*([A-Za-z_$][\w$]*)\s*\)', window, re.I)
                if vm and isinstance(values.get(vm.group(1)), dict):
                    data.update(values[vm.group(1)])
                bm = re.search(r'\bbody\s*:\s*["\']([^"\']*)["\']', window, re.I)
                if bm:
                    body = self._resolve_js_expr(bm.group(1), values)
                    for km in re.finditer(r'([A-Za-z0-9_-]+)=([^&]*)', body):
                        data[km.group(1)] = km.group(2)
            # URLSearchParams({v: v, id: id}) / URLSearchParams("v=" + v)
            um = re.search(r'new\s+URLSearchParams\s*\(\s*\{([\s\S]{0,900}?)\}\s*\)', window, re.I)
            if um:
                for km in re.finditer(r'["\']?([A-Za-z0-9_-]+)["\']?\s*:\s*([^,}]+)', um.group(1)):
                    val = km.group(2).strip().strip('"\'`')
                    data[km.group(1)] = str(values.get(val, val))
            if re.search(r'JSON\.stringify|application/json|content-type\s*[:=]\s*["\']application/json', window, re.I):
                data["__bd_json__"] = True
            calls.append(("POST", endpoint, data))
        # XMLHttpRequest：POST。
        # 不执行 JS，只把同一源码窗口内明确出现的 open/send 配对起来。
        for om in re.finditer(r'([A-Za-z_$][\w$]*)\.open\s*\(\s*["\']POST["\']\s*,\s*([^,\)]+)', text, re.I):
            xhr = om.group(1)
            endpoint = self._fix(self._resolve_js_expr(om.group(2), values, base), base)
            window = text[om.start():om.start() + 5000]
            sm = re.search(r'\b' + re.escape(xhr) + r'\.send\s*\(\s*([\s\S]{0,1800}?)\s*\)\s*;', window, re.I)
            data = {}
            if sm:
                body_expr = sm.group(1).strip()
                jm = re.search(r'JSON\.stringify\s*\(\s*\{([\s\S]{0,1200}?)\}\s*\)', body_expr, re.I)
                if jm:
                    for km in re.finditer(r'["\']?([A-Za-z0-9_-]+)["\']?\s*:\s*([^,}]+)', jm.group(1)):
                        val = km.group(2).strip().strip('"\'`')
                        data[km.group(1)] = str(values.get(val, val))
                else:
                    vm = re.search(r'JSON\.stringify\s*\(\s*([A-Za-z_$][\w$]*)\s*\)', body_expr, re.I)
                    if vm and isinstance(values.get(vm.group(1)), dict):
                        data.update(values[vm.group(1)])
                    else:
                        qm = re.search(r'([A-Za-z0-9_-]+)=([^&"\']*)', body_expr)
                        if qm:
                            data[qm.group(1)] = qm.group(2)
            if re.search(r'JSON\.stringify|application/json|content-type\s*[:=]\s*["\']application/json', window, re.I):
                data["__bd_json__"] = True
            calls.append(("POST", endpoint, data))

        # XMLHttpRequest：GET。以前这里仅靠 _extract_request_urls，
        # 对 x.open("GET", apiVariable) 这种“URL 放变量里”的播放器写法会漏掉。
        # 现在把它作为真正的 GET 调用处理，并允许把动态 v/id/token/vid
        # 继续带到 URL 上；仍然只跟随源码明确出现的请求，不做路径爆破。
        for om in re.finditer(r'([A-Za-z_$][\w$]*)\.open\s*\(\s*["\']GET["\']\s*,\s*([^,\)]+)', text, re.I):
            endpoint = self._fix(self._resolve_js_expr(om.group(2), values, base), base)
            if endpoint:
                calls.append(("GET", endpoint, {}))

        # jQuery $.ajax({url: expr, type/method: "GET"})，补变量 URL。
        for m in re.finditer(r'\$\.ajax\s*\(\s*\{([\s\S]{0,1600}?)\}\s*\)', text, re.I):
            block = m.group(1)
            um = re.search(r'\burl\s*:\s*([^,}]+)', block, re.I)
            mm = re.search(r'\b(?:type|method)\s*:\s*["\']GET["\']', block, re.I)
            if um and mm:
                endpoint = self._fix(self._resolve_js_expr(um.group(1), values, base), base)
                if endpoint:
                    calls.append(("GET", endpoint, {}))

        # fetch/axios 的 method 可以写成变量或小写 get；这里补一个轻量 GET
        # 调用识别，避免依赖“字符串 URL”正则。
        for m in re.finditer(r'fetch\s*\(\s*([^,\)]+)\s*,\s*\{([\s\S]{0,1200}?)\}\s*\)', text, re.I):
            block = m.group(2)
            if re.search(r'\bmethod\s*:\s*["\']GET["\']', block, re.I):
                endpoint = self._fix(self._resolve_js_expr(m.group(1), values, base), base)
                if endpoint:
                    calls.append(("GET", endpoint, {}))

        # axios.get(url, config) / $.get(url, config) 的变量 URL。
        for m in re.finditer(r'\b(?:axios|\$)\.(?:get)\s*\(\s*([^,\)]+)', text, re.I):
            endpoint = self._fix(self._resolve_js_expr(m.group(1), values, base), base)
            if endpoint:
                calls.append(("GET", endpoint, {}))

        # axios.request({url: expr, method: "GET"|"POST"})。POST 参数仍交给
        # _extract_request_calls 的其他专用分支；这里专门补 GET。
        for m in re.finditer(r'axios\.request\s*\(\s*\{([\s\S]{0,1800}?)\}\s*\)', text, re.I):
            block = m.group(1)
            if not re.search(r'\bmethod\s*:\s*["\']GET["\']', block, re.I):
                continue
            um = re.search(r'\burl\s*:\s*([^,}]+)', block, re.I)
            if um:
                endpoint = self._fix(self._resolve_js_expr(um.group(1), values, base), base)
                if endpoint:
                    calls.append(("GET", endpoint, {}))

        # axios.post(url, payloadVariable) / $.post(url, payloadVariable)
        # 补充对象变量形式，而不是只支持字面量 {...}。
        for m in re.finditer(r'\b(?:axios|\$)\.post\s*\(\s*([^,\)]+)\s*,\s*([A-Za-z_$][\w$]*)\s*\)', text, re.I):
            endpoint = self._fix(self._resolve_js_expr(m.group(1), values, base), base)
            payload = values.get(m.group(2))
            data = dict(payload) if isinstance(payload, dict) else {}
            if endpoint:
                calls.append(("POST", endpoint, data))

        # axios.request({url: expr, method: "POST", data: payload})。
        # 只接受静态对象/变量，避免执行任意 JS。
        for m in re.finditer(r'axios\.request\s*\(\s*\{([\s\S]{0,2200}?)\}\s*\)', text, re.I):
            block = m.group(1)
            if not re.search(r'\bmethod\s*:\s*["\']POST["\']', block, re.I):
                continue
            um = re.search(r'\burl\s*:\s*([^,}]+)', block, re.I)
            if not um:
                continue
            endpoint = self._fix(self._resolve_js_expr(um.group(1), values, base), base)
            data = {}
            dm = re.search(r'\bdata\s*:\s*([A-Za-z_$][\w$]*)', block, re.I)
            if dm and isinstance(values.get(dm.group(1)), dict):
                data.update(values[dm.group(1)])
            if endpoint:
                calls.append(("POST", endpoint, data))

        # axios/fetch 常见的 header token 不能在静态 Spider 里“生成”，但
        # 如果源码直接暴露 Bearer/Authorization 常量，保存下来供后续请求使用。
        # 这里只返回调用三元组，实际 header 由 _resolve_dynamic_requests 决定；
        # 因而不在这里伪造 token。

        # axios.post(url, {v: v})
        for m in re.finditer(r'axios\.post\s*\(\s*([^,\)]+)\s*,\s*\{([\s\S]{0,900}?)\}\s*\)', text, re.I):
            endpoint = self._fix(self._resolve_js_expr(m.group(1), values, base), base)
            data = {}
            for km in re.finditer(r'["\']?([A-Za-z0-9_-]+)["\']?\s*:\s*([^,}]+)', m.group(2)):
                val = km.group(2).strip().strip('"\'`')
                data[km.group(1)] = str(values.get(val, val))
            calls.append(("POST", endpoint, data))
        # $.ajax({url:"...", type:"POST", data:{...}})
        for m in re.finditer(r'\$\.ajax\s*\(\s*\{([\s\S]{0,1200}?)\}\s*\)', text, re.I):
            block = m.group(1)
            um = re.search(r'\burl\s*:\s*["\']([^"\']+)["\']', block, re.I)
            mm = re.search(r'\b(?:type|method)\s*:\s*["\']POST["\']', block, re.I)
            if um and mm:
                data = {}
                dm = re.search(r'\bdata\s*:\s*\{([\s\S]{0,700}?)\}', block, re.I)
                if dm:
                    for km in re.finditer(r'["\']?([A-Za-z0-9_-]+)["\']?\s*:\s*([^,}]+)', dm.group(1)):
                        val = km.group(2).strip().strip('"\'`')
                        data[km.group(1)] = str(values.get(val, val))
                calls.append(("POST", self._fix(self._resolve_js_expr(um.group(1), values, base), base), data))
        return calls

    def _resolve_dynamic_requests(self, source, page_url, depth=0, seen=None):
        """解析 player.html 的静态 JS：脚本文件、fetch/XHR/axios、JSON/iframe。
        不执行 JS；只跟随源码明确暴露的请求地址。
        """
        if not source or depth > 3:
            return ""
        if seen is None:
            seen = set()

        # 先把外链 JS 拉下来；很多 player.html 自身只有一个壳。
        sources = [source]
        # 递归追显式 JS 模块：player.html -> loader.js -> chunk.js -> API。
        # 不再只读取 HTML 第一层 script；每个已加载 JS 自己引用的 chunk 也会
        # 进入队列。这样更接近真实浏览器的模块加载链，同时仍然只访问源码
        # 明确暴露的脚本 URL。
        if depth <= 3:
            queue = list(self._extract_script_urls(source, page_url)[:16])
            script_count = 0
            while queue and script_count < 32:
                js_url = queue.pop(0)
                if not js_url or js_url in seen:
                    continue
                seen.add(js_url)
                js = self._get(js_url, referer=page_url)
                if not js:
                    continue
                sources.append(js)
                script_count += 1
                for nested_js in self._extract_script_urls(js, js_url)[:12]:
                    if nested_js not in seen and nested_js not in queue:
                        queue.append(nested_js)
        # 如果源码本身含有静态 eval(atob(...))，把解码后的源码当作下一份
        # 静态 JS 输入继续分析；绝不执行任意代码。
        values = self._js_static_values(source, page_url)
        for k, decoded in list(values.items()):
            if str(k).startswith('__decoded_script_') and decoded and decoded not in sources:
                sources.append(decoded)

        v_value = self._dynamic_v_value(page_url)
        for current in sources:
            # JS 模块本身可能已经包含最终媒体地址；不能只把它当成“请求定义”
            # 再去扫描，否则会把 m3u8 URL 当成一个 API URL 请求。
            direct_media = self._extract_media_url(current, page_url)
            if direct_media:
                return direct_media
            for method, endpoint, data in self._extract_request_calls(current, page_url):
                if not endpoint:
                    continue
                if v_value and not data and method == "POST":
                    data = {"v": v_value}
                key = method + " " + endpoint + " " + json.dumps(data, sort_keys=True, ensure_ascii=False)
                if key in seen:
                    continue
                seen.add(key)
                if method == "POST":
                    body = self._post(endpoint, data=data, referer=page_url)
                else:
                    target = endpoint
                    if v_value:
                        target = re.sub(r'([?&](?:v|id|token|vid)=)$', lambda m: m.group(1) + quote(v_value), target, flags=re.I)
                        target = re.sub(r'\$\{(?:v|id|token|vid)\}', quote(v_value), target, flags=re.I)
                        target = re.sub(r'\{(?:v|id|token|vid)\}', quote(v_value), target, flags=re.I)
                    body = self._get(target, referer=page_url)
                if body:
                    media = self._extract_media_url(body, endpoint)
                    if media:
                        return media
                    nested = self._extract_iframe(body, endpoint)
                    if nested:
                        media = self._resolve_play_page(nested, depth + 1, seen)
                        if media:
                            return media
                    media = self._resolve_dynamic_requests(body, endpoint, depth + 1, seen)
                    if media:
                        return media
            endpoints = self._extract_request_urls(current, page_url)
            for endpoint in endpoints:
                if not endpoint or endpoint in seen:
                    continue
                target = endpoint
                if v_value:
                    # 常见动态播放器把 query 参数直接拼进 API URL。
                    target = re.sub(r'([?&](?:v|id|token|vid)=)$', lambda m: m.group(1) + quote(v_value), target, flags=re.I)
                    target = re.sub(r'\$\{(?:v|id|token|vid)\}', quote(v_value), target, flags=re.I)
                    target = re.sub(r'\{(?:v|id|token|vid)\}', quote(v_value), target, flags=re.I)
                seen.add(target)
                body = self._get(target, referer=page_url)
                if not body:
                    continue
                media = self._extract_media_url(body, target)
                if media:
                    return media
                nested = self._extract_iframe(body, target)
                if nested:
                    media = self._resolve_play_page(nested, depth + 1, seen)
                    if media:
                        return media
                media = self._resolve_dynamic_requests(body, target, depth + 1, seen)
                if media:
                    return media
        return ""

    def _resolve_langfeng_proxy(self, player_url, referer=None):
        """解析 ttss.langfeng888.com 一类 player.html?v=TOKEN → /proxy/TOKEN。

        实测返回 JSON: {"code":200,"url":"https://...douyinvod..."}，
        媒体地址常无 .m3u8/.mp4 后缀，需按 CDN 特征识别。
        """
        if not player_url:
            return ""
        try:
            parsed = urlparse(player_url)
            host = (parsed.netloc or "").lower()
            # 兼容同系域名
            if not any(x in host for x in (
                "langfeng888.com", "langfeng", "ttss."
            )) and "player.html" not in (parsed.path or ""):
                # 仍尝试从 query 取 v，再拼已知 proxy
                pass

            q = dict(__import__("urllib.parse", fromlist=["parse_qsl"]).parse_qsl(
                parsed.query, keep_blank_values=True
            ))
            v = (q.get("v") or q.get("id") or q.get("token") or q.get("vid") or "").strip()
            if not v:
                # 路径尾部也可能是 token
                m = re.search(r"[?&]v=([A-Za-z0-9_-]+)", player_url)
                if m:
                    v = m.group(1)
            if not v:
                return ""

            # 优先用播放器同源 /proxy/
            origin = "%s://%s" % (parsed.scheme or "https", parsed.netloc)
            candidates = [
                "%s/proxy/%s" % (origin, quote(v, safe="")),
                "https://ttss.langfeng888.com/proxy/%s" % quote(v, safe=""),
            ]
            # 去重保序
            seen = set()
            apis = []
            for u in candidates:
                if u not in seen:
                    seen.add(u)
                    apis.append(u)

            ref = referer or player_url
            for api in apis:
                self._play_log("LANGFENG", "请求 proxy 接口", api=api, v=v[:16])
                body = self._get(api, referer=ref, timeout=12)
                if not body:
                    continue
                media = ""
                try:
                    obj = json.loads(body)
                    if isinstance(obj, dict):
                        code = obj.get("code")
                        url = obj.get("url") or obj.get("data") or ""
                        if isinstance(url, dict):
                            url = url.get("url") or url.get("src") or ""
                        if (code in (200, "200", 0, "0", None) or not code) and url:
                            media = self._fix(str(url).strip(), api)
                except Exception:
                    media = self._extract_media_url(body, api)
                if media:
                    self._play_log("LANGFENG_OK", "proxy 取得媒体地址", media=media[:120])
                    return media
                # 裸文本直链
                t = body.strip().strip('"')
                if t.startswith("http") and (
                    self.isVideoFormat(t) or "douyinvod" in t or "/video/" in t
                ):
                    return self._fix(t, api)
        except Exception as exc:
            self._play_log("LANGFENG_FAIL", "proxy 解析异常", error=str(exc)[:120])
        return ""

    def _resolve_play_page(self, play_url, depth=0, seen=None):
        """静态解析播放页、iframe、显式媒体地址及源码中暴露的 API。"""
        if depth > 3:
            return ""
        if seen is None:
            seen = set()
        if play_url in seen:
            return ""
        seen.add(play_url)

        # 已是 langfeng 播放器入口时直接走 proxy，避免再绕 HTML
        if "player.html" in play_url and ("v=" in play_url or "langfeng" in play_url):
            media = self._resolve_langfeng_proxy(play_url, referer=self.base_url + "/")
            if media:
                return media

        source = self._get(play_url, referer=self.base_url + "/")
        if not source:
            return ""
        media = self._extract_media_url(source, play_url)
        if media:
            return media
        iframe = self._extract_iframe(source, play_url)
        if iframe and iframe not in seen:
            # 优先识别 langfeng 系
            if "player.html" in iframe or "langfeng" in iframe:
                media = self._resolve_langfeng_proxy(iframe, referer=play_url)
                if media:
                    return media
            media = self._resolve_play_page(iframe, depth + 1, seen)
            if media:
                return media
        media = self._resolve_dynamic_requests(source, play_url, depth=0, seen=seen)
        if media:
            return media
        return ""

    def _play_cache_key(self, flag, raw):
        return "%s\n%s" % (str(flag or ""), str(raw or "").strip())

    def _play_cached(self, key):
        now = time.monotonic()
        with self._play_cache_lock:
            item = self._play_result_cache.get(key)
            if item and now - item[0] <= self._play_result_ttl:
                self._play_log("PLAY_CACHE", "命中已解析播放结果", key=key)
                return dict(item[1])
            if item:
                self._play_result_cache.pop(key, None)
            fail = self._play_failure_cache.get(key)
            if fail and now - fail[0] <= self._play_failure_ttl:
                self._play_log("PLAY_COOLDOWN", "同一播放页刚刚解析失败，进入冷却期，禁止重复请求", key=key)
                return dict(fail[1])
            if fail:
                self._play_failure_cache.pop(key, None)
        return None

    def _play_store_success(self, key, result):
        with self._play_cache_lock:
            self._play_result_cache[key] = (time.monotonic(), dict(result))
            self._play_failure_cache.pop(key, None)

    def _play_store_failure(self, key, result):
        with self._play_cache_lock:
            self._play_failure_cache[key] = (time.monotonic(), dict(result))

    def playerContent(self, flag, id, vipFlags=None, *args):
        raw = str(id or "").strip()
        key = self._play_cache_key(flag, raw)
        cached = self._play_cached(key)
        if cached is not None:
            return cached

        # 已经是媒体地址
        if self.isVideoFormat(raw):
            result = self._play_result(self._fix(raw), self.base_url + "/", parse=0)
            self._play_store_success(key, result)
            return result

        if raw.startswith("/"):
            play_url = self._fix(raw)
        elif raw.startswith("http://") or raw.startswith("https://"):
            play_url = raw
        elif re.match(r'^[A-Za-z0-9_-]+$', raw):
            play_url = f"{self.base_url}/v/{raw}.html"
        else:
            play_url = self._fix(raw)

        self._play_log("START", "开始解析播放链", flag=flag, play=play_url)
        source = self._get(play_url, referer=self.base_url + "/")

        # 入口本身就是 langfeng player.html?v=...
        if "player.html" in play_url and "v=" in play_url:
            media = self._resolve_langfeng_proxy(play_url, referer=self.base_url + "/")
            if media:
                result = self._play_result(media, play_url, parse=0)
                self._play_store_success(key, result)
                return result

        if source:
            media = self._extract_media_url(source, play_url)
            if media:
                result = self._play_result(media, play_url, parse=0)
                self._play_store_success(key, result)
                self._play_log("SUCCESS", "播放页直接得到媒体地址", play=play_url, media=media)
                return result

            iframe = self._extract_iframe(source, play_url)
            source_seen = {play_url}
            if iframe:
                source_seen.add(iframe)

            # 关键路径：移动 UA 下的 playerFrame → langfeng proxy
            # 非非/无极云：iframe src 直接是 byteimg?url=真实m3u8
            if iframe:
                self._play_log("IFRAME", "发现播放器 iframe", play=play_url, iframe=iframe)
                unwrapped = self._unwrap_nested_media(iframe)
                if unwrapped and unwrapped != iframe and (
                    self.isVideoFormat(unwrapped)
                    or re.search(r'\.(?:m3u8|mp4|flv|mkv)(?:\?|$)', unwrapped, re.I)
                ):
                    media = self._fix(unwrapped, play_url)
                    result = self._play_result(media, play_url, parse=0)
                    self._play_store_success(key, result)
                    self._play_log("SUCCESS", "iframe 嵌套 url= 解出媒体", media=media[:120])
                    return result
                # iframe 本身就是媒体直链
                if self.isVideoFormat(iframe) or re.search(
                    r'\.(?:m3u8|mp4|flv|mkv)(?:\?|$)', iframe, re.I
                ):
                    media = self._fix(self._unwrap_nested_media(iframe) or iframe, play_url)
                    result = self._play_result(media, play_url, parse=0)
                    self._play_store_success(key, result)
                    self._play_log("SUCCESS", "iframe 即媒体地址", media=media[:120])
                    return result

                if "player.html" in iframe or "langfeng" in iframe or "ttss." in iframe:
                    media = self._resolve_langfeng_proxy(iframe, referer=play_url)
                    if media:
                        result = self._play_result(media, iframe, parse=0)
                        self._play_store_success(key, result)
                        self._play_log("SUCCESS", "langfeng proxy 得到媒体地址", media=media[:120])
                        return result

                inner = self._get(iframe, referer=play_url)
                if inner:
                    media = self._extract_media_url(inner, iframe)
                    if media:
                        result = self._play_result(media, iframe, parse=0)
                        self._play_store_success(key, result)
                        self._play_log("SUCCESS", "iframe 直接得到媒体地址", iframe=iframe, media=media)
                        return result

                    # iframe 源码里的 fetchPlayUrl /proxy/ 模式
                    media = self._resolve_langfeng_proxy(iframe, referer=play_url)
                    if media:
                        result = self._play_result(media, iframe, parse=0)
                        self._play_store_success(key, result)
                        return result

                    media = self._resolve_dynamic_requests(inner, iframe, depth=0, seen={iframe})
                    if media:
                        result = self._play_result(media, iframe, parse=0)
                        self._play_store_success(key, result)
                        self._play_log("SUCCESS", "iframe 动态请求得到媒体地址", iframe=iframe, media=media)
                        return result

                    nested = self._extract_iframe(inner, iframe)
                    if nested and nested != iframe:
                        media = self._resolve_play_page(nested, 1, {iframe})
                        if media:
                            result = self._play_result(media, nested, parse=0)
                            self._play_store_success(key, result)
                            self._play_log("SUCCESS", "嵌套 iframe 得到媒体地址", nested=nested, media=media)
                            return result

                # 静态未解出时交给壳端 WebView 嗅探
                self._play_log(
                    "RUNTIME_PLAYER_UNRESOLVED",
                    "静态未取得媒体地址，回退 WebView",
                    play=play_url, iframe=iframe,
                )
                result = self._play_result(
                    iframe, play_url, parse=1, jx=0, click=iframe
                )
                self._play_store_failure(key, result)
                return result

            media = self._resolve_dynamic_requests(source, play_url, depth=0, seen=source_seen)
            if media:
                result = self._play_result(media, play_url, parse=0)
                self._play_store_success(key, result)
                self._play_log("SUCCESS", "播放页动态请求得到媒体地址", play=play_url, media=media)
                return result

        self._play_log(
            "PLAYER_FETCH_FAILED",
            "播放页没有取得有效内容（确认是否用了移动 UA）",
            play=play_url,
        )
        result = self._play_result(play_url, self.base_url + "/", parse=1)
        self._play_store_failure(key, result)
        return result

    # ------------------------------------------------------------------
    # 搜索
    # ------------------------------------------------------------------

    def searchContent(self, wd, quick=None, pg="1", *args):
        try:
            page = int(pg) if pg else 1
        except Exception:
            page = 1

        key = str(wd or "").strip()
        if not key:
            return {
                "page": page,
                "pagecount": 0,
                "limit": 24,
                "total": 0,
                "list": [],
            }

        # 站点搜索走 /search/{base64url(keyword)}/{page}.html
        # 注意：频繁搜索可能触发 human-check 滑块，静态 Spider 无法过验证。
        def _b64url_kw(text):
            s = quote(str(text or ""), safe="")
            raw = bytearray()
            i = 0
            while i < len(s):
                if s[i] == "%" and i + 2 < len(s):
                    try:
                        raw.append(int(s[i + 1:i + 3], 16))
                        i += 3
                        continue
                    except Exception:
                        pass
                raw.append(ord(s[i]))
                i += 1
            token = base64.b64encode(bytes(raw)).decode("ascii")
            return token.replace("+", "-").replace("/", "_").rstrip("=")

        token = _b64url_kw(key)
        q = quote(key)
        urls = [
            f"{self.base_url}/search/{token}/{page}.html",
            f"{self.base_url}/search.php?searchword={q}"
            + (f"&page={page}" if page > 1 else ""),
            f"{self.base_url}/vodsearch/{q}----------{page}.html",
        ]

        videos = []
        source = ""

        for url in urls:
            source = self._get(url)
            if source and ("human-check" in source or "访问验证" in source):
                self._play_log("SEARCH_CAPTCHA", "搜索触发人机验证，跳过该地址", url=url)
                continue
            videos = self.parse_video_list(source)
            if videos:
                break

        pagecount = self._pagecount(source, page, videos)

        return {
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": len(videos),
            "list": videos,
        }

    def searchContentPage(self, wd, quick, pg):
        return self.searchContent(wd, quick, pg)


def get_spider():
    return Spider()
