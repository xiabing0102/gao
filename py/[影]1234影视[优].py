"""
导航:   https://www.qiushui.vip
           https://www.qiushuitv.cn
           https://www.qiushuiying.cn
由「影视py源生成器」自动生成 2026-09-15 17:53
站点: https://www.1234sp.cc
接口: 
"""

import re
import json
import time
import base64
import ssl
import http.cookiejar
import urllib.parse
import urllib.request

import requests
from bs4 import BeautifulSoup

try:
    from base.spider import Spider as _BaseSpider
except ImportError:
    class _BaseSpider(object):
        """脱离影视壳独立运行时的占位基类，便于本地自检"""

class Spider(_BaseSpider):
    name = "1234影视"
    base_url = "https://www.1234sp.cc"
    host = "https://www.1234sp.cc"
    site_url = "https://www.1234sp.cc"
    timeout = 18
    UA_MOBILE = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
        "Mobile/15E148 Safari/604.1"
    )
    class_name = ["连续剧", "电影", "动漫", "综艺"]
    class_url = ["A2xeflx0UY1tu", "A2mOC0y4HbZ3l", "A2ttqWI1YGgTu", "A2b7iFz0ozYru"]
    page_size = 36
    _session = None
    _permit = None
    _ssl_ctx = None
    _cookie_domain = ""
    # 详情缓存（vid -> 解析后的详情 dict），避免跨线路回退时重复请求
    _detail_cache = {}

    def getName(self):
        return self.name

    def init(self, extend=""):
        self._extend = extend or ""
        host = urllib.parse.urlparse(self.base_url).netloc.split(":")[0]
        parts = host.split(".")
        self._cookie_domain = "." + ".".join(parts[-2:]) if len(parts) >= 2 else host
        if self._ssl_ctx is None:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            self._ssl_ctx = ctx
        if self._session is None:
            s = requests.Session()
            s.headers.clear()
            s.headers.update({
                "User-Agent": self.UA_MOBILE,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept-Encoding": "identity",
                "Referer": self.base_url + "/",
            })
            self._session = s

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass

    def localProxy(self, param):
        return None

    def _ssl(self):
        if self._ssl_ctx is None:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            self._ssl_ctx = ctx
        return self._ssl_ctx

    def _sess(self):
        if self._session is None:
            self.init("")
        return self._session

    def getHeaders(self):
        return {
            "User-Agent": self.UA_MOBILE,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.base_url + "/",
        }

    def _get(self, url, referer=None, allow_redirects=True):
        s = self._sess()
        hd = {"Referer": referer or (self.base_url + "/")}
        try:
            return s.get(url, headers=hd, timeout=self.timeout,
                         allow_redirects=allow_redirects)
        except Exception as e:
            print(f"[{self.name}] GET 异常 {url}: {e}")
            return None

    # ==================================================================
    #                       人形验证
    # ==================================================================

    def _solve_human_check(self, return_path):
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj),
            urllib.request.HTTPSHandler(context=self._ssl()),
        )
        opener.addheaders = [
            ("User-Agent", self.UA_MOBILE),
            ("Accept-Language", "zh-CN,zh;q=0.9"),
        ]

        def uget(u, ref=None):
            h = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
            if ref:
                h["Referer"] = ref
            return opener.open(urllib.request.Request(u, headers=h),
                               timeout=self.timeout).read()

        ch_url = self.base_url + "/human-check?" + urllib.parse.urlencode({"return": return_path})
        try:
            ch_html = uget(ch_url, ref=self.base_url + return_path).decode("utf-8", "ignore")
        except Exception as e:
            print(f"[{self.name}] 拉取人形验证页失败: {e}")
            return False

        m1 = re.search(r'name="challenge" value="([^"]+)"', ch_html)
        m2 = re.search(r'name="return" value="([^"]+)"', ch_html)
        if not m1 or not m2:
            print(f"[{self.name}] 人形验证页未找到 challenge 表单")
            return False

        data = urllib.parse.urlencode({
            "challenge": m1.group(1),
            "return": m2.group(1),
            "duration_ms": "850",
            "move_points": "47",
            "final_percent": "100",
            "pressed": "true",
            "released": "true",
        }).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/human-check/verify", data=data, method="POST",
            headers={
                "User-Agent": self.UA_MOBILE,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": self.base_url,
                "Referer": ch_url,
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        try:
            opener.open(req, timeout=self.timeout).read()
        except Exception as e:
            print(f"[{self.name}] 人形验证 POST 异常: {e}")
            return False

        permit = None
        permit_exp = None
        for c in cj:
            if c.name == "maccms_human_permit":
                permit = c.value
                permit_exp = c.expires or (int(time.time()) + 7200)
                break

        if not permit:
            print(f"[{self.name}] 人形验证未通过（无 permit cookie 下发）")
            return False

        s = self._sess()
        s.cookies.set("maccms_human_permit", permit,
                      domain=self._cookie_domain, path="/", expires=permit_exp)
        self._permit = {"cookie": permit, "exp": int(permit_exp)}
        print(f"[{self.name}] 人形验证通过，permit 缓存至 {time.ctime(self._permit['exp'])}")
        return True

    def _ensure_permit(self, return_path):
        now = int(time.time())
        if self._permit and self._permit.get("exp", 0) - 60 > now:
            return True
        return self._solve_human_check(return_path)

    # ==================================================================
    #                       列表/首页/搜索
    # ==================================================================

    CARD_RE = re.compile(
        r'<article class="pixel-card">\s*'
        r'<a class="pixel-card__link" href="/v/(?P<vid>[A-Za-z0-9]+)\.html"[^>]*?title="(?P<title>[^"]+)"'
        r'.*?<img src="(?P<pic>[^"]+)"[^>]*?>'
        r'.*?<span class="pixel-card__remark">(?P<remark>[^<]*)</span>',
        re.S,
    )

    def _parse_card_grid(self, html):
        items = []
        for m in self.CARD_RE.finditer(html or ""):
            items.append({
                "vod_id": m.group("vid"),
                "vod_name": m.group("title"),
                "vod_pic": m.group("pic"),
                "vod_remarks": (m.group("remark") or "").strip(),
            })
        return items

    def _parse_page_count(self, html):
        if not html:
            return 1
        nav = re.search(r'<nav class="pixel-pagination"[^>]*>(?P<body>.*?)</nav>',
                        html, re.S)
        if not nav:
            return 1
        nums = [int(x) for x in
                re.findall(r'aria-label="第\s*(\d+)\s*页"', nav.group("body"))]
        return max(nums) if nums else 1

    def homeContent(self, filter=True):
        result = {"list": [], "class": [], "filters": {}}
        try:
            r = self._get(self.base_url + "/")
            if r is None or r.status_code != 200:
                return result
            html = r.text
            hero = re.search(r'<div class="pixel-home__lead">(.*?)</div>\s*</section>',
                             html, re.S)
            seed = hero.group(1) if hero else html
            result["list"] = self._parse_card_grid(seed)[:30]
            result["class"] = [
                {"type_id": u, "type_name": n}
                for n, u in zip(self.class_name, self.class_url)
            ]
            result["filters"] = {u: [] for u in self.class_url}
            print(f"[{self.name}] 首页加载：{len(result['list'])} 条推荐，"
                  f"{len(result['class'])} 个分类")
        except Exception as e:
            print(f"[{self.name}] 首页异常: {e}")
        return result

    def homeVideoContent(self):
        return self.homeContent(True)

    def categoryContent(self, tid, pg, filter=True, extend=None):
        page = int(pg) if str(pg).isdigit() else 1
        result = {"list": [], "page": page, "pagecount": 1,
                  "limit": self.page_size, "total": 0}
        try:
            url = f"{self.base_url}/list/{tid}/{page}.html"
            r = self._get(url, referer=self.base_url + "/")
            if r is None or r.status_code != 200:
                return result
            cards = self._parse_card_grid(r.text)
            result["list"] = cards
            total_pages = self._parse_page_count(r.text)
            result["pagecount"] = total_pages
            result["total"] = total_pages * self.page_size
            print(f"[{self.name}] 分类 {tid} 第 {page}/{total_pages} 页：{len(cards)} 条")
        except Exception as e:
            print(f"[{self.name}] 分类异常: {e}")
        return result

    # ==================================================================
    #                       详情（多线路采集）
    # ==================================================================

    # 剧集链接正则，兼容多种 href 形式
    _EP_HREF_RES = [
        re.compile(r"/p/([A-Za-z0-9]+)/(\d+)/(\d+)\.html"),        # /p/vid/line/nid.html
        re.compile(r"/p/([A-Za-z0-9]+)/(\d+)-(\d+)\.html"),         # /p/vid/line-nid.html
        re.compile(r"/play/([A-Za-z0-9]+)/(\d+)/(\d+)\.html"),      # /play/vid/line/nid.html
    ]

    def _parse_ep_pid(self, href):
        """从剧集 href 中提取 pid = vid|line|nid"""
        if not href:
            return None
        for pat in self._EP_HREF_RES:
            m = pat.search(href)
            if m:
                return f"{m.group(1)}|{m.group(2)}|{m.group(3)}"
        return None

    def _fetch_detail_html(self, vid):
        """抓取详情页并缓存原始 HTML"""
        cache_key = f"html:{vid}"
        if cache_key in self._detail_cache:
            return self._detail_cache[cache_key]
        url = f"{self.base_url}/v/{vid}.html"
        r = self._get(url, referer=self.base_url + "/")
        if r is None or r.status_code != 200:
            self._detail_cache[cache_key] = None
            return None
        self._detail_cache[cache_key] = r.text
        return r.text

    def _extract_play_groups(self, soup):
        """
        从详情页提取所有播放线路与剧集。
        返回 [(线路名, [(集名, pid), ...]), ...]
        """
        groups = []
        playlist = soup.select_one("[data-playlist]")
        if not playlist:
            return groups

        tabs = playlist.select("[data-playlist-tab]")
        panels = {p.get("data-playlist-panel"): p
                  for p in playlist.select("[data-playlist-panel]")}

        used_labels = set()
        for tab in tabs:
            line_no = tab.get("data-playlist-tab")
            raw_label = tab.get_text(strip=True) or f"线路{line_no}"
            panel = panels.get(line_no)
            if not panel:
                continue

            eps = []
            seen_pids = set()
            for a in panel.select(".pixel-playlist__episodes a"):
                ep_name = a.get_text(strip=True)
                href = a.get("href", "")
                pid = self._parse_ep_pid(href)
                if not pid or pid in seen_pids:
                    continue
                seen_pids.add(pid)
                if not ep_name:
                    ep_name = pid.split("|")[-1]
                eps.append((ep_name, pid))

            if not eps:
                continue

            # 线路名去重
            label = raw_label
            n = 1
            while label in used_labels:
                n += 1
                label = f"{raw_label}-{n}"
            used_labels.add(label)
            groups.append((label, eps))

        # 若无 data-playlist，退化为扫全页 /p/ 链接
        if not groups:
            eps, seen = [], set()
            for a in soup.find_all("a", href=True):
                pid = self._parse_ep_pid(a["href"])
                if not pid or pid in seen:
                    continue
                seen.add(pid)
                name = a.get_text(strip=True) or pid.split("|")[-1]
                eps.append((name, pid))
            if eps:
                groups.append(("默认线路", eps))

        return groups

    def detailContent(self, ids):
        try:
            vid = ids[0] if isinstance(ids, list) else ids
        except Exception:
            vid = str(ids)

        html = self._fetch_detail_html(vid)
        if not html:
            return {"list": []}
        soup = BeautifulSoup(html, "html.parser")

        vod = {
            "vod_id": vid, "vod_name": "", "vod_pic": "", "vod_year": "",
            "vod_area": "", "vod_class": "", "vod_remarks": "", "vod_director": "",
            "vod_actor": "", "vod_content": "", "vod_play_from": "", "vod_play_url": "",
        }

        h1 = soup.find("h1")
        if h1:
            vod["vod_name"] = h1.get_text(strip=True)

        poster = soup.select_one(".pixel-detail__poster img")
        if poster:
            vod["vod_pic"] = poster.get("src", "")

        for row in soup.select(".pixel-meta div"):
            dt = row.find("dt")
            dd = row.find("dd")
            if not dt or not dd:
                continue
            k = dt.get_text(strip=True)
            v = dd.get_text(strip=True)
            if k == "主演":
                vod["vod_actor"] = v
            elif k == "导演":
                vod["vod_director"] = v
            elif k == "类型":
                vod["vod_class"] = v
            elif k in ("地区 / 年份", "地区/年份"):
                parts = [p.strip() for p in v.split("/") if p.strip()]
                if parts:
                    vod["vod_area"] = parts[0]
                if len(parts) > 1:
                    vod["vod_year"] = parts[-1]
            elif k == "状态":
                vod["vod_remarks"] = v

        intro = soup.select_one("[data-vod-intro]")
        if intro:
            vod["vod_content"] = intro.get_text(strip=True)

        # ---- 多线路采集 ----
        groups = self._extract_play_groups(soup)
        from_names, url_groups = [], []
        for label, eps in groups:
            from_names.append(label)
            url_groups.append("#".join(f"{n}${p}" for n, p in eps))

        vod["vod_play_from"] = "$$$".join(from_names)
        vod["vod_play_url"] = "$$$".join(url_groups)
        print(f"[{self.name}] 详情 {vid}：{vod['vod_name']} | 线路 {len(from_names)} 条 "
              f"(每线集数：{[len(g[1]) for g in groups]})")

        # 缓存解析后的详情，供跨线路回退使用
        self._detail_cache[f"vod:{vid}"] = vod
        return {"list": [vod]}

    # ==================================================================
    #                       搜索
    # ==================================================================

    def searchContent(self, key, quick=None, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        result = {"list": []}
        bkey = base64.urlsafe_b64encode(str(key or "").encode("utf-8")) \
            .decode("ascii").rstrip("=")
        ret_path = f"/search/{bkey}/{page}.html"
        search_url = self.base_url + ret_path
        self._ensure_permit(ret_path)
        r = self._get(search_url, referer=self.base_url + "/")
        if r is None:
            return result
        if r.status_code in (301, 302, 303, 307) or "/human-check" in r.url \
                or "<title>访问验证" in r.text:
            if self._solve_human_check(ret_path):
                r = self._get(search_url, referer=self.base_url + "/")
                if r is None:
                    return result
        result["list"] = self._parse_card_grid(r.text)
        print(f"[{self.name}] 搜索 {key} 第 {page} 页：{len(result['list'])} 条")
        return result

    # ==================================================================
    #                       播放解析
    # ==================================================================

    def _fetch_play_iframe(self, vid, line, nid):
        url = f"{self.base_url}/p/{vid}/{line}/{nid}.html"
        r = self._get(url, referer=f"{self.base_url}/v/{vid}.html")
        if r is None or not r.text:
            return None
        m = re.search(r'<iframe[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', r.text, re.I)
        return m.group(1).strip() if m else None

    @staticmethod
    def _extract_query_url(iframe_src):
        try:
            qs = urllib.parse.urlparse(iframe_src).query
            params = urllib.parse.parse_qs(qs)
            for k in ("url", "URL", "src", "play", "m3u8"):
                if k in params and params[k]:
                    return params[k][0]
        except Exception:
            pass
        return None

    @staticmethod
    def _collect_play_urls(obj, out=None):
        if out is None:
            out = []
        if isinstance(obj, dict):
            for key in ("url", "play_url", "playUrl", "playurl", "src",
                        "video", "video_url", "m3u8", "mp4", "file"):
                v = obj.get(key)
                if isinstance(v, str) and v.strip():
                    out.append(v.strip().replace("\\/", "/"))
            for v in obj.values():
                if isinstance(v, (dict, list)):
                    Spider._collect_play_urls(v, out)
        elif isinstance(obj, list):
            for it in obj:
                Spider._collect_play_urls(it, out)
        return out

    def _proxy_candidates(self, iframe):
        try:
            u = urllib.parse.urlsplit(iframe)
        except Exception:
            return []
        qs = urllib.parse.parse_qs(u.query)
        v = ""
        for k in ("v", "vid", "id", "hash", "code"):
            if qs.get(k):
                v = qs[k][0]
                break
        if not v:
            return []
        base_dir = u.path.rsplit("/", 1)[0]
        root = f"{u.scheme}://{u.netloc}"
        cands = [
            f"{root}{base_dir}/proxy/{v}",
            f"{root}/proxy/{v}",
            f"{root}{base_dir}/api/proxy/{v}",
            f"{root}/api/proxy/{v}",
            f"{root}{base_dir}/player.php?v={v}",
            f"{root}/player.php?v={v}",
        ]
        seen, uniq = set(), []
        for c in cands:
            if c not in seen:
                seen.add(c)
                uniq.append(c)
        return uniq

    def _resolve_from_proxy(self, iframe, header):
        for purl in self._proxy_candidates(iframe):
            try:
                pr = self._sess().get(purl, headers={
                    "User-Agent": self.UA_MOBILE,
                    "Accept": "application/json, text/plain, */*",
                    "Referer": iframe,
                    "X-Requested-With": "XMLHttpRequest",
                }, timeout=self.timeout)
            except Exception as e:
                print(f"[{self.name}] proxy 请求异常 {purl}: {e}")
                continue
            if pr is None or not (pr.text or "").strip():
                continue
            data = None
            try:
                data = pr.json()
            except Exception:
                m = re.search(
                    r'["\']?(?:url|play_url|playUrl|m3u8|src)["\']?\s*[:=]\s*["\']([^"\']+)',
                    pr.text, re.I)
                if m:
                    data = {"url": m.group(1)}
            if not data:
                continue
            urls = self._collect_play_urls(data)
            for u in urls:
                if ".m3u8" in u or ".mp4" in u:
                    print(f"[{self.name}] proxy 解析成功：{u[:90]}")
                    return u
            for u in urls:
                if u.startswith("http"):
                    print(f"[{self.name}] proxy 返回候选：{u[:90]}")
                    return u
        return None

    def _resolve_from_player_page(self, iframe, header):
        try:
            r = self._sess().get(iframe, headers={
                "User-Agent": self.UA_MOBILE,
                "Referer": self.base_url + "/",
            }, timeout=self.timeout)
        except Exception as e:
            print(f"[{self.name}] player.html 拉取异常: {e}")
            return None
        if r is None or not r.text:
            return None
        html = r.text
        for m in re.finditer(r'https?:\\?/\\?/[^"\'\s\\<>]+?\.(?:m3u8|mp4)[^"\'\s\\<>]*',
                             html, re.I):
            u = m.group(0).replace("\\/", "/")
            if u.startswith("http"):
                print(f"[{self.name}] player 页面直链：{u[:90]}")
                return u
        for m in re.finditer(
                r'["\'](?:url|play_url|playUrl|playurl|src|file)["\']\s*[:=]\s*["\']([^"\']+)["\']',
                html, re.I):
            u = m.group(1).replace("\\/", "/")
            if u.startswith("http") and (".m3u8" in u or ".mp4" in u):
                print(f"[{self.name}] player 页面字段直链：{u[:90]}")
                return u
        return None

    def _resolve_single(self, vid, line, nid, header):
        """
        解析单个 pid(vid|line|nid) → 返回直链 URL 或 None。
        解析顺序：iframe query 直链 → 站点 proxy → player 页面 → 壳解析(iframe)
        """
        iframe = self._fetch_play_iframe(vid, line, nid)
        if not iframe:
            return None, None

        direct = self._extract_query_url(iframe)
        if direct and (".m3u8" in direct or ".mp4" in direct):
            print(f"[{self.name}] iframe query 直链：{direct[:90]}")
            return direct, iframe

        play_url = self._resolve_from_proxy(iframe, header)
        if play_url:
            return play_url, iframe

        play_url = self._resolve_from_player_page(iframe, header)
        if play_url:
            return play_url, iframe

        return None, iframe

    def _get_cached_vod(self, vid):
        """获取（可能已缓存的）解析后的详情 vod dict"""
        key = f"vod:{vid}"
        if key in self._detail_cache:
            return self._detail_cache[key]
        res = self.detailContent([vid])
        if res and res.get("list"):
            return res["list"][0]
        return None

    def _collect_other_line_pids(self, vid, cur_line, nid):
        """
        多线路采集回退：找出同一 vid 中「除当前线路外」的、集号 nid 匹配的所有 pid。
        返回 [(线路序号, 线路名, 集名, pid), ...]
        """
        vod = self._get_cached_vod(vid)
        if not vod:
            return []
        from_names = vod.get("vod_play_from", "").split("$$$")
        url_groups = vod.get("vod_play_url", "").split("$$$")

        cur_line_s = str(cur_line)
        out = []
        for idx, (label, group) in enumerate(zip(from_names, url_groups)):
            line_no = str(idx + 1)
            if line_no == cur_line_s:
                continue
            if not group:
                continue
            for ep in group.split("#"):
                parts = ep.split("$")
                if len(parts) != 2:
                    continue
                ep_name, pid = parts
                ps = pid.split("|")
                if len(ps) != 3:
                    continue
                # 集号匹配（nid）
                if ps[2] == str(nid):
                    out.append((line_no, label, ep_name, pid))
                    break  # 每条线路只取第一个匹配
        return out

    def playerContent(self, flag, id, vipFlags=None):
        header = {"User-Agent": self.UA_MOBILE}
        parts = str(id).split("|")
        if len(parts) != 3:
            return {"parse": 0, "url": str(id), "header": header}

        vid, line, nid = parts

        # 1) 解析当前 pid
        play_url, iframe = self._resolve_single(vid, line, nid, header)
        if play_url:
            return {"parse": 0, "url": play_url, "header": header}

        # 2) 多线路采集回退：尝试同集在其他线路的播放地址
        print(f"[{self.name}] 当前线路解析失败，启动多线路采集回退 ...")
        candidates = self._collect_other_line_pids(vid, line, nid)
        for line_no, label, ep_name, pid in candidates:
            ps = pid.split("|")
            if len(ps) != 3:
                continue
            print(f"[{self.name}] 回退线路 {line_no}({label}) - {ep_name}")
            u, ifr = self._resolve_single(ps[0], ps[1], ps[2], header)
            if u:
                return {"parse": 0, "url": u, "header": header}

        # 3) 全部失败 → 交给壳自身解析 iframe
        if iframe:
            print(f"[{self.name}] 所有线路直链均失败，回退到壳解析：{iframe}")
            return {"parse": 1, "url": iframe, "header": header}
        print(f"[{self.name}] 未找到播放 iframe：vid={vid} line={line} nid={nid}")
        return {"parse": 0, "url": "", "header": header}