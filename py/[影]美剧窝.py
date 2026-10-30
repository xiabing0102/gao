# -*- coding: utf-8 -*-
# TVBox / OK影视(OKPro影视家, FongMi内核) / 影视壳 通用 Python 源 —— 美剧窝
# 站点: https://www.mjwo.net/ (天天美剧_人人美剧天堂 - 美剧窝)
#
# 全链路实测(2026-09-18, 匿名可访问):
#   - 频道: 导航共有 11 个内容频道, 完整列表页在 /show/{slug}/ (每页24条):
#       电影 dianying(541页) 美剧 meiju(288) 港剧 gangju(41) 动作片 dongzuopian(76)
#       喜剧片 xijupian(94) 爱情片 aiqingpian(34) 科幻片 kehuanpian(26)
#       恐怖片 kongbupian(82) 剧情片 juqingpian(196) 战争片 zhanzhengpian(10)
#       动画片 donghuapian(28)
#   - 分页: /show/{slug}/page/{n}/
#   - 筛选可叠加(各频道通用, 均已实测): /show/{slug}/class/{类型}/year/{年份}/
#       isend/{完结|连载}/by/{time|hits|score}/page/{n}/
#   - 条目: <div class="myui-vodlist__box"> 内 <a href="/vod/{id}/" title="{名}"
#           data-original="{封面}"> 封面角标 span.pic-text, 副信息 p.text-muted(年/地区/类型)
#   - 详情: /vod/{id}/ 内 img.lazyload data-original 为封面,
#           简介在 span.data, 选集 <a class="btn btn-gray" href="/play/{vid}-{sid}-{nid}/">第{n}集</a>
#   - 播放页 /play/{vid}-{sid}-{nid}/: 内嵌 <script>var player_aaaa={...,"url":"{加密id}",...}
#   - 播放解析: https://edge.apiimg.com/super.php?id={加密id} 响应内含
#           window.PLAYER_CONFIG = { lineList: [{"name":"线路 1","url":"https:\/\/...m3u8?...\u0026expires=..."}...] }
#           JSON 转义(\\/, \\u0026), 多条 m3u8 直链匿名可播(HTTP 200, #EXTM3U),
#           token/expires 每次请求刷新
#   - 搜索(/search/--/?wd=...) 被站方"系统安全验证"验证码保护, 采集接口 api.php 返回 closed
#     -> 搜索与采集通道站方未开放, 按合规处理不绕过, searchContent 返回空列表
#
# 实现: urllib 标准库 + 正则, 无第三方依赖; 所有网络/解析失败降级空结构, 不向壳抛异常

import json
import re
from html import unescape as _unescape
from urllib import parse as _up
from urllib import request as _ur

from base.spider import Spider

HOST = 'https://www.mjwo.net'
SUPER = 'https://edge.apiimg.com/super.php'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# 频道表: (type_id, type_name) — 与站点导航一致, 完整列表页均在 /show/{slug}/
CHANNELS = [
    ('dianying', '电影'),
    ('meiju', '美剧'),
    ('gangju', '港剧'),
    ('dongzuopian', '动作片'),
    ('xijupian', '喜剧片'),
    ('aiqingpian', '爱情片'),
    ('kehuanpian', '科幻片'),
    ('kongbupian', '恐怖片'),
    ('juqingpian', '剧情片'),
    ('zhanzhengpian', '战争片'),
    ('donghuapian', '动画片'),
]

# 分类 filter 类型值(实测自列表页筛选导航)
GENRES = ['剧情', '喜剧', '爱情', '动作', '惊悚', '悬疑', '恐怖', '犯罪',
          '科幻', '冒险', '奇幻', '战争', '历史', '古装', '家庭', '武侠',
          '生活', '灾难', '歌舞', '预告', '都市', '传奇', '穿越', '动画',
          '传记', '偶像', '校园', '青春', '运动', '同性', '西部', '纪录',
          '音乐']
YEARS = ['2026', '2025', '2024', '2023', '2022', '2021', '2020',
         '2010-2019', '2000-2009', '1990-1999', '1980-1989', '1800-1979']


def _choices(items, with_all=True):
    out = [{'n': '全部', 'v': ''}] if with_all else []
    out += [{'n': str(x), 'v': str(x)} for x in items]
    return out


# 各频道通用筛选组(类型/年份/状态/排序), 实测全频道可用
_FILTER_GROUPS = [
    {'key': 'class', 'name': '类型', 'value': _choices(GENRES)},
    {'key': 'year', 'name': '年份', 'value': _choices(YEARS)},
    {'key': 'isend', 'name': '状态',
     'value': [{'n': '全部', 'v': ''},
               {'n': '完结', 'v': '完结'},
               {'n': '连载', 'v': '连载'}]},
    {'key': 'by', 'name': '排序',
     'value': [{'n': '时间', 'v': 'time'},
               {'n': '人气', 'v': 'hits'},
               {'n': '评分', 'v': 'score'}]},
]


def _get(url, timeout=12):
    """GET 文本; 任何失败返回 ''(不抛异常)"""
    try:
        req = _ur.Request(url, headers={
            'User-Agent': UA,
            'Referer': HOST + '/',
        })
        with _ur.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', 'ignore')
    except Exception:
        return ''


def _clean_ids(ids):
    """兼容 '46:123' / '123' / ['123'] 多种 ids 传参"""
    if isinstance(ids, (list, tuple)):
        ids = ids[0] if ids else ''
    s = str(ids or '').strip()
    return s.split(':')[-1] if ':' in s else s


def _parse_vodlist(html):
    """解析 myui-vodlist__box 条目块 -> list[vod dict]"""
    out = []
    for m in re.finditer(r'<div class="myui-vodlist__box">(.*?)'
                         r'<div class="myui-vodlist__detail">(.*?)'
                         r'</div>\s*</div>', html, re.S):
        head, detail = m.group(1), m.group(2)
        vm = re.search(r'href="(/vod/(\d+)/)" title="([^"]+)"'
                       r' data-original="([^"]+)"', head)
        if not vm:
            continue
        pic = ''
        rm = re.search(r'pic-text[^>]*>\s*([^<]*)', head)
        dm = re.search(r'href="/vod/\d+/" title="[^"]*">([^<]*)</a>', detail)
        tm = re.search(r'text-muted[^>]*>\s*([^<]*)', detail)
        vod = {
            'vod_id': vm.group(2),
            'vod_name': vm.group(3),
            'vod_pic': vm.group(4),
            'vod_remarks': rm.group(1).strip() if rm else '',
            'vod_area': tm.group(1).strip().split('/')[1].strip()
            if tm and '/' in tm.group(1) else '',
        }
        if dm:
            vod['vod_name'] = dm.group(1).strip()
        out.append(vod)
    return out


def _parse_classes(html):
    """从筛选导航解析分类 filter 实际可用项(可选)"""
    return []


class Spider(Spider):

    def getName(self):
        return '美剧窝'

    def init(self, extend=''):
        # 预留: extend 传 JSON(host) 可覆盖站点根地址
        global HOST
        if isinstance(extend, str) and extend.strip():
            s = extend.strip()
            if s.startswith('{'):
                try:
                    cfg = json.loads(s)
                    if cfg.get('host'):
                        HOST = str(cfg['host']).rstrip('/')
                except Exception:
                    pass
            elif s.startswith('http'):
                HOST = s.rstrip('/')

    def homeContent(self, filter):
        filters = {slug: [dict(g) for g in _FILTER_GROUPS]
                   for slug, _ in CHANNELS}
        html = _get(HOST + '/show/meiju/')
        return {
            'class': [{'type_id': slug, 'type_name': name}
                      for slug, name in CHANNELS],
            'filters': filters,
            'list': _parse_vodlist(html)[:24],
        }

    def homeVideoContent(self):
        html = _get(HOST + '/show/meiju/')
        return {'list': _parse_vodlist(html)[:24]}

    def _category_url(self, tid, page, filter):
        slug = str(tid or 'meiju')
        if slug not in dict(CHANNELS):
            slug = 'meiju'
        seg = '/show/%s/' % slug
        if filter and isinstance(filter, dict):
            for k in ('class', 'year', 'isend', 'by'):
                v = filter.get(k)
                if v:
                    seg += k + '/' + _up.quote(str(v)) + '/'
        seg += 'page/%d/' % page
        return HOST + seg

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg) if str(pg).isdigit() and int(pg) > 0 else 1
        except Exception:
            page = 1
        html = _get(self._category_url(tid, page, filter))
        items = _parse_vodlist(html)
        pagecount = 0
        for x in re.findall(r'/page/(\d+)/', html):
            try:
                pagecount = max(pagecount, int(x))
            except Exception:
                pass
        return {
            'page': page,
            'pagecount': pagecount,
            'limit': len(items) or 24,
            'total': (pagecount or 0) * (len(items) or 24),
            'list': items,
        }

    def detailContent(self, ids):
        vid = _clean_ids(ids)
        if not vid:
            return {'list': []}
        html = _get(HOST + '/vod/%s/' % vid)
        if not html:
            return {'list': []}
        name = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        vod_name = re.sub(r'<[^>]+>', '', name.group(1)).strip() if name else ''
        pic = re.search(r'<img[^>]*data-original="([^"]+)"', html)
        desc = re.search(r'<span class="data"\s*>\s*<p>(.*?)</p>', html, re.S)
        play_url = []
        # 选集: 播放列表容器 ul.myui-content__list 内 btn-gray 链接,
        # 文本既可能是"第{nn}集", 也可能是单集标记(如"HD高清"/"正片"/"蓝光")
        ul = re.search(r'<ul class="myui-content__list[^"]*"[^>]*>(.*?)</ul>', html, re.S)
        if ul:
            for ep in re.finditer(r'<a class="btn btn-gray" href="(/play/[^"]+/)"'
                                  r'[^>]*>\s*([^<]+?)\s*</a>', ul.group(1)):
                label = _unescape(ep.group(2)).strip()
                if label:
                    play_url.append('%s$%s' % (label, HOST + ep.group(1)))
        vod = {
            'vod_id': vid,
            'vod_name': vod_name,
            'vod_pic': pic.group(1) if pic else '',
            'vod_content': desc.group(1).strip() if desc else '',
            'vod_play_from': '云播',
            'vod_play_url': '#'.join(play_url),
        }
        return {'list': [vod] if play_url or vod_name else []}

    def searchContent(self, key, quick, pg='1'):
        # 站方搜索被"系统安全验证"验证码保护(实测 2026-09-18), 采集接口亦关闭;
        # 不绕过访问控制, 按合规返回空列表
        return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        try:
            play_url = str(id or '').strip()
            if not play_url:
                return {}
            if not play_url.startswith('http'):
                play_url = HOST + play_url
            html = _get(play_url)
            m = re.search(r'var player_aaaa=(\{.*?\})\s*</script>', html, re.S)
            if not m:
                return {}
            enc = json.loads(m.group(1)).get('url') or ''
            if not enc:
                return {}
            super_html = _get(SUPER + '?id=' + _up.quote(enc, safe='='))
            lm = re.search(r'lineList:\s*(\[[\s\S]*?\])\s*,', super_html)
            if not lm:
                return {}
            lines = json.loads(lm.group(1))
            urls = [x.get('url') for x in lines if x.get('url')]
            if not urls:
                return {}
            return {
                'parse': 0,
                'url': urls[0],
                'header': json.dumps({'User-Agent': UA}),
            }
        except Exception:
            return {}

    def localProxy(self, param):
        return [200, 'video/MP2T', '', '']

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False