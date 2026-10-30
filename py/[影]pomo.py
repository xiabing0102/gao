# coding=utf-8
# !/usr/bin/python
"""
@name    : Pomo4K
@author  : TVBox
@desc    : pomo.mom 4K 影视源 - 3路磁力播放线路
           兼容 FongMi/TV (T3) 与 WebHomeTV / PeekPro (T4)
@version : 3.0.0
@config  : {"proxy":"","timeout":15}
"""

import sys
import re
import json
import html as html_parser
from urllib.parse import quote

try:
    import requests
except ImportError:
    import urllib.request as _urllib


class Spider(object):
    def __init__(self, extend=''):
        self.site = 'https://pomo.mom'
        self.name = 'Pomo 4K'
        self.extend = extend
        self.headers = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/120.0.0.0 Safari/537.36'),
            'Referer': self.site + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }

    # ==================== 基本信息 ====================
    def getName(self):
        return self.name

    def getDependence(self):
        return []

    def init(self, extend=''):
        self.extend = extend

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        if u.startswith(('magnet:', 'thunder:', 'ed2k:')):
            return False
        return any(ext in u for ext in (
            '.m3u8', '.mp4', '.mkv', '.avi', '.flv', '.ts', '.mov', '.webm', '.m4v'
        ))

    def manualVideoCheck(self):
        return False

    # ==================== 首页分类 ====================
    def homeContent(self, filter):
        classes = [
            {'type_id': 'home',           'type_name': '首页'},
            {'type_id': 'huayurm',        'type_name': '华语热门'},
            {'type_id': 'jiating',        'type_name': '家庭影院'},
            {'type_id': 'donghuadadiany', 'type_name': '动画大电影'},
            {'type_id': 'lengmenjiapian', 'type_name': '冷门佳片'},
            {'type_id': 'paihangbang',    'type_name': 'TOP250'},
            {'type_id': 'sort/12',        'type_name': '蓝光原盘'},
            {'type_id': 'dianshiju',      'type_name': '剧集'},
        ]
        genres = ['人性', '传记', '儿童', '冒险', '剧情', '动作', '动画', '历史', '古装',
                  '同性', '喜剧', '奇幻', '家庭', '恐怖', '悬疑', '情色', '惊悚', '战争',
                  '歌舞', '武侠', '灾难', '爱情', '犯罪', '真人秀', '短片', '科幻', '纪录片',
                  '脱口秀', '西部', '运动', '音乐', '黑色电影']
        areas = ['大陆', '香港', '台湾', '亚洲', '海外', '欧美', '美国', '日本', '韩国',
                 '英国', '法国', '德国', '印度', '泰国', '瑞典', '巴西', '加拿大', '俄罗斯',
                 '意大利', '西班牙', '澳大利亚']
        langs = ['汉语普通话', '国语', '英语', '法语', '粤语', '日语', '韩语', '泰语',
                 '德语', '俄语', '闽南语', '丹麦语', '波兰语', '瑞典语', '印地语',
                 '挪威语', '意大利语', '西班牙语', '无对白']
        years = [str(y) for y in range(2026, 1930, -1)]

        filters = {}
        for c in classes:
            if c['type_id'] == 'home':
                continue
            filters[c['type_id']] = [
                {'key': 'genre', 'name': '类型',
                 'value': [{'n': '全部', 'v': ''}] + [{'n': g, 'v': g} for g in genres]},
                {'key': 'year',  'name': '年份',
                 'value': [{'n': '全部', 'v': ''}] + [{'n': y, 'v': y} for y in years]},
                {'key': 'area',  'name': '地区',
                 'value': [{'n': '全部', 'v': ''}] + [{'n': a, 'v': a} for a in areas]},
                {'key': 'lang',  'name': '语言',
                 'value': [{'n': '全部', 'v': ''}] + [{'n': l, 'v': l} for l in langs]},
                {'key': 'order', 'name': '排序',
                 'value': [
                     {'n': '最新', 'v': 'new'},
                     {'n': '最早', 'v': 'old'},
                     {'n': '评分', 'v': 'rating'},
                 ]},
            ]
        return {'class': classes, 'filters': filters}

    # ==================== 首页推荐 ====================
    def homeVideoContent(self):
        try:
            html_text = self._fetch(self.site + '/')
            return {'list': self._parse_list(html_text)}
        except Exception as e:
            print('[Pomo4K] homeVideoContent error:', e)
            return {'list': []}

    # ==================== 分类列表 ====================
    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg) if pg else 1
        except Exception:
            pg = 1
        if not tid or tid == 'home':
            base = self.site + '/'
        else:
            base = self.site + '/' + str(tid).strip('/') + '/'
        if pg > 1:
            base = base.rstrip('/') + '/page/' + str(pg)
        params = []
        if extend and isinstance(extend, dict):
            for k in ('genre', 'year', 'area', 'lang', 'order'):
                v = extend.get(k, '')
                if v:
                    params.append(k + '=' + quote(str(v)))
        if params:
            base += ('&' if '?' in base else '?') + '&'.join(params)
        try:
            html_text = self._fetch(base)
            videos = self._parse_list(html_text)
        except Exception as e:
            print('[Pomo4K] categoryContent error:', e)
            videos = []
        return {
            'list': videos,
            'page': pg,
            'pagecount': 9999,
            'limit': 20,
            'total': 999999,
        }

    # ==================== 视频详情（3路磁力线路）====================
    def detailContent(self, ids):
        try:
            vod_id = ids[0]
        except Exception:
            return {'list': []}
        if not vod_id.startswith('http'):
            vod_id = self.site + '/' + vod_id.lstrip('/')
        try:
            html_text = self._fetch(vod_id)
        except Exception as e:
            print('[Pomo4K] detailContent error:', e)
            return {'list': []}

        vod = {
            'vod_id': vod_id, 'vod_name': '', 'vod_pic': '',
            'vod_year': '', 'vod_area': '', 'vod_remarks': '',
            'vod_actor': '', 'vod_director': '', 'vod_content': '',
            'vod_play_from': '', 'vod_play_url': '',
        }

        # 标题
        m = re.search(r'<h[12][^>]*class="x-dbjs-title"[^>]*>(.*?)</h[12]>', html_text, re.S)
        if not m:
            m = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, re.S)
        if m:
            vod['vod_name'] = html_parser.unescape(
                re.sub(r'<[^>]+>', '', m.group(1)).strip())

        # 海报
        m = re.search(r'class="x-dbjs-poster"[^>]*>\s*<img[^>]*src="([^"]+)"', html_text, re.S)
        if not m:
            m = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html_text)
        if m:
            vod['vod_pic'] = m.group(1)

        # 元信息
        for block in re.findall(r'<div class="meta-row[^"]*"[^>]*>(.*?)</div>', html_text, re.S):
            text = html_parser.unescape(re.sub(r'<[^>]+>', '', block)).strip()
            text = re.sub(r'\s+', ' ', text)
            if not text:
                continue
            if '导演' in text:
                vod['vod_director'] = re.sub(r'^导演\s*[:：]\s*', '', text).strip()
            elif '主演' in text or '演员' in text:
                vod['vod_actor'] = re.sub(r'^(主演|演员阵容|演员)\s*[:：]\s*', '', text).strip()
            elif '国家' in text or '地区' in text:
                vod['vod_area'] = re.sub(r'^(国家|地区)\s*[:：]\s*', '', text).strip()
            elif '时间' in text or '年份' in text or '上映' in text:
                m2 = re.search(r'(\d{4})', text)
                if m2:
                    vod['vod_year'] = m2.group(1)

        # 简介
        m = re.search(r'<div class="x-dbjs-desc-block"[^>]*>.*?<p[^>]*>(.*?)</p>', html_text, re.S)
        if not m:
            m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html_text)
        if m:
            vod['vod_content'] = html_parser.unescape(
                re.sub(r'<[^>]+>', '', m.group(1)).strip())

        # ---------- 提取 accordion 磁力分组 ----------
        groups = self._parse_accordion_magnet_groups(html_text)
        # 最多保留 3 个线路
        groups = groups[:3]

        play_from = []
        play_urls = []
        for g in groups:
            play_from.append(g['title'])
            play_urls.append('#'.join([n + '$' + u for n, u in g['items']]))

        # 兜底：无任何磁力分组
        if not play_from:
            m = re.search(r'<a[^>]*class="play-btn[^"]*"[^>]*href="([^"]+)"', html_text)
            if m:
                play_from.append('在线播放')
                play_urls.append('在线播放$' + html_parser.unescape(m.group(1)))
            else:
                play_from.append('详情')
                play_urls.append('查看详情$' + vod_id)

        vod['vod_play_from'] = '$$$'.join(play_from)
        vod['vod_play_url'] = '$$$'.join(play_urls)

        return {'list': [vod]}

    # ==================== 搜索 ====================
    def searchContent(self, key, quick, pg='1'):
        try:
            pg = int(pg) if pg else 1
        except Exception:
            pg = 1
        url = self.site + '/?keyword=' + quote(key)
        if pg > 1:
            url += '&page=' + str(pg)
        try:
            html_text = self._fetch(url)
            videos = self._parse_list(html_text)
        except Exception as e:
            print('[Pomo4K] searchContent error:', e)
            videos = []
        return {'list': videos, 'page': pg}

    # ==================== 播放（磁力→客户端 P2P 播放）====================
    def playerContent(self, flag, id, vipFlags):
        """
        磁力/迅雷/ed2k 链接直接返回给播放器：
        - FongMi/T3：调用内置 P2P 引擎（libtorrent）自动加载并边下边播
        - WebHomeTV/PeekPro/T4：同上
        - 若客户端未集成 P2P 引擎，会弹出"复制磁力链"提示
        """
        url = (id or '').strip()
        header_json = json.dumps(self.headers, ensure_ascii=False)

        # 磁力 / 迅雷 / ed2k —— 交给客户端 P2P 播放器自动加载
        if url.startswith(('magnet:', 'thunder:', 'ed2k:')):
            return {
                'parse': 0,
                'playUrl': '',
                'url': url,
                'header': '',
                'format': 'application/x-bittorrent',
            }

        # 直链视频
        if self.isVideoFormat(url):
            return {
                'parse': 0,
                'playUrl': '',
                'url': url,
                'header': header_json,
                'format': 'video/*',
            }

        # 其他 HTTP
        if url.startswith('http'):
            return {
                'parse': 0,
                'playUrl': '',
                'url': url,
                'header': header_json,
            }

        return {'parse': 0, 'playUrl': '', 'url': url, 'header': ''}

    # ==================== 内部工具 ====================
    def _fetch(self, url):
        r = requests.get(url, headers=self.headers, timeout=15)
        r.encoding = 'utf-8'
        return r.text

    def _parse_accordion_magnet_groups(self, html_text):
        """
        解析详情页所有 accordion 分组，返回:
        [{'title': '原盘', 'items': [(名称, magnet), ...]}, ...]
        仅保留包含磁力/迅雷/ed2k 链接的分组
        """
        groups = []
        if not html_text:
            return groups

        # 按 accordion-item 切分
        parts = re.split(r'<div\s+class="x-dbjs-accordion-item', html_text)

        for part in parts[1:]:
            # 提取标题
            title_m = re.search(
                r'<span\s+class="x-dbjs-accordion-title"[^>]*>(.*?)</span>',
                part, re.S)
            if not title_m:
                continue
            raw_title = html_parser.unescape(
                re.sub(r'<[^>]+>', '', title_m.group(1))).strip()
            # "夸克网盘 : 一键转存，免下载在线看。" → "夸克网盘"
            title = re.split(r'[:：]', raw_title, 1)[0].strip()
            if not title:
                continue

            # 提取分组内所有磁力 download-link
            items = []
            for m in re.finditer(
                    r'<a\b[^>]*class="[^"]*x-dbjs-download-link[^"]*"[^>]*>(.*?)</a>',
                    part, re.S):
                a_tag = m.group(0)
                inner = m.group(1)

                url_m = re.search(r'data-url="([^"]+)"', a_tag)
                if not url_m:
                    url_m = re.search(r'href="([^"]+)"', a_tag)
                if not url_m:
                    continue

                url = html_parser.unescape(url_m.group(1).strip())
                if not url or url in ('javascript:;', '#', 'javascript:void(0);'):
                    continue

                # 只保留磁力/迅雷/ed2k
                if not url.startswith(('magnet:', 'thunder:', 'ed2k:')):
                    continue

                # 名称
                name = html_parser.unescape(re.sub(r'<[^>]+>', ' ', inner))
                name = re.sub(r'\s+', ' ', name).strip()
                if not name:
                    name = '磁力资源'

                # 文件大小（在 a 标签后面的兄弟节点中查找）
                size = ''
                tail = part[m.end():m.end() + 500]
                size_m = re.search(
                    r'class="file-size"[^>]*>\s*\[?([^\]<]+)\]?', tail)
                if size_m:
                    size = ' [' + size_m.group(1).strip().strip('[]') + ']'

                display = (name[:70] + '…') if len(name) > 70 else name
                display += size

                items.append((display, url))

            # 去重
            seen = set()
            uniq = []
            for n, u in items:
                if u in seen:
                    continue
                seen.add(u)
                uniq.append((n, u))

            if uniq:
                groups.append({'title': title, 'items': uniq})

        return groups

    def _parse_list(self, html_text):
        videos = []
        if not html_text:
            return videos
        pattern = re.compile(
            r'<a\s+href="(https?://pomo\.mom/\d+)"[^>]*>(.*?)</a>',
            re.S)
        seen = set()
        for m in pattern.finditer(html_text):
            href = m.group(1)
            if href in seen:
                continue
            seen.add(href)
            inner = m.group(2)
            title_m = re.search(r'<h3[^>]*>(.*?)</h3>', inner, re.S)
            if not title_m:
                continue
            title = html_parser.unescape(
                re.sub(r'<[^>]+>', '', title_m.group(1)).strip())
            if not title:
                continue
            img_m = re.search(r'<img[^>]*src="([^"]+)"', inner)
            pic = img_m.group(1) if img_m else ''
            remark = ''
            remark_m = re.search(
                r'<div class="text-\[12px\][^"]*text-gray-400[^"]*"[^>]*>(.*?)</div>',
                inner, re.S)
            if remark_m:
                remark = html_parser.unescape(
                    re.sub(r'<[^>]+>', '', remark_m.group(1)).strip())
            videos.append({
                'vod_id': href,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': remark,
            })
        return videos