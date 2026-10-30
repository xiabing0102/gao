#coding=utf-8
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox / 影视仓  Python源脚本 - 可可影视
修复：海报显示（CDN 域名 + 占位图识别 + 双属性回退）
"""

import sys
import re
import json
import requests
import urllib3
from urllib.parse import quote
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Spider(Spider):

    def __init__(self):
        super().__init__()
        self.site = 'https://103.51.147.112:51120'
        # 修复1：图片 CDN 域名更正为 vres.esadj.com
        self.pic_host = 'https://vres.esadj.com'
        # 静态资源域名（仅用于识别占位符）
        self.static_host = 'https://vf.esadj.com'

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://103.51.147.112:51120/'
        })
        self.cateManual = {
            '电影': '1',
            '连续剧': '2',
            '动漫': '3',
            '综艺纪录': '4',
            '短剧': '6'
        }
        self._mark = chr(26143) + chr(27821)

    def init(self, extend=""):
        pass

    def getName(self):
        return "可可影视"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    # ==================================================================
    # 核心修复：海报地址提取
    # ==================================================================
    def _is_placeholder(self, url):
        """判断是否为占位图/无效图"""
        if not url:
            return True
        low = url.lower()
        skip_keys = [
            'placeholder', 'blank.gif', 'logo_placeholder',
            'nonecoverimg', 'logo.png', 'logo_horizontal.png',
            'data:image', 'base64', 'avatar.png',
        ]
        return any(k in low for k in skip_keys)

    def _fix_pic_url(self, url):
        """把相对路径补全为完整海报 URL（用正确的 vres 域名）"""
        if not url:
            return ''
        url = url.strip()
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('http://') or url.startswith('https://'):
            return url
        if url.startswith('/'):
            return self.pic_host + url
        return self.pic_host + '/' + url

    def _extract_pic(self, item):
        """
        从 module-item 中提取真实海报地址
        规则：
          1. 遍历该 item 下所有 <img>
          2. 对每张图，按 data-original → data-src → src 顺序尝试
          3. 跳过占位符/无效图
          4. 相对路径用 vres.esadj.com 补全
        """
        imgs = item.find('img')
        for j in range(len(imgs)):
            img = imgs.eq(j)
            for attr in ('data-original', 'data-src', 'src'):
                raw = img.attr(attr)
                if not raw:
                    continue
                if self._is_placeholder(raw):
                    continue
                fixed = self._fix_pic_url(raw)
                if fixed:
                    return fixed
        return ''

    # ==================================================================
    # 首页
    # ==================================================================
    def homeContent(self, filter):
        result = {'class': [], 'filters': {}, 'list': [], 'parse': 0, 'jx': 0}
        for k, v in self.cateManual.items():
            result['class'].append({
                'type_id': str(v),
                'type_name': k
            })
            result['filters'][str(v)] = self._get_filters(str(v))
        return result

    def homeVideoContent(self):
        videos = []
        try:
            url = f'{self.site}/channel/1.html'
            r = self.session.get(url, timeout=15, verify=False)
            r.encoding = 'utf-8'
            doc = pq(r.text)
            items = doc('.module-item')
            seen = set()
            for item in items.items():
                a = item.find('.v-item')
                href = a.attr('href') or ''
                vid = self.getVid(href)
                if not vid or vid in seen:
                    continue
                seen.add(vid)

                # 标题
                titles = item.find('.v-item-title')
                title = ''
                for j in range(len(titles)):
                    t = titles.eq(j).text().strip()
                    if t and t != '可可影视-kekys.com':
                        title = t
                        break

                # 修复2：使用统一的 _extract_pic
                pic = self._extract_pic(item)

                # 备注
                note = ''
                bottom = item.find('.v-item-bottom span')
                if bottom.length:
                    note = bottom.text().strip()

                if title:
                    videos.append({
                        'vod_id': vid,
                        'vod_name': title,
                        'vod_pic': pic,
                        'vod_remarks': note
                    })
        except Exception as e:
            print(f'homeVideoContent error: {e}')
        return {'list': videos[:24], 'parse': 0, 'jx': 0}

    # ==================================================================
    # 筛选配置（各频道独立）
    # ==================================================================
    def _year_opts(self):
        return [
            {'n': '全部', 'v': ''}, {'n': '2026', 'v': '2026'},
            {'n': '2025', 'v': '2025'}, {'n': '2024', 'v': '2024'},
            {'n': '2023', 'v': '2023'}, {'n': '2022', 'v': '2022'},
            {'n': '2021', 'v': '2021'}, {'n': '2020', 'v': '2020'},
            {'n': '10年代', 'v': '2010_2019'}, {'n': '00年代', 'v': '2000_2009'},
            {'n': '90年代', 'v': '1990_1999'}, {'n': '80年代', 'v': '1980_1989'},
            {'n': '更早', 'v': '0_1979'},
        ]

    def _order_opts(self):
        return [
            {'n': '综合', 'v': '1'}, {'n': '最新', 'v': '2'},
            {'n': '最热', 'v': '3'}, {'n': '评分', 'v': '4'},
        ]

    def _lang_opts(self):
        return [
            {'n': '全部', 'v': ''}, {'n': '国语', 'v': '国语'},
            {'n': '粤语', 'v': '粤语'}, {'n': '英语', 'v': '英语'},
            {'n': '日语', 'v': '日语'}, {'n': '韩语', 'v': '韩语'},
            {'n': '法语', 'v': '法语'}, {'n': '其他', 'v': '其他'},
        ]

    def _area_opts_full(self):
        return [
            {'n': '全部', 'v': ''}, {'n': '大陆', 'v': '中国大陆'},
            {'n': '香港', 'v': '中国香港'}, {'n': '台湾', 'v': '中国台湾'},
            {'n': '美国', 'v': '美国'}, {'n': '日本', 'v': '日本'},
            {'n': '韩国', 'v': '韩国'}, {'n': '英国', 'v': '英国'},
            {'n': '法国', 'v': '法国'}, {'n': '德国', 'v': '德国'},
            {'n': '印度', 'v': '印度'}, {'n': '泰国', 'v': '泰国'},
            {'n': '丹麦', 'v': '丹麦'}, {'n': '瑞典', 'v': '瑞典'},
            {'n': '巴西', 'v': '巴西'}, {'n': '加拿大', 'v': '加拿大'},
            {'n': '俄罗斯', 'v': '俄罗斯'}, {'n': '意大利', 'v': '意大利'},
            {'n': '比利时', 'v': '比利时'}, {'n': '爱尔兰', 'v': '爱尔兰'},
            {'n': '西班牙', 'v': '西班牙'}, {'n': '澳大利亚', 'v': '澳大利亚'},
            {'n': '其他', 'v': '其他'},
        ]

    def _area_opts_asia(self):
        return [
            {'n': '全部', 'v': ''}, {'n': '大陆', 'v': '中国大陆'},
            {'n': '香港', 'v': '中国香港'}, {'n': '台湾', 'v': '中国台湾'},
            {'n': '美国', 'v': '美国'}, {'n': '日本', 'v': '日本'},
            {'n': '韩国', 'v': '韩国'}, {'n': '英国', 'v': '英国'},
            {'n': '法国', 'v': '法国'}, {'n': '德国', 'v': '德国'},
            {'n': '印度', 'v': '印度'}, {'n': '泰国', 'v': '泰国'},
            {'n': '其他', 'v': '其他'},
        ]

    def _get_filters(self, tid):
        if tid == '1':
            return [
                {'key': 'class', 'name': '类型', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '剧情', 'v': '剧情'},
                    {'n': '喜剧', 'v': '喜剧'}, {'n': '动作', 'v': '动作'},
                    {'n': '爱情', 'v': '爱情'}, {'n': '恐怖', 'v': '恐怖'},
                    {'n': '惊悚', 'v': '惊悚'}, {'n': '犯罪', 'v': '犯罪'},
                    {'n': '科幻', 'v': '科幻'}, {'n': '悬疑', 'v': '悬疑'},
                    {'n': '奇幻', 'v': '奇幻'}, {'n': '冒险', 'v': '冒险'},
                    {'n': '战争', 'v': '战争'}, {'n': '历史', 'v': '历史'},
                    {'n': '古装', 'v': '古装'}, {'n': '家庭', 'v': '家庭'},
                    {'n': '传记', 'v': '传记'}, {'n': '武侠', 'v': '武侠'},
                    {'n': '歌舞', 'v': '歌舞'}, {'n': '短片', 'v': '短片'},
                    {'n': '动画', 'v': '动画'}, {'n': '儿童', 'v': '儿童'},
                    {'n': '职场', 'v': '职场'},
                ]},
                {'key': 'area', 'name': '地区', 'value': self._area_opts_full()},
                {'key': 'lang', 'name': '语言', 'value': self._lang_opts()},
                {'key': 'year', 'name': '年份', 'value': self._year_opts()},
                {'key': 'order', 'name': '排序', 'value': self._order_opts()},
            ]
        if tid == '2':
            return [
                {'key': 'class', 'name': '类型', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '剧情', 'v': '剧情'},
                    {'n': '爱情', 'v': '爱情'}, {'n': '喜剧', 'v': '喜剧'},
                    {'n': '犯罪', 'v': '犯罪'}, {'n': '悬疑', 'v': '悬疑'},
                    {'n': '古装', 'v': '古装'}, {'n': '动作', 'v': '动作'},
                    {'n': '家庭', 'v': '家庭'}, {'n': '惊悚', 'v': '惊悚'},
                    {'n': '奇幻', 'v': '奇幻'}, {'n': '美剧', 'v': '美剧'},
                    {'n': '科幻', 'v': '科幻'}, {'n': '历史', 'v': '历史'},
                    {'n': '战争', 'v': '战争'}, {'n': '韩剧', 'v': '韩剧'},
                    {'n': '武侠', 'v': '武侠'}, {'n': '言情', 'v': '言情'},
                    {'n': '恐怖', 'v': '恐怖'}, {'n': '冒险', 'v': '冒险'},
                    {'n': '都市', 'v': '都市'}, {'n': '职场', 'v': '职场'},
                ]},
                {'key': 'area', 'name': '地区', 'value': self._area_opts_asia()},
                {'key': 'lang', 'name': '语言', 'value': self._lang_opts()},
                {'key': 'year', 'name': '年份', 'value': self._year_opts()},
                {'key': 'order', 'name': '排序', 'value': self._order_opts()},
            ]
        if tid == '3':
            return [
                {'key': 'class', 'name': '类型', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '日漫', 'v': '日漫'},
                    {'n': '国漫', 'v': '国漫'}, {'n': '欧美动漫', 'v': '欧美动漫'},
                    {'n': '动漫电影', 'v': '动漫电影'}, {'n': '剧场版', 'v': '剧场版'},
                    {'n': '热血', 'v': '热血'}, {'n': '搞笑', 'v': '搞笑'},
                    {'n': '冒险', 'v': '冒险'}, {'n': '奇幻', 'v': '奇幻'},
                    {'n': '恋爱', 'v': '恋爱'}, {'n': '科幻', 'v': '科幻'},
                    {'n': '悬疑', 'v': '悬疑'}, {'n': '竞技', 'v': '竞技'},
                    {'n': '运动', 'v': '运动'}, {'n': '校园', 'v': '校园'},
                    {'n': '治愈', 'v': '治愈'}, {'n': '日常', 'v': '日常'},
                ]},
                {'key': 'area', 'name': '地区', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '日本', 'v': '日本'},
                    {'n': '大陆', 'v': '中国大陆'}, {'n': '美国', 'v': '美国'},
                    {'n': '其他', 'v': '其他'},
                ]},
                {'key': 'lang', 'name': '语言', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '日语', 'v': '日语'},
                    {'n': '国语', 'v': '国语'}, {'n': '英语', 'v': '英语'},
                    {'n': '其他', 'v': '其他'},
                ]},
                {'key': 'year', 'name': '年份', 'value': self._year_opts()},
                {'key': 'order', 'name': '排序', 'value': self._order_opts()},
            ]
        if tid == '4':
            return [
                {'key': 'class', 'name': '类型', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '真人秀', 'v': '真人秀'},
                    {'n': '脱口秀', 'v': '脱口秀'}, {'n': '选秀', 'v': '选秀'},
                    {'n': '搞笑', 'v': '搞笑'}, {'n': '访谈', 'v': '访谈'},
                    {'n': '生活', 'v': '生活'}, {'n': '音乐', 'v': '音乐'},
                    {'n': '游戏', 'v': '游戏'}, {'n': '亲子', 'v': '亲子'},
                    {'n': '情感', 'v': '情感'}, {'n': '纪实', 'v': '纪实'},
                    {'n': '纪录片', 'v': '纪录片'},
                ]},
                {'key': 'area', 'name': '地区', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '大陆', 'v': '中国大陆'},
                    {'n': '香港', 'v': '中国香港'}, {'n': '台湾', 'v': '中国台湾'},
                    {'n': '韩国', 'v': '韩国'}, {'n': '日本', 'v': '日本'},
                    {'n': '美国', 'v': '美国'}, {'n': '其他', 'v': '其他'},
                ]},
                {'key': 'lang', 'name': '语言', 'value': self._lang_opts()},
                {'key': 'year', 'name': '年份', 'value': self._year_opts()},
                {'key': 'order', 'name': '排序', 'value': self._order_opts()},
            ]
        if tid == '6':
            return [
                {'key': 'class', 'name': '类型', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '都市', 'v': '都市'},
                    {'n': '古装', 'v': '古装'}, {'n': '悬疑', 'v': '悬疑'},
                    {'n': '言情', 'v': '言情'}, {'n': '豪门', 'v': '豪门'},
                    {'n': '甜宠', 'v': '甜宠'}, {'n': '逆袭', 'v': '逆袭'},
                    {'n': '穿越', 'v': '穿越'}, {'n': '战神', 'v': '战神'},
                ]},
                {'key': 'area', 'name': '地区', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '大陆', 'v': '中国大陆'},
                    {'n': '其他', 'v': '其他'},
                ]},
                {'key': 'lang', 'name': '语言', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '国语', 'v': '国语'},
                    {'n': '其他', 'v': '其他'},
                ]},
                {'key': 'year', 'name': '年份', 'value': self._year_opts()},
                {'key': 'order', 'name': '排序', 'value': self._order_opts()},
            ]
        return self._get_filters('1')

    # ==================================================================
    # URL 构建
    # ==================================================================
    def _build_show_url(self, tid, extend, page):
        class_v = (extend.get('class') or '') if extend else ''
        area_v = (extend.get('area') or '') if extend else ''
        lang_v = (extend.get('lang') or '') if extend else ''
        year_v = (extend.get('year') or '') if extend else ''
        order_v = (extend.get('order') or '') if extend else ''
        if not order_v:
            order_v = '3'
        fields = [str(tid), class_v, area_v, lang_v, year_v, order_v, str(page)]
        return f'{self.site}/show/{"-".join(fields)}.html'

    # ==================================================================
    # 分类内容
    # ==================================================================
    def categoryContent(self, tid, pg, filter, extend):
        result = {'list': [], 'parse': 0, 'jx': 0}
        page = int(pg) if pg else 1

        if not extend:
            extend = {}
        if filter and isinstance(filter, dict):
            for k in ('class', 'area', 'lang', 'year', 'order'):
                if k not in extend or not extend.get(k):
                    if filter.get(k):
                        extend[k] = filter[k]

        try:
            url = self._build_show_url(tid, extend, page)
            print(f'categoryContent url = {url}')

            r = self.session.get(url, timeout=15, verify=False)
            r.encoding = 'utf-8'
            doc = pq(r.text)
            items = doc('.module-item')

            for item in items.items():
                a = item.find('.v-item')
                href = a.attr('href') or ''
                vid = self.getVid(href)
                if not vid:
                    continue

                titles = item.find('.v-item-title')
                title = ''
                for j in range(len(titles)):
                    t = titles.eq(j).text().strip()
                    if t and t != '可可影视-kekys.com':
                        title = t
                        break

                # 修复：统一使用 _extract_pic
                pic = self._extract_pic(item)

                note = ''
                bottom = item.find('.v-item-bottom span')
                if bottom.length:
                    note = bottom.text().strip()

                if title:
                    result['list'].append({
                        'vod_id': vid,
                        'vod_name': title,
                        'vod_pic': pic,
                        'vod_remarks': note
                    })
        except Exception as e:
            print(f'categoryContent error: {e}')

        result['page'] = page
        result['pagecount'] = page + 1 if len(result['list']) >= 24 else page
        result['limit'] = len(result['list'])
        result['total'] = len(result['list'])
        return result

    # ==================================================================
    # 详情
    # ==================================================================
    def detailContent(self, ids):
        result = {'list': [], 'parse': 0, 'jx': 0}
        vid = ids[0] if ids else ''
        if not vid:
            return result
        try:
            url = f'{self.site}/detail/{vid}.html'
            r = self.session.get(url, timeout=15, verify=False)
            r.encoding = 'utf-8'
            html = r.text

            title = ''
            title_match = re.search(r'<title>(.+?)</title>', html)
            if title_match:
                title = title_match.group(1).split('-')[0].strip()
                title = re.sub(r'[𝕜𝕜𝕪𝕤𝟘𝟙𝕔𝕠𝕞.\s]+', ' ', title).strip()
                title = re.sub(r'\s+', ' ', title).strip()

            # 修复：详情页海报也从 vres.esadj.com 取
            pic = ''
            og_img = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
            if og_img:
                pic = og_img.group(1)
                if pic.startswith('/'):
                    pic = self.pic_host + pic
            if not pic or self._is_placeholder(pic):
                # 退而求其次，从页面里找
                imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', html)
                for img in imgs:
                    if self._is_placeholder(img):
                        continue
                    pic = self._fix_pic_url(img)
                    break

            desc = ''
            desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html)
            if desc_match:
                desc = desc_match.group(1).strip()

            play_from = []
            play_url = []
            episodes_by_sid = {}
            sids_in_order = []
            seen_sids = set()

            all_play = re.findall(
                r'<a[^>]+href="(/play/\d+-(\d+)-(\d+)\.html)"[^>]+class="episode-item"[^>]*>(.*?)</a>',
                html, re.DOTALL)
            if not all_play:
                all_play = re.findall(
                    r'<a[^>]+class="episode-item"[^>]+href="(/play/\d+-(\d+)-(\d+)\.html)"[^>]*>(.*?)</a>',
                    html, re.DOTALL)

            for href, sid, nid, link_html in all_play:
                text = re.sub(r'<[^>]+>', '', link_html).strip()
                if not text:
                    continue
                if sid not in episodes_by_sid:
                    episodes_by_sid[sid] = []
                episodes_by_sid[sid].append(f'{text}${href}')
                if sid not in seen_sids:
                    seen_sids.add(sid)
                    sids_in_order.append(sid)

            source_labels = []
            all_labels = re.findall(r'class="source-item-label"[^>]*>([^<]+)</', html)
            for label in all_labels:
                label = label.strip()
                if label:
                    source_labels.append(label)

            for i, sid in enumerate(sids_in_order):
                if sid in episodes_by_sid and episodes_by_sid[sid]:
                    if i < len(source_labels):
                        line_name = source_labels[i]
                    else:
                        line_name = f'线路{sid}'
                    if line_name == '4K':
                        continue
                    play_from.append(line_name)
                    play_url.append('#'.join(episodes_by_sid[sid]))

            vod = {
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'type_name': '',
                'vod_year': '',
                'vod_area': '',
                'vod_remarks': '',
                'vod_actor': '',
                'vod_director': self._mark,
                'vod_content': desc,
                'vod_play_from': '$$$'.join(play_from) if play_from else '',
                'vod_play_url': '$$$'.join(play_url) if play_url else ''
            }
            result['list'].append(vod)
        except Exception as e:
            print(f'detailContent error: {e}')
        return result

    # ==================================================================
    # 播放
    # ==================================================================
    def playerContent(self, flag, id, vipFlags):
        result = {}
        try:
            play_url = id
            if id and not id.startswith('http'):
                play_url = self.site + id

            r = self.session.get(play_url, timeout=15, verify=False)
            r.encoding = 'utf-8'

            video_url = ''
            patterns = [
                r"src:\s*['\"]([^'\"]+\.(m3u8|mp4)[^'\"]*)['\"]",
                r'"url"\s*:\s*"([^"]+\.(m3u8|mp4)[^"]*)"',
                r"url\s*:\s*'([^']+\.(m3u8|mp4)[^']*)'",
            ]
            for pat in patterns:
                m = re.search(pat, r.text, re.DOTALL)
                if m:
                    video_url = m.group(1)
                    break

            if not video_url:
                all_urls = re.findall(
                    r'https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*', r.text)
                if all_urls:
                    for u in all_urls:
                        if 'index.m3u8' in u or 'video.m3u8' in u or '.mp4' in u:
                            video_url = u
                            break
                    if not video_url:
                        video_url = all_urls[0]

            if video_url and not video_url.startswith('http'):
                if video_url.startswith('/'):
                    video_url = self.site + video_url
                else:
                    video_url = self.site + '/' + video_url

            headers_out = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': self.site + '/'
            }

            if video_url:
                result['parse'] = 0
                result['url'] = video_url
                result['jx'] = 0
                result['header'] = headers_out
            else:
                result['parse'] = 1
                result['url'] = play_url
                result['jx'] = 0
                result['header'] = headers_out
        except Exception as e:
            print(f'playerContent error: {e}')
            result['parse'] = 1
            result['url'] = id if id.startswith('http') else self.site + id
            result['jx'] = 0
            result['header'] = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': self.site + '/'
            }
        return result

    # ==================================================================
    # 搜索
    # ==================================================================
    def searchContent(self, key, quick, pg='1'):
        result = {'list': [], 'parse': 0, 'jx': 0}
        page = int(pg) if pg else 1
        try:
            search_url = f'{self.site}/search?k={quote(key)}'
            r = self.session.get(search_url, timeout=15, verify=False)
            r.encoding = 'utf-8'
            t_match = re.search(r'name="t" value="([^"]+)"', r.text)
            t = t_match.group(1) if t_match else ''

            if t:
                url = f'{self.site}/search?k={quote(key)}&t={quote(t)}'
                if page > 1:
                    url += f'&page={page}'
                r = self.session.get(url, timeout=15, verify=False)
                r.encoding = 'utf-8'

            doc = pq(r.text)
            items = doc('.search-result-item')
            for item in items.items():
                href = item.attr('href') or ''
                if not href:
                    a_tag = item.find('a')
                    if a_tag.length:
                        href = a_tag.attr('href') or ''

                vid = self.getVid(href)
                if not vid:
                    continue

                title = ''
                title_elem = item.find('.title')
                if title_elem.length:
                    title = title_elem.text().strip()
                if not title:
                    img = item.find('img')
                    if img.length:
                        title = img.attr('alt') or img.attr('title') or ''
                        title = title.strip()

                # 修复：统一海报提取
                pic = self._extract_pic(item)

                if title:
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

    def getVid(self, url):
        if not url:
            return ''
        m = re.search(r'/detail/(\d+)\.html', url)
        if m:
            return m.group(1)
        m = re.search(r'/play/(\d+)-', url)
        if m:
            return m.group(1)
        return ''