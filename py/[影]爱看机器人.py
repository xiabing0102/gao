#coding=utf-8
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox / 影视仓 Python源脚本
站点: 爱看机器人 (www1.ikanbot.com)
说明: 苹果CMS二开，token逆向获取播放源，纯正则提取兼容TVbox
"""

import sys
import re
import json
import requests
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def __init__(self):
        super().__init__()
        self.site = 'https://www1.ikanbot.com'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site + '/'
        })
        self.cateManual = {
            '电影': 'movie',
            '剧集': 'tv',
            '动漫': '18',
            '综艺': '19',
        }

    def init(self, extend=""):
        pass

    def getName(self):
        return "爱看机器人"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def getVid(self, url):
        if not url:
            return ''
        m = re.search(r'/play/(\d+)', url)
        if m:
            return m.group(1)
        return ''

    def get_tks(self, currentId, e_token):
        """逆向 get_tks 函数：从e_token和videoId末4位生成token"""
        try:
            substr = currentId[-4:]
            token = ''
            remaining = e_token
            for ch in substr:
                pos = int(ch) % 3 + 1
                if pos + 8 > len(remaining):
                    break
                token += remaining[pos:pos+8]
                remaining = remaining[pos+8:]
            return token
        except:
            return ''

    # ============ ★ 海报提取 ============
    def _abs_pic(self, pic):
        """补全图片 URL 的协议和域名"""
        if not pic:
            return ''
        pic = pic.strip()
        if pic.startswith('//'):
            return 'https:' + pic
        if pic.startswith('/'):
            return self.site + pic
        if not pic.startswith('http'):
            return self.site + '/' + pic
        return pic

    def _extract_pic(self, fragment):
        """★ 从 HTML 片段提取海报 URL（核心修复）
        优先级：data-src > data-original > src
        跳过 data:image/svg 占位符、tv_default_medium.png 等占位图
        """
        if not fragment:
            return ''
        # 1) data-src（懒加载真实图，爱看机器人的主要来源）
        for m in re.finditer(r'data-src="([^"]+)"', fragment):
            url = m.group(1).strip()
            if not url or url.startswith('data:'):
                continue
            if 'svg+xml' in url.lower():
                continue
            return self._abs_pic(url)
        # 2) data-original
        for m in re.finditer(r'data-original="([^"]+)"', fragment):
            url = m.group(1).strip()
            if not url or url.startswith('data:'):
                continue
            if 'svg+xml' in url.lower():
                continue
            return self._abs_pic(url)
        # 3) src（跳过占位图）
        for m in re.finditer(r'\bsrc="([^"]+)"', fragment):
            url = m.group(1).strip()
            if not url or url.startswith('data:'):
                continue
            low = url.lower()
            if 'tv_default' in low or 'placeholder' in low or 'load_tv' in low:
                continue
            return self._abs_pic(url)
        return ''

    def _extract_title_home(self, fragment):
        """主页卡片标题：优先 <p>，其次 img 的 alt"""
        tm = re.search(r'<p[^>]*>([^<]+)</p>', fragment)
        if tm:
            return tm.group(1).strip()
        tm = re.search(r'alt="([^"]+)"', fragment)
        if tm:
            return tm.group(1).strip()
        return ''

    def _extract_title_search(self, fragment):
        """搜索卡片标题：优先 class="title-text" 的 <a>"""
        tm = re.search(r'class="title-text"[^>]*>([^<]+)</a>', fragment)
        if tm:
            return tm.group(1).strip()
        # 兜底：<h5 class="media-heading"> 里的第一个 <a>
        tm = re.search(
            r'<h5[^>]*class="[^"]*media-heading[^"]*"[^>]*>\s*<a[^>]*>([^<]+)</a>',
            fragment, re.DOTALL
        )
        if tm:
            return tm.group(1).strip()
        return ''

    def extract_vod_list(self, html):
        """★ 提取影片列表（重写，兼容主页 / 搜索页两种结构）"""
        result = []
        seen = set()
        if not html:
            return result

        # ============ 模式1: 主页卡片 <a class="item" href="/play/xxx">...<p>标题</p></a> ============
        pattern1 = r'<a[^>]*class="[^"]*\bitem\b[^"]*"[^>]*href="(/play/(\d+))"[^>]*>(.*?)</a>'
        for m in re.finditer(pattern1, html, re.DOTALL):
            vid = m.group(2)
            if vid in seen:
                continue
            seen.add(vid)

            inner = m.group(3)
            title = self._extract_title_home(inner)
            pic = self._extract_pic(inner)
            if title:
                result.append((vid, title, pic))

        # ============ 模式2: 搜索页媒体卡片 <div class="media">...</div> ============
        # 用每个 <div class="media"> 的起始位置分割块，避免嵌套 div 导致正则截断
        positions = [
            m.start() for m in
            re.finditer(r'<div[^>]*class="media"', html)
        ]
        for i, start in enumerate(positions):
            end = positions[i + 1] if i + 1 < len(positions) else len(html)
            block = html[start:end]

            vid_m = re.search(r'href="/play/(\d+)"', block)
            if not vid_m:
                continue
            vid = vid_m.group(1)
            if vid in seen:
                continue
            seen.add(vid)

            title = self._extract_title_search(block)
            pic = self._extract_pic(block)
            if title:
                result.append((vid, title, pic))

        # ============ 模式3: 兜底简单链接 ============
        if not result:
            for m in re.finditer(r'<a[^>]*href="(/play/(\d+))"[^>]*>([^<]+)</a>', html):
                vid = m.group(2)
                title = m.group(3).strip()
                if vid not in seen and title and 0 < len(title) <= 100:
                    seen.add(vid)
                    result.append((vid, title, ''))

        return result

    def homeContent(self, filter):
        result = {'class': [], 'filters': {}, 'list': [], 'parse': 0, 'jx': 0}
        for k, v in self.cateManual.items():
            result['class'].append({
                'type_id': str(v),
                'type_name': k
            })
        return result

    def homeVideoContent(self):
        videos = []
        try:
            r = self.session.get(self.site, timeout=15)
            r.encoding = 'utf-8'
            vod_list = self.extract_vod_list(r.text)
            for vid, title, pic in vod_list:
                videos.append({
                    'vod_id': vid,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': ''
                })
        except Exception as e:
            print(f'homeVideoContent error: {e}')
        return {'list': videos, 'parse': 0, 'jx': 0}

    def categoryContent(self, tid, pg, filter, extend):
        result = {'list': [], 'parse': 0, 'jx': 0}
        page = int(pg) if pg else 1
        try:
            if tid in ('movie', 'tv'):
                # 电影/剧集用 /hot/ 页面
                if page == 1:
                    url = f'{self.site}/hot/index-{tid}-%E7%83%AD%E9%97%A8.html'
                else:
                    url = f'{self.site}/hot/index-{tid}-%E7%83%AD%E9%97%A8-p-{page}.html'
            else:
                # 动漫/综艺用 /category/ 页面
                if page == 1:
                    url = f'{self.site}/category/{tid}'
                else:
                    url = f'{self.site}/category/{tid}?p={page}'
            r = self.session.get(url, timeout=15)
            r.encoding = 'utf-8'
            vod_list = self.extract_vod_list(r.text)
            for vid, title, pic in vod_list:
                result['list'].append({
                    'vod_id': vid,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': ''
                })
        except Exception as e:
            print(f'categoryContent error: {e}')

        result['page'] = page
        result['pagecount'] = page + 1 if len(result['list']) > 0 else page
        result['limit'] = len(result['list'])
        result['total'] = len(result['list'])
        return result

    def detailContent(self, ids):
        result = {'list': [], 'parse': 0, 'jx': 0}
        vid = ''
        if isinstance(ids, list):
            vid = ids[0] if ids else ''
        else:
            vid = str(ids)
        if not vid:
            return result
        try:
            url = f'{self.site}/play/{vid}'
            r = self.session.get(url, timeout=15)
            r.encoding = 'utf-8'
            html = r.text

            # 标题
            title = ''
            m = re.search(r'<title>([^<]+)<', html)
            if m:
                t = m.group(1).strip()
                title = re.sub(r'\s*[-–—].*$', '', t).strip()

            # 封面（用统一的 _extract_pic）
            pic = self._extract_pic(html)

            # 简介
            desc = ''
            for m in re.finditer(r'(?:描述|简介|剧情)[^<]*<[^>]*>([^<]+)', html):
                text = m.group(1).strip()
                if len(text) > 20:
                    desc = text
                    break

            # 获取 e_token 并调用 API 获取播放源
            e_token = ''
            m = re.search(r'id="e_token"\s+value="([^"]+)"', html)
            if m:
                e_token = m.group(1)

            play_from = []
            play_url = []
            if e_token:
                token = self.get_tks(str(vid), e_token)
                if token:
                    try:
                        r2 = self.session.get(f'{self.site}/api/getResN', params={
                            'videoId': vid,
                            'mtype': '1',
                            'token': token
                        }, timeout=15)
                        resp = r2.json()
                        data_list = resp.get('data', {}).get('list', [])
                        for line in data_list:
                            line_name = line.get('name', '') or f'线路{len(play_from)+1}'
                            res_data = json.loads(line.get('resData', '[]'))
                            episodes = []
                            for ep in res_data:
                                ep_name = ep.get('newName', '') or f'第{len(episodes)+1}集'
                                ep_url = ep.get('url', '')
                                if ep_url:
                                    episodes.append(f'{ep_name}${ep_url}')
                            if episodes:
                                play_from.append(line_name)
                                play_url.append('#'.join(episodes))
                    except Exception as e:
                        print(f'getResN error: {e}')

            vod = {
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'type_name': '',
                'vod_year': '',
                'vod_area': '',
                'vod_remarks': '',
                'vod_actor': '',
                'vod_director': '',
                'vod_content': desc,
                'vod_play_from': '$$$'.join(play_from) if play_from else '',
                'vod_play_url': '$$$'.join(play_url) if play_url else ''
            }
            result['list'].append(vod)
        except Exception as e:
            print(f'detailContent error: {e}')
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        try:
            play_url = id
            if '$' in play_url:
                play_url = play_url.split('$')[-1]
            result['parse'] = 0
            result['url'] = play_url
            result['jx'] = 0
            result['header'] = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': self.site + '/'
            }
        except Exception as e:
            print(f'playerContent error: {e}')
            result['parse'] = 1
            result['url'] = id
            result['jx'] = 0
        return result

    def searchContent(self, key, quick, pg='1'):
        result = {'list': [], 'parse': 0, 'jx': 0}
        page = int(pg) if pg else 1
        try:
            url = f'{self.site}/search?q={key}'
            if page > 1:
                url += f'&page={page}'
            r = self.session.get(url, timeout=15)
            r.encoding = 'utf-8'
            vod_list = self.extract_vod_list(r.text)
            for vid, title, pic in vod_list:
                result['list'].append({
                    'vod_id': vid,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': ''
                })
        except Exception as e:
            print(f'searchContent error: {e}')

        result['page'] = page
        result['pagecount'] = page + 1 if len(result['list']) > 0 else page
        result['limit'] = len(result['list'])
        result['total'] = len(result['list'])
        return result

    def localProxy(self, params):
        return [200, "video/MP2T", {}, ""]