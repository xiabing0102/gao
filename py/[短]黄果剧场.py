"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '黄果剧场',
  lang: 'hipy'
})
"""
import sys
import re
import json
import threading
import urllib.request
import urllib.parse

try:
    import concurrent.futures as _cf
except ImportError:
    _cf = None

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        pass


class Spider(SpiderBase):
    def init(self, extend=""):
        self.siteName = "黄果剧场"
        self.siteUrl = "https://huangguo.video"
        self._ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36")

        self.categories = [
            {"type_id": "1", "type_name": "MV/音乐剧"},
            {"type_id": "2", "type_name": "短片"},
            {"type_id": "3", "type_name": "连续剧"},
            {"type_id": "4", "type_name": "片段"},
        ]

        self.tag_options = [
            {"n": "全部",     "v": ""},
            {"n": "都市",     "v": "1"},
            {"n": "人妻",     "v": "2"},
            {"n": "校园",     "v": "5"},
            {"n": "职场",     "v": "6"},
            {"n": "古风",     "v": "7"},
            {"n": "乱伦",     "v": "8"},
            {"n": "NTR",      "v": "9"},
            {"n": "玄幻",     "v": "40"},
        ]

        # raw(video页或m3u8) -> (final_url, referer)
        self._play_url_cache = {}
        # 正在后台预热的 URL，防止重复起线程
        self._prefetching = set()
        self._prefetch_lock = threading.Lock()

    def getName(self):
        return self.siteName

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".ts"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    # ==================== HTTP ====================

    def _http_get(self, url, referer=None, timeout=12):
        headers = {
            "User-Agent": self._ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": referer or (self.siteUrl + "/"),
            "Cookie": "hg_age=1",
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"[黄果剧场] 请求失败 {url}: {e}")
            return ""

    # ==================== 列表解析 ====================

    def _parse_list(self, html):
        if not html:
            return []

        items = []
        seen = set()

        for art in re.finditer(
            r'<article class="(?:video-card|search-content-card)[^"]*">(.*?)</article>',
            html, re.S
        ):
            block = art.group(1)

            link_m = re.search(r'<a\s+href="(/(?:video|series)/[^"]+)"', block)
            if not link_m:
                continue
            path = link_m.group(1).strip()

            if path.startswith('/video/'):
                vid = 'video:' + path[len('/video/'):].strip('/')
            elif path.startswith('/series/'):
                vid = 'series:' + path[len('/series/'):].strip('/')
            else:
                continue

            if vid in seen:
                continue

            img_m = re.search(r'<img[^>]+src="([^"]+)"', block)
            cover = img_m.group(1).strip() if img_m else ""
            if cover.startswith('/'):
                cover = self.siteUrl + cover

            title = ""
            alt_m = re.search(r'<img[^>]+alt="([^"]*)"', block)
            if alt_m:
                title = alt_m.group(1).strip()
            if not title:
                t_m = re.search(
                    r'<p[^>]*class="[^"]*(?:text-cream|font-display)[^"]*"[^>]*>([^<]+)</p>',
                    block
                )
                if t_m:
                    title = t_m.group(1).strip()

            tag = ""
            tag_m = re.search(
                r'<span class="absolute bottom-2 right-2[^"]*">([^<]+)</span>', block)
            if tag_m:
                tag = tag_m.group(1).strip()

            sub = ""
            sub_m = re.search(
                r'<p class="mt-2[^"]*font-mono-meta[^"]*">(.*?)</p>', block, re.S)
            if sub_m:
                sub = re.sub(r'<[^>]+>', '', sub_m.group(1)).strip()

            parts = []
            if tag:
                parts.append(tag)
            if sub:
                parts.append(sub)

            seen.add(vid)
            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": cover,
                "vod_remarks": " · ".join(parts),
            })

        return items

    # ==================== 详情页解析 ====================

    def _extract_title(self, html):
        t_m = re.search(r'<title>(.*?)</title>', html, re.S)
        if t_m:
            title = t_m.group(1).strip()
            title = re.sub(r'\s*[-–|·]\s*黄果剧场.*$', '', title).strip()
            return title
        return ""

    def _extract_cover(self, html):
        m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
        if m:
            return m.group(1).strip()
        m = re.search(r'data-poster="([^"]+)"', html)
        if m:
            pic = m.group(1).strip()
            return pic if pic.startswith('http') else self.siteUrl + pic
        return ""

    def _extract_intro(self, html):
        m = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html)
        return m.group(1).strip() if m else ""

    def _extract_hls(self, html):
        if not html:
            return ""
        m = re.search(r'data-hls="([^"]+)"', html)
        if m:
            url = m.group(1).strip()
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                url = self.siteUrl + url
            return url
        return ""

    # ============== 剧集列表：兼容属性顺序 + 集号排序 ==============

    def _extract_episodes(self, html):
        if not html:
            return []

        eps = []
        seen = set()

        for m in re.finditer(r'<a\b([^>]*)>(.*?)</a>', html, re.S):
            attrs = m.group(1)
            inner = m.group(2)

            href_m = re.search(r'href="(/video/[^"]+)"', attrs)
            if not href_m:
                continue

            path = href_m.group(1).strip()
            if path in seen:
                continue

            cls_m = re.search(r'class="([^"]*)"', attrs)
            cls = cls_m.group(1) if cls_m else ""

            inner_text = re.sub(r'<[^>]+>', ' ', inner)
            inner_text = re.sub(r'\s+', ' ', inner_text).strip()

            is_ep = ('ep-chip' in cls) or ('group' in cls)
            if not is_ep:
                if not re.search(r'第\s*\d+\s*[集话季]|EP\s*\d+|E\s*\d+',
                                 inner_text, re.I):
                    continue

            name = ""
            if 'ep-chip' in cls:
                name = inner_text
            else:
                for pat in (
                    r'<p[^>]*class="[^"]*font-display[^"]*"[^>]*>([^<]+)</p>',
                    r'<p[^>]*class="[^"]*text-[^"]*"[^>]*>([^<]+)</p>',
                    r'<p[^>]*>([^<]+)</p>',
                ):
                    nm = re.search(pat, inner, re.S)
                    if nm:
                        name = nm.group(1).strip()
                        break

            if not name and inner_text and len(inner_text) <= 30:
                name = inner_text

            if not name:
                name = f"第{len(eps) + 1}集"

            seen.add(path)
            eps.append({
                "name": name,
                "ep_id": path[len('/video/'):].strip('/'),
                "url": self.siteUrl + path,
            })

        return self._sort_episodes(eps)

    def _sort_episodes(self, eps):
        if not eps:
            return eps

        decorated = []
        has_number = False
        for idx, ep in enumerate(eps):
            m = re.search(r'(\d+)', ep.get('name', '') or '')
            if m:
                has_number = True
                decorated.append((0, int(m.group(1)), idx, ep))
            else:
                decorated.append((1, idx, idx, ep))

        if has_number:
            decorated.sort(key=lambda x: (x[0], x[1], x[2]))
        else:
            decorated.sort(key=lambda x: x[2])

        return [d[3] for d in decorated]

    def _extract_series_url(self, html):
        m = re.search(r'data-series-url="([^"]+)"', html)
        if m:
            url = m.group(1).strip()
            return url if url.startswith('http') else self.siteUrl + url
        return ""

    # ==================== m3u8 并行展开找 mp4 ====================

    def _extract_mp4_from_playlist(self, content, playlist_url):
        if not content:
            return ""
        m = re.search(r'https?://[^\s"\'<>\\]+\.mp4[^\s"\'<>\\]*', content)
        if m:
            return m.group(0)
        sub_base = playlist_url.rsplit('/', 1)[0]
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '.mp4' in line:
                if line.startswith('http'):
                    return line
                elif line.startswith('/'):
                    return self.siteUrl + line
                else:
                    return sub_base + '/' + line
        return ""

    def _resolve_mp4_from_m3u8(self, master_url, referer):
        """并行请求子播放列表，找到第一个 mp4 立即返回。"""
        if not master_url:
            return ""

        content = self._http_get(master_url, referer=referer, timeout=6)
        if not content:
            return ""

        m = re.search(r'https?://[^\s"\'<>\\]+\.mp4[^\s"\'<>\\]*', content)
        if m:
            return m.group(0)

        base = master_url.rsplit('/', 1)[0]
        sub_urls = []
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('http') and '.m3u8' in line:
                sub_urls.append(line)
            elif line.endswith('.m3u8'):
                sub_urls.append(base + '/' + line.lstrip('/'))

        if not sub_urls:
            return ""

        priority = ['720p', '1080p', '480p', '360p']

        def score(u):
            for i, p in enumerate(priority):
                if p in u:
                    return i
            return 99

        sub_urls.sort(key=score)

        contents = {}

        if _cf is not None:
            try:
                with _cf.ThreadPoolExecutor(max_workers=min(4, len(sub_urls))) as ex:
                    fut_map = {
                        ex.submit(self._http_get, u, referer, 6): u
                        for u in sub_urls
                    }
                    for fut in _cf.as_completed(fut_map, timeout=8):
                        u = fut_map[fut]
                        try:
                            contents[u] = fut.result()
                        except Exception:
                            contents[u] = ""
            except Exception:
                contents = {}
        else:
            for u in sub_urls:
                contents[u] = self._http_get(u, referer=referer, timeout=6)

        for u in sub_urls:
            sub_content = contents.get(u, "")
            if not sub_content:
                continue
            mp4 = self._extract_mp4_from_playlist(sub_content, u)
            if mp4:
                return mp4

        return ""

    # ==================== 播放地址解析（公共） ====================

    def _resolve_play_url(self, raw):
        """
        返回 (final_url, referer) 或 None。
        命中缓存直接返回；否则按类型解析。
        结果写入 self._play_url_cache[raw]。
        """
        if not raw:
            return None

        if raw in self._play_url_cache:
            return self._play_url_cache[raw]

        # 1) video 页 URL
        if raw.startswith('http') and '/video/' in raw and not self.isVideoFormat(raw):
            html = self._http_get(raw, timeout=6)
            master = self._extract_hls(html)
            if master:
                mp4 = self._resolve_mp4_from_m3u8(master, referer=raw)
                if mp4:
                    result = (mp4, self.siteUrl + "/")
                else:
                    result = (master, raw)
                self._play_url_cache[raw] = result
                return result
            return None

        # 2) m3u8 直链
        if self.isVideoFormat(raw) and '.m3u8' in raw:
            mp4 = self._resolve_mp4_from_m3u8(raw, referer=self.siteUrl + "/")
            result = (mp4, self.siteUrl + "/") if mp4 else (raw, self.siteUrl + "/")
            self._play_url_cache[raw] = result
            return result

        # 3) mp4 直链
        if self.isVideoFormat(raw) and '.mp4' in raw:
            result = (raw, self.siteUrl + "/")
            self._play_url_cache[raw] = result
            return result

        return None

    # ==================== 后台预热 ====================

    def _prefetch_play_url(self, ep_url):
        """后台线程预解析一集，结果写入缓存；不阻塞 detailContent。"""
        if not ep_url or not ep_url.startswith('http'):
            return
        if ep_url in self._play_url_cache:
            return
        with self._prefetch_lock:
            if ep_url in self._prefetching:
                return
            self._prefetching.add(ep_url)

        def worker():
            try:
                self._resolve_play_url(ep_url)
            except Exception as e:
                print(f"[黄果剧场] 预热失败 {ep_url}: {e}")
            finally:
                with self._prefetch_lock:
                    self._prefetching.discard(ep_url)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    # ==================== TVBox 接口 ====================

    def homeContent(self, filter):
        filters = {
            "1": self._build_filters(),
            "2": self._build_filters(),
            "3": self._build_filters(),
            "4": self._build_filters(),
        }
        return {"class": self.categories, "filters": filters}

    def _build_filters(self):
        return [
            {
                "key": "rating",
                "name": "尺度",
                "value": [
                    {"n": "全部",  "v": ""},
                    {"n": "安全",  "v": "safe"},
                    {"n": "裸露",  "v": "nude"},
                    {"n": "限制级", "v": "explicit"},
                ]
            },
            {
                "key": "tags",
                "name": "标签",
                "value": self.tag_options,
            },
            {
                "key": "sort",
                "name": "排序",
                "value": [
                    {"n": "最新发布", "v": "latest"},
                    {"n": "最热",     "v": "hot"},
                ]
            },
        ]

    def homeVideoContent(self):
        html = self._http_get(f"{self.siteUrl}/videos")
        items = self._parse_list(html)
        return {"list": items[:20]}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg or 1)
        extend = extend or {}

        params = [f"category={tid}"]
        if extend.get("rating"):
            params.append(f"rating={extend['rating']}")
        if extend.get("tags"):
            params.append(f"tags={extend['tags']}")
        if extend.get("sort"):
            params.append(f"sort={extend['sort']}")
        if page > 1:
            params.append(f"page={page}")

        url = f"{self.siteUrl}/videos?" + "&".join(params)

        html = self._http_get(url)
        items = self._parse_list(html)

        pagecount = page + 1 if items else page
        m = re.search(r'共\s*(\d+)\s*部', html)
        if m:
            total = int(m.group(1))
            page_size = 20
            if total > 0:
                pagecount = (total + page_size - 1) // page_size

        return {
            "list": items,
            "page": page,
            "pagecount": pagecount,
            "limit": 20,
            "total": 999,
        }

    def searchContent(self, key, quick, pg="1"):
        page = int(pg or 1)
        kw = str(key or "").strip()
        if not kw:
            return {"list": [], "page": page, "pagecount": 1}

        url = f"{self.siteUrl}/search?q={urllib.parse.quote(kw)}"
        if page > 1:
            url += f"&page={page}"

        html = self._http_get(url)
        items = self._parse_list(html)

        return {
            "list": items,
            "page": page,
            "pagecount": page + 1 if items else page,
            "limit": 20,
            "total": len(items),
        }

    def detailContent(self, ids):
        raw = str(ids[0] if isinstance(ids, (list, tuple)) else ids).strip()
        if not raw:
            return {"list": []}

        if raw.startswith('video:'):
            kind, real_id = 'video', raw[len('video:'):]
        elif raw.startswith('series:'):
            kind, real_id = 'series', raw[len('series:'):]
        else:
            kind, real_id = 'video', raw

        url = f"{self.siteUrl}/{kind}/{real_id}"
        html = self._http_get(url)
        if not html:
            return {"list": []}

        title = self._extract_title(html) or real_id
        pic = self._extract_cover(html)
        intro = self._extract_intro(html)

        play_urls = []
        eps = []

        if kind == 'series':
            eps = self._extract_episodes(html)
        else:
            series_url = self._extract_series_url(html)
            if series_url:
                shtml = self._http_get(series_url)
                eps = self._extract_episodes(shtml)
            if not eps:
                eps = self._extract_episodes(html)

        if eps:
            for ep in eps:
                play_urls.append(f"{ep['name']}${ep['url']}")
        else:
            vurl = self._extract_hls(html)
            if vurl:
                play_urls.append(f"正片${vurl}")
            else:
                play_urls.append(f"正片${url}")

        # 后台预热第一集：用户通常先点第 1 集，提前把真实地址解析好
        if play_urls:
            first_target = ""
            if eps:
                first_target = eps[0].get("url", "")
            else:
                first_target = play_urls[0].split('$', 1)[-1]
            if first_target.startswith('http'):
                self._prefetch_play_url(first_target)

        return {
            "list": [{
                "vod_id": raw,
                "vod_name": title,
                "vod_pic": pic,
                "vod_content": intro,
                "vod_remarks": f"共{len(play_urls)}集" if play_urls else "",
                "vod_play_from": "黄果" if play_urls else "",
                "vod_play_url": "#".join(play_urls),
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        raw = str(id or "").strip()
        if not raw:
            return {"parse": 1, "url": raw}

        result = self._resolve_play_url(raw)
        if result:
            url, referer = result
            return {
                "parse": 0,
                "url": url,
                "header": {
                    "User-Agent": self._ua,
                    "Referer": referer,
                    "Origin": self.siteUrl,
                    "Cookie": "hg_age=1",
                }
            }

        # 无法解析，交给外部解析器
        return {
            "parse": 1,
            "url": raw,
            "header": {
                "User-Agent": self._ua,
                "Referer": self.siteUrl + "/",
                "Cookie": "hg_age=1",
            }
        }

    def localProxy(self, params):
        return [404, "text/plain; charset=utf-8", "disabled"]

    def liveContent(self):
        return ""

    def action(self, action):
        return {"msg": "ok"}