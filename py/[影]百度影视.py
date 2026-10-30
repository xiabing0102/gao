# -*- coding: utf-8 -*-
"""
百度影视 (www.lcnwg.com / lcnwg.top) - TVBox 爬虫源 (maccms)
============================================================
v2 更新：
  - ✅ 标签顺序：电影 / 电视剧 / 短剧 / 动漫 / 娱乐
  - ✅ 每个标签配套筛选：类型(二级分类) / 地区 / 年份 / 排序
  - ✅ 短剧无子分类时自动隐藏「类型」筛选，只保留地区/年份/排序
接口：homeContent / homeVideoContent / categoryContent(含筛选) / detailContent / playerContent / searchContent
"""

import re
import json
import time
import socket
import threading
from urllib.parse import quote, urlencode

import requests
from requests.adapters import HTTPAdapter

try:
    from concurrent.futures import ThreadPoolExecutor, as_completed
except ImportError:
    ThreadPoolExecutor = None
    as_completed = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

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


# ============================================================
# 常量
# ============================================================

DOMAIN_CANDIDATES = [
    "https://www.lcnwg.com",
    "https://lcnwg.com",
    "https://www.lcnwg.top",
    "https://lcnwg.top",
]
_CURRENT_DOMAIN = DOMAIN_CANDIDATES[0]
_DOMAIN_LOCK = threading.Lock()

_SITE_MARK = "maccms"
_VERIFY_MARK = "系统安全验证"
_MIN_OK_BYTES = 10000

UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)

TIMEOUT_PAGE = 8
TIMEOUT_API = 5
TIMEOUT_PLAY = 4

TTL_HOME = 600
TTL_CAT = 300
TTL_DETAIL_OK = 300
TTL_DETAIL_EMPTY = 30
TTL_SEARCH = 180
TTL_PLAY = 900

DOMAIN_FAIL_THRESHOLD = 3

AREAS = [
    "大陆", "香港", "台湾", "美国", "英国", "法国",
    "日本", "韩国", "德国", "泰国", "印度", "新加坡",
    "西班牙", "意大利", "加拿大", "其他",
]

YEARS = [str(y) for y in range(2026, 2003, -1)]

# ============================================================
# ✅ 分类表（顺序：电影 / 电视剧 / 短剧 / 动漫 / 娱乐）
#    - 「娱乐」即站点的「综艺」分类（tid=3），仅显示名不同
#    - 每个一级分类都配有二级类型，筛选走 /lcnwgtp/ URL 参数通道
# ============================================================
CATS = [
    {"id": "1", "name": "电影", "subs": [
        ("6", "动作片"), ("7", "喜剧片"), ("8", "爱情片"), ("9", "科幻片"),
        ("10", "恐怖片"), ("11", "剧情片"), ("12", "战争片"), ("13", "纪录片"),
        ("14", "悬疑片"), ("15", "犯罪片"), ("16", "奇幻片"), ("31", "动画片"),
        ("32", "预告片"),
    ]},
    {"id": "2", "name": "电视剧", "subs": [
        ("17", "国产剧"), ("18", "港台剧"), ("20", "日韩剧"),
        ("21", "欧美剧"), ("22", "海外剧"),
    ]},
    {"id": "5", "name": "短剧", "subs": [
        # 短剧站点通常无固定子分类；如有可在此补充 (tid, name)
    ]},
    {"id": "4", "name": "动漫", "subs": [
        ("27", "国产动漫"), ("28", "日韩动漫"),
        ("29", "欧美动漫"), ("30", "其他动漫"),
    ]},
    {"id": "3", "name": "娱乐", "subs": [
        ("23", "大陆综艺"), ("24", "日韩综艺"),
        ("25", "欧美综艺"), ("26", "港台综艺"),
    ]},
]


def _build_filters(cat):
    """
    构建筛选器：类型(二级分类) / 地区 / 年份 / 排序
    - 当 subs 为空时，跳过「类型」筛选（避免只有一个"全部"的空筛选项）
    """
    filters = []

    subs = [{"n": name, "v": tid} for tid, name in cat["subs"]]
    if subs:
        filters.append({
            "key": "class", "name": "类型",
            "value": [{"n": "全部", "v": ""}] + subs,
        })

    filters.append({
        "key": "area", "name": "地区",
        "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in AREAS],
    })
    filters.append({
        "key": "year", "name": "年份",
        "value": [{"n": "全部", "v": ""}] + [{"n": y, "v": y} for y in YEARS],
    })
    filters.append({
        "key": "by", "name": "排序",
        "value": [
            {"n": "最新更新", "v": "time"},
            {"n": "最多播放", "v": "hits"},
            {"n": "好评高分", "v": "score"},
        ],
    })
    return filters


# 一级分类列表（顺序 = CATS 顺序）
ALL_CLASSES = [
    {"type_id": c["id"], "type_name": c["name"], "filter": 1}
    for c in CATS
]
# 筛选器（按 type_id 索引）
ALL_FILTERS = {c["id"]: _build_filters(c) for c in CATS}


# ============================================================
# 域名跟踪器
# ============================================================
class DomainTracker(object):
    def __init__(self, candidates=None, mark=_SITE_MARK):
        self.candidates = candidates or DOMAIN_CANDIDATES
        self.mark = mark
        self._probe_lock = threading.Lock()
        self._probing = False
        self._fail_count = 0
        self._last_probe = 0.0
        self._min_probe_interval = 30.0

    @staticmethod
    def current():
        with _DOMAIN_LOCK:
            return _CURRENT_DOMAIN

    def is_healthy(self):
        return self._fail_count < DOMAIN_FAIL_THRESHOLD

    def mark_failed(self):
        self._fail_count += 1
        if self._fail_count >= DOMAIN_FAIL_THRESHOLD:
            self.probe_async()

    def mark_ok(self):
        self._fail_count = 0

    def probe_async(self):
        with self._probe_lock:
            if self._probing:
                return
            if time.time() - self._last_probe < self._min_probe_interval:
                return
            self._probing = True
        threading.Thread(target=self._probe_worker, daemon=True).start()

    def _probe_worker(self):
        try:
            best = self._probe_all()
            if best:
                self._switch(best)
                self._fail_count = 0
        finally:
            with self._probe_lock:
                self._probing = False
                self._last_probe = time.time()

    def _probe_all(self):
        results = {}
        if ThreadPoolExecutor is not None and len(self.candidates) > 1:
            try:
                with ThreadPoolExecutor(
                        max_workers=min(5, len(self.candidates))) as ex:
                    fut_map = {ex.submit(self._probe_one, d): d
                               for d in self.candidates}
                    for f in as_completed(fut_map, timeout=TIMEOUT_API + 3):
                        d = fut_map[f]
                        try:
                            results[d] = f.result(timeout=TIMEOUT_API)
                        except Exception:
                            results[d] = False
            except Exception:
                for d in self.candidates:
                    results[d] = self._probe_one(d)
        else:
            for d in self.candidates:
                results[d] = self._probe_one(d)
        for d in self.candidates:
            if results.get(d):
                return d
        return None

    def _probe_one(self, domain):
        try:
            r = requests.get(
                domain + "/", timeout=min(TIMEOUT_API, 6),
                headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.8"},
                verify=False,
            )
            if r.status_code != 200:
                return False
            text = r.text
            if len(text) < _MIN_OK_BYTES:
                return False
            if _VERIFY_MARK in text:
                return False
            if self.mark not in text.lower():
                return False
            return True
        except Exception:
            return False

    @staticmethod
    def _switch(domain):
        global _CURRENT_DOMAIN
        with _DOMAIN_LOCK:
            if domain and domain != _CURRENT_DOMAIN:
                _CURRENT_DOMAIN = domain


TRACKER = DomainTracker()


# ============================================================
# Spider 主类
# ============================================================
_Base = _BaseSpider if _BaseSpider is not None else object


class Spider(_Base):
    siteUrl = DOMAIN_CANDIDATES[0]
    headers = {
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Referer': DOMAIN_CANDIDATES[0] + '/',
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.headers['Connection'] = 'keep-alive'
        self.session.verify = False
        adapter = HTTPAdapter(
            pool_connections=20, pool_maxsize=40,
            max_retries=0, pool_block=False,
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        self._tracker = TRACKER
        self._warm_thread = None

        self._lock = threading.Lock()
        self._home_cache = []
        self._home_cache_time = 0
        self._cat_cache = {}
        self._detail_cache = {}
        self._search_cache = {}
        self._play_cache = {}
        self._prefetching = set()

    def init(self, extend=""):
        self.extend = extend or ""
        self._tracker.probe_async()

    @property
    def HOST(self):
        return self._tracker.current()

    def _mk_headers(self, referer=''):
        headers = {'Connection': 'keep-alive'}
        if referer:
            headers['Referer'] = referer
        return headers

    def _get(self, url, referer='', timeout=TIMEOUT_PAGE):
        for attempt in range(2):
            try:
                r = self.session.get(url, timeout=timeout,
                                     headers=self._mk_headers(referer))
                if r.status_code == 429:
                    time.sleep(2.0)
                    continue
                r.raise_for_status()
                r.encoding = r.apparent_encoding or 'utf-8'
                if _VERIFY_MARK in r.text[:2000]:
                    self._tracker.mark_failed()
                    return None
                self._tracker.mark_ok()
                return r
            except Exception:
                self._tracker.mark_failed()
                if attempt == 0:
                    time.sleep(0.3)
                else:
                    return None
        return None

    def _get_text(self, url, referer='', timeout=TIMEOUT_PAGE):
        r = self._get(url, referer, timeout)
        return r.text if r is not None else ""

    def _post_text(self, url, data=None, referer='', timeout=TIMEOUT_API):
        for attempt in range(2):
            try:
                r = self.session.post(url, data=data, timeout=timeout,
                                      headers=self._mk_headers(referer))
                if r.status_code == 429:
                    time.sleep(2.0)
                    continue
                r.raise_for_status()
                r.encoding = r.apparent_encoding or 'utf-8'
                if _VERIFY_MARK in r.text[:2000]:
                    self._tracker.mark_failed()
                    return ""
                self._tracker.mark_ok()
                return r.text
            except Exception:
                self._tracker.mark_failed()
                if attempt == 0:
                    time.sleep(0.3)
                else:
                    return ""
        return ""

    @staticmethod
    def _cache_get(cache, key, ttl=None):
        item = cache.get(key)
        if item and time.time() - item[0] < (
                ttl if ttl is not None else item[2]):
            return item[1]
        return None

    @staticmethod
    def _cache_set(cache, key, value, ttl=TTL_CAT):
        if len(cache) > 512:
            cache.clear()
        cache[key] = (time.time(), value, ttl)

    @staticmethod
    def _soup(html):
        if not html or BeautifulSoup is None:
            return None
        try:
            return BeautifulSoup(html, 'lxml')
        except Exception:
            try:
                return BeautifulSoup(html, 'html.parser')
            except Exception:
                return None

    @staticmethod
    def _abs(u):
        u = (u or '').strip()
        if not u:
            return ''
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return TRACKER.current() + u
        if not u.startswith('http'):
            return TRACKER.current() + '/' + u
        return u

    @staticmethod
    def _extract_id(href):
        m = re.search(r'/(\d{4,10})\.(?:html|shtml)$', (href or '').strip())
        return m.group(1) if m else None

    @staticmethod
    def _clean_name(raw):
        if not raw:
            return raw
        raw = re.sub(r'<span[^>]*class="[^"]*score[^"]*"[^>]*>.*?</span>',
                     '', raw, flags=re.S)
        raw = re.sub(r'\s+', ' ', raw).strip()
        raw = re.sub(r'\s+\d+\s*\.\s*\d+\s*$', '', raw).strip()
        return raw

    @staticmethod
    def _pick_pic(el):
        if el is None:
            return ''
        for attr in ('data-original', 'data-src', 'src'):
            val = str(el.get(attr) or '').strip()
            if val:
                return Spider._abs(val)
        return ''

    def _parse_cards(self, html, limit=36):
        if not html:
            return []
        soup = self._soup(html)
        if soup is None:
            return []
        items = {}
        for li in soup.select('li.dx-vod'):
            vid, pic, link = None, '', ''
            dj = str(li.get('data-json') or '')
            if dj:
                try:
                    d = json.loads(dj.replace('\\/', '/'))
                    vid = str(d.get('id') or '')
                    pic = str(d.get('pic') or '')
                    link = str(d.get('link') or '')
                except Exception:
                    pass
            if not vid:
                m = re.search(r'data-id="(\d+)"', dj)
                if not m:
                    m = re.search(r'data-id="(\d+)"', str(li))
                vid = m.group(1) if m else None
            if not vid:
                continue

            a = li.select_one('a.cover-area,\n                           a[href*="/lcnwgdt/"]')
            if not a:
                continue
            title = str(a.get('title') or '').strip()
            if not title:
                h = li.select_one('h5.title, h5')
                if h:
                    title = h.get_text(strip=True)
            if not title:
                continue
            if not pic:
                pic = self._pick_pic(a)

            remarks = ''
            st = li.select_one('span.vod_remarks')
            if st:
                remarks = st.get_text(strip=True)

            items[vid] = {
                'vod_id': vid,
                'vod_name': self._clean_name(title),
                'vod_pic': pic,
                'vod_remarks': remarks,
            }
        return list(items.values())[:limit]

    @staticmethod
    def _parse_pages(html):
        page, pagecount, total = 1, 1, 0
        m = re.search(r'page_total[^>]*>\s*(\d+)/(\d+)页', html)
        if m:
            page, pagecount = int(m.group(1)), int(m.group(2))
        m = re.search(r'共(\d+)条数据', html)
        if m:
            total = int(m.group(1))
        return page, pagecount, total

    # ============================================================
    # 首页
    # ============================================================
    def homeContent(self, filter=False):
        now = int(time.time())
        with self._lock:
            if self._home_cache and now - self._home_cache_time < TTL_HOME:
                vod_list = self._home_cache[:60]
            else:
                vod_list = []
        if not vod_list:
            try:
                html = self._get_text(self.HOST + "/")
                vod_list = self._parse_cards(html, limit=60)
                if vod_list:
                    with self._lock:
                        self._home_cache = vod_list
                        self._home_cache_time = int(time.time())
            except Exception:
                pass
        return {
            "class": ALL_CLASSES,
            "filters": ALL_FILTERS,
            "list": vod_list,
        }

    def homeVideoContent(self):
        now = int(time.time())
        with self._lock:
            if self._home_cache and now - self._home_cache_time < TTL_HOME:
                return {"list": self._home_cache[:60]}
        try:
            html = self._get_text(self.HOST + "/")
            vod_list = self._parse_cards(html, limit=60)
            if vod_list:
                with self._lock:
                    self._home_cache = vod_list
                    self._home_cache_time = int(time.time())
            return {"list": vod_list[:60]}
        except Exception:
            return {"list": []}

    # ============================================================
    # 分类列表（筛选走 /lcnwgtp/ URL 参数通道）
    # ============================================================
    def _empty_category(self, page=1):
        return {"list": [], "page": page, "pagecount": 1,
                "limit": 36, "total": 0}

    def _cat_url(self, tid, page, ext):
        """
        URL 构建：
        - 第1页无筛选：/lcnwgtp/{tid}.html
        - 第1页带筛选：/lcnwgtp/{tid}.html?area=xxx&year=xxx&by=xxx
        - 第2+页：    /lcnwgtp/{tid}-{page}.html
        """
        tid = str(tid)
        url = f"{self.HOST}/lcnwgtp/{tid}.html" if page <= 1 \
            else f"{self.HOST}/lcnwgtp/{tid}-{page}.html"
        params = {}
        for key in ('area', 'year', 'by'):
            val = (ext.get(key) or '').strip()
            if val:
                params[key] = val
        if params:
            url += '?' + urlencode(params)
        return url

    def categoryContent(self, tid, pg, filter, extend):
        page = 1
        try:
            page = max(1, int(pg or 1))
            ext = {}
            if extend:
                if isinstance(extend, dict):
                    ext = extend
                elif isinstance(extend, str):
                    try:
                        ext = json.loads(extend)
                    except Exception:
                        ext = {}

            # 类型筛选（二级分类）时，用二级 tid 覆盖一级 tid
            real_tid = (ext.get('class') or '').strip() or str(tid)

            ckey = "%s|%d|%s" % (real_tid, page,
                                 json.dumps(ext, ensure_ascii=False, sort_keys=True))
            cached = self._cache_get(self._cat_cache, ckey, TTL_CAT)
            if cached is not None:
                return cached

            url = self._cat_url(real_tid, page, ext)
            html = self._get_text(url)
            if not html:
                return self._empty_category(page)

            vod_list = self._parse_cards(html, limit=36)
            p, pc, total = self._parse_pages(html)

            result = {
                "list": vod_list,
                "page": p if p > 1 else page,
                "pagecount": pc if pc > 1 else max(page, 1),
                "limit": 36,
                "total": total or (pc * 36),
            }
            self._cache_set(self._cat_cache, ckey, result, TTL_CAT)
            return result
        except Exception:
            return self._empty_category(page)

    # ============================================================
    # 详情页
    # ============================================================
    def detailContent(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        vid = str(ids[0]).split(',')[0].strip()
        if not vid:
            return {"list": []}

        cached = self._cache_get(self._detail_cache, vid, None)
        if cached is not None:
            return cached

        result = self._fetch_detail(vid)
        ttl = TTL_DETAIL_OK if result.get("list") else TTL_DETAIL_EMPTY
        self._cache_set(self._detail_cache, vid, result, ttl)

        if result.get("list"):
            self._prefetch_play(result["list"][0])
        return result

    def _fetch_detail(self, vid):
        html = self._get_text(f"{self.HOST}/lcnwgdt/{vid}.html")
        if not html:
            return {"list": []}
        soup = self._soup(html)
        if soup is None:
            return {"list": []}

        name = ''
        h1 = soup.select_one('h1')
        if h1:
            name = self._clean_name(h1.get_text(' ', strip=True))
        if not name:
            t1 = soup.title
            if t1:
                name = re.sub(r'[《》].*?[》]|全集在线播放.*$|_百度影视$', '',
                              t1.get_text(strip=True)).strip()

        pic = ''
        img = soup.select_one('.obj-pic img') or soup.select_one('img.lazy')
        if img:
            pic = self._pick_pic(img)

        meta = {}
        tags = []
        vi = soup.select_one('.video-info')
        if vi:
            for a in vi.select('a'):
                t = a.get_text(strip=True)
                if t and t not in tags:
                    tags.append(t)
            for t in tags:
                if re.fullmatch(r'\d{4}', t):
                    meta['year'] = t
                    break
            for t in tags:
                if t in AREAS:
                    meta['area'] = t
                    break

        AREA_ALIAS = {'中国大陆': '大陆', '中国香港': '香港', '中国台湾': '台湾'}

        key_map = {'导演': 'director', '主演': 'actor',
                   '制片国家/地区': 'area', '状态': 'remarks'}
        for p in soup.select('.info-items'):
            label_el = p.find('label')
            if label_el is None:
                continue
            label = (label_el.get_text(strip=True) or '').rstrip(':：')
            if label not in key_map:
                continue
            full = p.get_text(' ', strip=True)
            val = full[len(label_el.get_text(strip=True)):].strip()
            val = val.lstrip(':： ').strip()
            val = re.sub(r'^\s*[/|]\s*', '', val)
            val = re.sub(r'\s*/\s*$', '', val).strip()
            if key_map.get(label) == 'area' and val in AREA_ALIAS:
                val = AREA_ALIAS[val]
            if val:
                meta.setdefault(key_map[label], val)

        content = ''
        vc = soup.select_one('.vod_content')
        if vc:
            content = vc.get_text(' ', strip=True)
        if not content:
            meta_el = soup.find('meta', attrs={'name': 'description'})
            if meta_el:
                content = str(meta_el.get('content') or '')[:200]

        play_groups = []
        for box in soup.select('div[id^="playlist_"]'):
            src_name = ''
            h2 = box.select_one('h2')
            if h2:
                src_name = h2.get_text(strip=True)
            eps = []
            for a in box.select('a[href*="/lcnwgpy/"]'):
                ep_name = a.get_text(strip=True) or '播放'
                ep_url = self._abs(str(a.get('href') or ''))
                if ep_url:
                    eps.append((ep_name, ep_url))
            if eps:
                play_groups.append((src_name or '线路', eps))

        play_from, play_url = '', ''
        for src_name, eps in play_groups:
            ep_parts = [f"{n}${u}" for n, u in eps]
            play_from = ((play_from + '$$$' + src_name)
                         if play_from else src_name)
            play_url = ((play_url + '$$$' + '#'.join(ep_parts))
                        if play_url else '#'.join(ep_parts))

        detail = {
            "vod_id": vid,
            "vod_name": name or f"视频{vid}",
            "vod_pic": pic or self.HOST,
            "type_name": tags[0] if tags else '',
            "vod_year": meta.get('year', ''),
            "vod_area": meta.get('area', ''),
            "vod_remarks": meta.get('remarks', ''),
            "vod_actor": meta.get('actor', ''),
            "vod_director": meta.get('director', ''),
            "vod_content": content,
            "vod_play_from": play_from or '默认',
            "vod_play_url": play_url or '',
        }
        return {"list": [detail]}

    # ============================================================
    # 播放
    # ============================================================
    def _resolve_play(self, play_url):
        cached = self._cache_get(self._play_cache, play_url, TTL_PLAY)
        if cached:
            return cached
        real = ''
        try:
            text = self._get_text(play_url, referer=self.HOST + '/',
                                  timeout=TIMEOUT_PLAY)
            if text:
                m = re.search(r'var\s+player_\w+\s*=\s*(\{.*?\})\s*[;<]',
                              text, re.S)
                if m:
                    try:
                        data = json.loads(m.group(1))
                        u = (data.get('url') or '').replace('\\/', '/').strip()
                        if u:
                            real = self._abs(u)
                    except Exception:
                        pass
                if not real:
                    m2 = re.search(r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"', text)
                    if m2:
                        real = self._abs(m2.group(1).replace('\\/', '/'))
                if not real:
                    m3 = re.search(r'"url"\s*:\s*"(https?://[^"]+)"', text)
                    if m3:
                        u = m3.group(1).replace('\\/', '/').strip()
                        if '.m3u8' in u.lower() or '.mp4' in u.lower():
                            real = self._abs(u)
        except Exception:
            real = ''
        if real:
            self._cache_set(self._play_cache, play_url, real, TTL_PLAY)
        return real

    def _first_play_url(self, vod):
        for seg in (vod.get("vod_play_url") or "").split("$$$"):
            for item in seg.split("#"):
                parts = item.split("$", 1)
                if len(parts) == 2 and parts[1]:
                    return parts[1]
        return None

    def _prefetch_play(self, vod):
        target = self._first_play_url(vod)
        if not target:
            return
        with self._lock:
            if (self._cache_get(self._play_cache, target, TTL_PLAY)
                    or target in self._prefetching):
                return
            self._prefetching.add(target)

        def _job():
            try:
                self._resolve_play(target)
            except Exception:
                pass
            finally:
                with self._lock:
                    self._prefetching.discard(target)

        threading.Thread(target=_job, daemon=True).start()

    def _play_payload(self, playurl):
        is_m3u8 = '.m3u8' in playurl.lower()
        return {
            "parse": 0,
            "playUrl": "",
            "url": playurl,
            "header": {
                "User-Agent": UA,
                "Referer": self.HOST + "/",
                "Origin": self.HOST,
            },
            "format": "application/x-mpegURL" if is_m3u8 else "",
            "contentType": "application/x-mpegURL" if is_m3u8 else "",
        }

    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {"parse": 0, "playUrl": "", "url": ""}
        play_url = self._abs(str(id))

        m3u8 = self._resolve_play(play_url)
        if m3u8:
            return self._play_payload(m3u8)

        return {
            "parse": 1,
            "playUrl": "",
            "url": play_url,
            "header": {"User-Agent": UA, "Referer": self.HOST + "/"},
        }

    # ============================================================
    # 搜索
    # ============================================================
    @staticmethod
    def _norm_keyword(keyword):
        if not isinstance(keyword, str):
            keyword = str(keyword or '')
        kw = (keyword or '').strip()
        kw = re.sub(r'[\s\u3000]+', '', kw)
        if '%' in kw:
            try:
                from urllib.parse import unquote
                dec = unquote(kw)
                if dec != kw:
                    kw = dec.strip()
            except Exception:
                pass
        return kw

    def _suggest(self, keyword, limit=100):
        kw = self._norm_keyword(keyword)
        if not kw:
            return []
        try:
            url = (f"{self.HOST}/index.php/ajax/suggest?mid=1&wd="
                   + quote(kw) + f"&limit={limit}")
            text = self._get_text(url, referer=self.HOST + '/',
                                  timeout=TIMEOUT_API)
            if not text:
                return []
            data = json.loads(text)
            if data.get('code') != 1:
                return []
            out, seen = [], set()
            for it in data.get('list') or []:
                vid = str(it.get('id') or '')
                name = str(it.get('name') or '').strip()
                if not vid or not name:
                    continue
                if vid in seen:
                    continue
                seen.add(vid)
                out.append({
                    'vod_id': vid,
                    'vod_name': self._clean_name(name),
                    'vod_pic': self._abs(it.get('pic') or ''),
                    'vod_remarks': str(it.get('remark') or ''),
                })
                if len(out) >= limit:
                    break
            return out
        except Exception:
            return []

    def suggest(self, word):
        return self._suggest(word, limit=20)

    def _scrape_fallback(self, keyword, limit=20):
        kw = (keyword or '').strip().lower().replace(' ', '')
        if not kw:
            return []
        out, seen = [], set()
        for c in CATS:
            try:
                html = self._get_text(self._cat_url(c['id'], 1, {}),
                                      timeout=TIMEOUT_API)
                if not html:
                    continue
                soup = self._soup(html)
                if soup is None:
                    continue
                for li in soup.select('li.dx-vod'):
                    h = li.select_one('h5.title, h5')
                    if h is None:
                        continue
                    name = h.get_text(strip=True)
                    if kw in name.lower().replace(' ', ''):
                        vid = None
                        dj = str(li.get('data-json') or '')
                        if dj:
                            try:
                                vid = str(json.loads(dj.replace('\\/', '/'))
                                          .get('id') or '')
                            except Exception:
                                pass
                        if not vid:
                            m = (re.search(r'data-id="(\d+)"', dj)
                                 or re.search(r'data-id="(\d+)"', str(li)))
                            vid = m.group(1) if m else None
                        if vid and vid not in seen:
                            seen.add(vid)
                            a = li.select_one('a.cover-area,\n                           a[href*="/lcnwgdt/"]')
                            out.append({
                                'vod_id': vid,
                                'vod_name': self._clean_name(name),
                                'vod_pic': self._pick_pic(a) if a else '',
                                'vod_remarks': '',
                            })
                            if len(out) >= limit:
                                return out
            except Exception:
                continue
        return out

    def searchContent(self, keyword, quick):
        key = self._norm_keyword(keyword)
        if not key:
            return {"list": []}

        cached = self._cache_get(self._search_cache, key, TTL_SEARCH)
        if cached is not None:
            return cached

        result = self._suggest(key, limit=100)

        if not result and len(key) >= 2 and not quick:
            for sub in self._split_keywords(key):
                sub_res = self._suggest(sub, limit=50)
                if sub_res:
                    kept = [r for r in sub_res if key in r['vod_name']]
                    if kept:
                        result = kept[:20]
                        break

        if not result and not quick:
            result = self._scrape_fallback(key)

        resp = {"list": result[:40]}
        self._cache_set(self._search_cache, key, resp, TTL_SEARCH)
        return resp

    @staticmethod
    def _split_keywords(key):
        cands = []
        n = len(key)
        if n <= 2:
            return [key]
        cands.append(key[:2])
        cands.append(key[-2:])
        if n >= 3:
            cands.append(key[0])
            cands.append(key[-1])
            cands.append(key[1])
        seen, out = set(), []
        for c in cands:
            if c and c not in seen:
                seen.add(c)
                out.append(c)
        return out

    # ============================================================
    # 生命周期
    # ============================================================
    def localProxy(self, param):
        action = param.get('do') if isinstance(param, dict) else ''
        if action == 'domain':
            return [200, "text/plain; charset=utf-8",
                    TRACKER.current().encode('utf-8'), ""]
        return [200, "text/plain; charset=utf-8", b"", ""]

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass

    def close(self):
        try:
            self.session.close()
        except Exception:
            pass


# ============================================================
# 自测入口
# ============================================================
if __name__ == '__main__':
    print("=== 百度影视 TVBox 爬虫源自测 ===\n")
    sp = Spider()
    sp.init("")

    home = sp.homeContent()
    print("[首页] 标签顺序：", [c["type_name"] for c in home.get("class", [])])
    print("[首页] 筛选器 key：", list(home.get("filters", {}).keys()))
    for tid, flt in home.get("filters", {}).items():
        print(f"  tid={tid} 筛选：", [f["name"] for f in flt])

    # 各标签首屏测试
    for c in home.get("class", []):
        tid = c["type_id"]
        cat = sp.categoryContent(tid, 1, "", {})
        print(f"\n[{c['type_name']} tid={tid}] 列表：", len(cat.get("list", [])),
              "| 总页数：", cat.get("pagecount"), "| 总数：", cat.get("total"))

    print("\n=== 自测完成 ===")