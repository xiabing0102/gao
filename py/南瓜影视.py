#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
南瓜影视 TVBox / drpy / FongMi  Python 爬虫源
目标站: https://nangua1.tv/channel/movie

接口: Spider 类方法 + 顶层转发函数（兼容类式壳与函数式壳）

站点是 Vite SPA，数据全部来自公开 H5 JSON API（无需登录态）:
    GET /api/home                      首页推荐 / 频道行
    GET /api/menus                     导航菜单
    GET /api/config                    站点配置、图片存储白名单
    GET /api/channel/{key}             频道列表，支持 genre/region/year/sort/page/size
    GET /api/search                    搜索，支持 q/page/size
    GET /api/video/{id}                详情，sources[].episodes[].url 即播放直链
    GET /api/img?u=xxx                 图片代理（非白名单图片走这里）

支持: 首页 / 分类 + 筛选 / 搜索(分页) / 详情 / 播放
依赖: 仅标准库，urllib 直连，不需要 requests / bs4 / Crypto
数据源: 仅 nangua1.tv 自身 API，无备用域名、无第三方源兜底
"""

import sys
import json
import re
import time
import html
import urllib.request
import urllib.parse
from datetime import datetime

sys.path.append('..')

try:
    from base.spider import Spider as _BaseSpider
except Exception:
    # 本地直接运行（python 南瓜.py --selftest）时的兜底；
    # 在 drpy / TVBox 环境里会加载到真实基类，不受影响。
    class _BaseSpider(object):
        pass


# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #
HOST = 'https://nangua1.tv'
API = HOST + '/api'

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

PAGE_SIZE = 24          # 列表 / 搜索每页条数（站点默认 24，最大 60）
HOME_LIMIT = 30         # 首页推荐条数
CACHE_TTL = 300         # GET 结果缓存秒数

# (频道 key, 名称, 类型标签) —— 与站点前端频道配置一致
CHANNELS = [
    ('movie',   '电影',   ['喜剧', '爱情', '动作', '犯罪', '科幻', '奇幻', '冒险']),
    ('drama',   '电视剧', ['国产剧', '港剧', '台剧', '日剧', '韩剧', '欧美剧', '英剧']),
    ('variety', '综艺',   ['真人秀', '选秀', '网综', '脱口秀', '搞笑', '竞技', '情感']),
    ('anime',   '动漫',   ['热血', '格斗', '机战', '少女', '竞技', '科幻', '魔幻']),
    ('short',   '短剧',   ['都市', '古装', '甜宠', '逆袭', '悬疑', '总裁', '重生']),
    ('doc',     '纪录片', ['人文', '历史', '自然', '社会', '科学', '军事']),
    ('sports',  '体育',   ['足球', '篮球', '赛事', '格斗', '网球']),
    ('chinese', '华人',   ['留学生活', '活动演出', '推广']),
    ('music',   '音乐',   ['MV', '自创', '舞蹈', '现场']),
    ('game',    '游戏',   ['电竞', '网游', '单机', '主机', '手游']),
]
TAGS = {k: t for k, _, t in CHANNELS}

# 显示名做规范化；传给接口的值保持站点原值，避免筛选失效
REGIONS = [
    ('全部', ''), ('大陆', '大陆'), ('中国香港', '香港'), ('中国台湾', '台湾'),
    ('美国', '美国'), ('日本', '日本'), ('韩国', '韩国'), ('英国', '英国'), ('法国', '法国'),
]
SORTS = [('最新', 'new'), ('最热', 'hot'), ('评分', 'rating')]
_YEAR = datetime.now().year
YEARS = [('全部', '')] + [(str(_YEAR - i), str(_YEAR - i)) for i in range(8)] + [('更早', '更早')]

VIDEO_EXT = re.compile(r'\.(m3u8|mp4|flv|mkv|ts|m4a)(\?|#|$)', re.I)
IMG_EXT = re.compile(r'\.(jpg|jpeg|png|webp|gif|bmp)(\?|#|$)', re.I)
TAG_RE = re.compile(r'<[^>]+>')


def _asdict(x):
    return x if isinstance(x, dict) else {}


def _aslist(x):
    return x if isinstance(x, list) else []


def _parse_kv(extend):
    """extend 兼容 dict / JSON 字符串 / 'k=v&k=v' / 'k=v;k=v'。"""
    if isinstance(extend, dict):
        return dict(extend)
    s = str(extend or '').strip()
    if not s:
        return {}
    if s.startswith('{'):
        try:
            return _asdict(json.loads(s))
        except Exception:
            return {}
    out = {}
    for part in re.split(r'[&;]', s):
        if '=' in part:
            k, v = part.split('=', 1)
            out[k.strip().lower()] = urllib.parse.unquote(v.strip())
    return out


# --------------------------------------------------------------------------- #
# 爬虫主体
# --------------------------------------------------------------------------- #
class Spider(_BaseSpider):

    # 类级默认值：部分壳不显式调用 init，直接用类方法也不会崩
    host = HOST
    api = API
    page_size = PAGE_SIZE
    storage_bases = []
    _classes_cache = None

    def getName(self):
        return '南瓜影视'

    def isVideoFormat(self, url):
        return bool(VIDEO_EXT.search(str(url or '')))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    # ------------------------------------------------------------------ #
    # 初始化 / 网络层
    # ------------------------------------------------------------------ #
    def init(self, extend=""):
        """域名固定为目标站，不提供换源开关；extend 仅支持 size= 调整每页条数。"""
        self.host = HOST
        self.api = API
        self.page_size = PAGE_SIZE
        self.storage_bases = []
        self._cache = {}
        self._classes_cache = None

        cfg = _parse_kv(extend)
        try:
            n = int(cfg.get('size') or 0)
            if 1 <= n <= 60:
                self.page_size = n
        except Exception:
            pass

        # 图片白名单（OSS 域名可直连，其余走站点图片代理）
        data = _asdict(self._get('/config', timeout=8))
        self.storage_bases = [b for b in _aslist(data.get('storageBases')) if isinstance(b, str)]
        return None

    def _headers(self):
        return {
            'User-Agent': UA,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.host + '/',
            'Origin': self.host,
        }

    def _get(self, path, params=None, timeout=12, retry=2, ttl=CACHE_TTL):
        """GET 一个 API，返回响应里的 data 字段；失败返回 {}。"""
        if not hasattr(self, '_cache'):
            self.init()
        url = self.api + path
        if params:
            clean = {}
            for k, v in params.items():
                if v is None or v == '' or v == '全部':
                    continue
                clean[k] = v
            if clean:
                url += ('&' if '?' in url else '?') + urllib.parse.urlencode(clean)

        now = time.time()
        if ttl and url in self._cache:
            ts, val = self._cache[url]
            if now - ts < ttl:
                return val

        req = urllib.request.Request(url, headers=self._headers())
        data = {}
        for attempt in range(max(1, retry)):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    raw = r.read().decode('utf-8', 'ignore')
                obj = json.loads(raw)
                code = obj.get('code')
                if code not in (0, '0', 1, '1', 200, '200', None):
                    raise RuntimeError(str(obj.get('msg') or ('code=' + str(code))))
                data = obj.get('data')
                if data is None:
                    data = {}
                break
            except Exception:
                if attempt + 1 >= max(1, retry):
                    data = {}
        if ttl:
            self._cache[url] = (now, data)
        return data

    # ------------------------------------------------------------------ #
    # 通用字段处理
    # ------------------------------------------------------------------ #
    def _clean(self, s):
        """去 HTML / 去掉会破坏 TVBox 分隔符的字符。"""
        s = str(s or '')
        s = TAG_RE.sub(' ', s)
        s = html.unescape(s)
        s = s.replace('#', ' ').replace('$', ' ').replace('\r', ' ').replace('\n', ' ')
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    def _pic(self, u):
        """封面：白名单 OSS 直连，其它外链走 /api/img 代理，相对路径补主域。"""
        u = str(u or '').strip()
        if not u:
            return ''
        if u.startswith('//'):
            u = 'https:' + u
        if not u.startswith('http'):
            return urllib.parse.urljoin(self.host + '/', u.lstrip('/'))
        if re.search(r'aliyuncs\.com|taihangtop\.cn', u, re.I):
            return u
        for base in getattr(self, 'storage_bases', []):
            if u.startswith(base):
                return u
        return self.api + '/img?u=' + urllib.parse.quote(u, safe='')

    def _remark(self, v):
        """列表角标：清晰度/更新状态 + 评分。"""
        parts = []
        latest = self._clean(v.get('latest'))
        if latest:
            parts.append(latest)
        try:
            score = float(v.get('rating') or 0)
        except Exception:
            score = 0
        if score > 0:
            parts.append('%.1f分' % score)
        return ' '.join(parts)

    def _item(self, v):
        """站点影片对象 -> TVBox vod 列表项。"""
        v = _asdict(v)
        vid = v.get('id')
        if vid is None or vid == '':
            return {}
        return {
            'vod_id': str(vid),
            'vod_name': self._clean(v.get('title')) or '未命名',
            'vod_pic': self._pic(v.get('cover') or v.get('wide') or v.get('hero_image')),
            'vod_remarks': self._remark(v),
            'vod_year': str(v.get('year') or ''),
            'vod_area': self._clean(v.get('region')),
            'vod_score': str(v.get('rating') or ''),
            'type_name': self._clean(v.get('category')),
        }

    def _page_result(self, data, pg, size):
        data = _asdict(data)
        lst = []
        for v in _aslist(data.get('list')):
            one = self._item(v)
            if one:
                lst.append(one)
        try:
            total = int(data.get('total') or 0)
        except Exception:
            total = 0
        try:
            real_size = int(data.get('size') or size) or size
        except Exception:
            real_size = size
        pages = (total + real_size - 1) // real_size if total > 0 else 0
        if not pages and lst:
            pages = pg + (1 if len(lst) >= real_size else 0)
        return {
            'list': lst,
            'page': pg,
            'pagecount': max(1, pages) if pages else max(1, pg),
            'limit': real_size,
            'total': total,
        }

    # ------------------------------------------------------------------ #
    # 首页
    # ------------------------------------------------------------------ #
    def _classes(self):
        if getattr(self, '_classes_cache', None):
            return self._classes_cache
        classes = [{'type_id': k, 'type_name': n} for k, n, _ in CHANNELS]
        known = {k for k, _, _ in CHANNELS}
        names = {n for _, n, _ in CHANNELS}
        # 首页行里出现的新频道自动补进来，站点改版也不用改代码
        home = _asdict(self._get('/home'))
        for row in _aslist(home.get('rows')):
            row = _asdict(row)
            key = str(row.get('channel') or '')
            name = self._clean(row.get('name')) or key
            if key and key not in known and name not in names:
                classes.append({'type_id': key, 'type_name': name})
                known.add(key)
                names.add(name)
        self._classes_cache = classes
        return classes

    def _home_videos(self):
        home = _asdict(self._get('/home'))
        out, seen = [], set()
        pool = list(_aslist(home.get('hero')))
        for row in _aslist(home.get('rows')):
            row = _asdict(row)
            pool.extend(_aslist(row.get('videos')))
            pool.extend(_aslist(row.get('ranking')))
        for v in pool:
            one = self._item(v)
            vid = one.get('vod_id')
            if vid and vid not in seen:
                seen.add(vid)
                out.append(one)
            if len(out) >= HOME_LIMIT:
                break
        return out

    def _filters_for(self, tid):
        f = []
        tags = TAGS.get(tid) or []
        if tags:
            f.append({
                'key': 'genre', 'name': '类型',
                'value': [{'n': '全部', 'v': ''}] + [{'n': t, 'v': t} for t in tags],
            })
        f.append({'key': 'region', 'name': '地区',
                  'value': [{'n': n, 'v': v} for n, v in REGIONS]})
        f.append({'key': 'year', 'name': '年份',
                  'value': [{'n': n, 'v': v} for n, v in YEARS]})
        f.append({'key': 'sort', 'name': '排序',
                  'value': [{'n': n, 'v': v} for n, v in SORTS]})
        return f

    def homeContent(self, filter=False):
        result = {'class': self._classes(), 'list': self._home_videos()}
        if filter:
            result['filters'] = {c['type_id']: self._filters_for(c['type_id'])
                                 for c in result['class']}
        return result

    def homeVideoContent(self):
        return {'list': self._home_videos()}

    # ------------------------------------------------------------------ #
    # 分类 + 筛选
    # ------------------------------------------------------------------ #
    def categoryContent(self, tid, pg="1", filter=False, extend=None):
        try:
            page = max(1, int(pg or 1))
        except Exception:
            page = 1
        size = getattr(self, 'page_size', PAGE_SIZE)
        ext = _parse_kv(extend)
        params = {
            'page': page,
            'size': size,
            'sort': ext.get('sort') or 'new',
        }
        for k in ('genre', 'region', 'year'):
            v = ext.get(k)
            if v and v != '全部':
                params[k] = v
        key = urllib.parse.quote(str(tid or 'movie').strip(), safe='')
        data = self._get('/channel/' + key, params)
        return self._page_result(data, page, size)

    # ------------------------------------------------------------------ #
    # 详情 / 播放列表
    # ------------------------------------------------------------------ #
    def detailContent(self, array):
        if not isinstance(array, (list, tuple)):
            array = [array]
        if not array:
            return {'list': []}
        vid = str(array[0] or '').strip()
        if not vid:
            return {'list': []}
        info = _asdict(self._get('/video/' + urllib.parse.quote(vid, safe='')))

        play_from, play_url, used_names = [], [], set()
        for src in _aslist(info.get('sources')):
            src = _asdict(src)
            name = self._clean(src.get('name')) or '默认线路'
            base, i = name, 1
            while name in used_names:
                i += 1
                name = '%s%d' % (base, i)
            eps, seen_urls = [], set()
            for ep in _aslist(src.get('episodes')):
                ep = _asdict(ep)
                url = str(ep.get('url') or '').strip()
                if not url or url in seen_urls or IMG_EXT.search(url):
                    continue
                seen_urls.add(url)
                ep_name = self._clean(ep.get('name'))
                if not ep_name:
                    num = ep.get('num')
                    ep_name = ('第%s集' % num) if num else '播放'
                eps.append('%s$%s' % (ep_name, url))
            if eps:
                used_names.add(name)
                play_from.append(name)
                play_url.append('#'.join(eps))

        if not play_from:
            play_from = ['提示']
            play_url = ['暂无可用播放线路$']

        actors = _aslist(info.get('actors'))
        actor = ','.join([str(a).strip() for a in actors if a])
        vod = {
            'vod_id': vid,
            'vod_name': self._clean(info.get('title')) or '未命名',
            'vod_pic': self._pic(info.get('cover') or info.get('wide') or info.get('hero_image')),
            'type_name': self._clean(info.get('category')),
            'vod_year': str(info.get('year') or ''),
            'vod_area': self._clean(info.get('region')),
            'vod_lang': self._clean(info.get('language')),
            'vod_remarks': self._clean(info.get('latest')),
            'vod_score': str(info.get('rating') or ''),
            'vod_actor': actor,
            'vod_director': self._clean(info.get('director')),
            'vod_content': self._clean(info.get('description')),
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_url),
        }
        return {'list': [vod]}

    # ------------------------------------------------------------------ #
    # 搜索
    # ------------------------------------------------------------------ #
    def searchContentPage(self, key, quick=False, pg="1"):
        try:
            page = max(1, int(pg or 1))
        except Exception:
            page = 1
        size = getattr(self, 'page_size', PAGE_SIZE)
        kw = str(key or '').strip()
        if not kw:
            return {'list': [], 'page': page, 'pagecount': 1,
                    'limit': size, 'total': 0}
        data = self._get('/search', {'q': kw, 'page': page, 'size': size})
        return self._page_result(data, page, size)

    def searchContent(self, key, quick=False, pg="1"):
        return self.searchContentPage(key, quick, pg)

    # ------------------------------------------------------------------ #
    # 播放
    # ------------------------------------------------------------------ #
    def playerContent(self, flag, id, vipFlags=None):
        raw = str(id or '').strip()
        # 兼容 "集名$URL" 这种整段传进来的情况
        if '$' in raw and not raw.startswith('http'):
            tail = raw.rsplit('$', 1)[-1].strip()
            if tail.startswith('http'):
                raw = tail
        # 兼容只给了纯数字影片 id：自动取第一条线路第一集
        if raw.isdigit():
            try:
                info = _asdict(self._get('/video/' + raw))
                for src in _aslist(info.get('sources')):
                    for ep in _aslist(_asdict(src).get('episodes')):
                        u = str(_asdict(ep).get('url') or '').strip()
                        if u:
                            raw = u
                            break
                    if raw and not raw.isdigit():
                        break
            except Exception:
                pass
        return {
            'parse': 0,
            'playUrl': '',
            'url': raw,
            'header': {
                'User-Agent': UA,
                'Referer': self.host + '/',
                'Origin': self.host,
            },
        }

    def localProxy(self, param):
        # 播放地址是第三方 m3u8 直链，可直接播放，无需本地代理
        return [200, 'text/plain', '', '']


# --------------------------------------------------------------------------- #
# 顶层转发层：部分壳按模块函数调用，保留这一层最省事
# --------------------------------------------------------------------------- #
_S = None


def _inst():
    global _S
    if _S is None:
        _S = Spider()
        _S.init()
    return _S


def getName():
    return _inst().getName()


def init(extend=""):
    return _inst().init(extend)


def isVideoFormat(url):
    return _inst().isVideoFormat(url)


def manualVideoCheck():
    return _inst().manualVideoCheck()


def destroy():
    return _inst().destroy()


def homeContent(filter=False):
    return _inst().homeContent(filter)


def homeVideoContent():
    return _inst().homeVideoContent()


def categoryContent(tid, pg="1", filter=False, extend=None):
    return _inst().categoryContent(tid, pg, filter, extend)


def detailContent(ids):
    return _inst().detailContent(ids)


def searchContent(key, quick=False, pg="1"):
    return _inst().searchContent(key, quick, pg)


def searchContentPage(key, quick=False, pg="1"):
    return _inst().searchContentPage(key, quick, pg)


def playerContent(flag, id, vipFlags=None):
    return _inst().playerContent(flag, id, vipFlags)


def localProxy(param):
    return _inst().localProxy(param)


# --------------------------------------------------------------------------- #
# 自测：python 南瓜.py --selftest
# --------------------------------------------------------------------------- #
if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    s = Spider()
    s.init()
    print('站点: %s' % s.host)
    print('名称: %s' % s.getName())

    h = s.homeContent(True)
    print('\n[首页] 分类 %d 个: %s' % (
        len(h.get('class') or []),
        '、'.join([c['type_name'] for c in (h.get('class') or [])])))
    print('[首页] 推荐 %d 条, 首条: %s' % (
        len(h.get('list') or []),
        (h.get('list') or [{}])[0].get('vod_name', '-')))
    print('[首页] 筛选组: %s' % ', '.join(
        [f['name'] for f in (h.get('filters') or {}).get('movie', [])]))

    c1 = s.categoryContent('movie', 1, True, None)
    c2 = s.categoryContent('movie', 2, True, None)
    print('\n[分类] 电影 共 %s 部 / %s 页, 本页 %d 条' % (
        c1.get('total'), c1.get('pagecount'), len(c1.get('list') or [])))
    print('[分类] 第1页前3: %s' % [x['vod_name'] for x in (c1.get('list') or [])[:3]])
    print('[分类] 第2页前3: %s' % [x['vod_name'] for x in (c2.get('list') or [])[:3]])
    cf = s.categoryContent('movie', 1, True, {'genre': '喜剧', 'year': str(_YEAR), 'sort': 'hot'})
    print('[筛选] 喜剧/%s/最热 -> %s 部, 首条: %s' % (
        _YEAR, cf.get('total'),
        (cf.get('list') or [{}])[0].get('vod_name', '-')))

    sr = s.searchContent('喜剧', False, 1)
    print('\n[搜索] "喜剧" 共 %s 条, 前3: %s' % (
        sr.get('total'), [x['vod_name'] for x in (sr.get('list') or [])[:3]]))

    first = (c1.get('list') or [{}])[0].get('vod_id')
    if first:
        det = s.detailContent([first])
        vod = (det.get('list') or [{}])[0]
        froms = (vod.get('vod_play_from') or '').split('$$$')
        groups = (vod.get('vod_play_url') or '').split('$$$')
        print('\n[详情] id=%s %s' % (first, vod.get('vod_name')))
        print('[详情] 线路: %s' % '、'.join(froms))
        for name, grp in zip(froms, groups):
            print('       %s: %d 集' % (name, len([x for x in grp.split('#') if x])))
        u = ''
        if groups and '$' in groups[0]:
            u = groups[0].split('#')[0].rsplit('$', 1)[-1]
        print('[详情] 首集地址: %s' % u)
        p = s.playerContent(froms[0] if froms else '', u)
        print('[播放] parse=%s, 视频格式=%s, url=%s' % (
            p.get('parse'), s.isVideoFormat(p.get('url')), p.get('url')))
    print('\n自测完成。')
