# -*- coding: utf-8 -*-
# TVBox / 影视仓 / OK影视 Python 标准爬虫
# 站点: 四虎影视 (shxinju.com)
# 架构: 苹果CMS (MacCMS) 自定义模板 (hl-* 前缀)
# 特性: 多线路播放、player_aaaa解析、子分类筛选
# API已关闭, 全部走HTML解析
import sys
import re
import json
import time
from urllib.parse import quote

sys.path.append('..')
try:
    from base.spider import Spider
except Exception:
    class Spider(object):
        pass


class Spider(Spider):

    def getName(self):
        return '四虎影视'

    def init(self, extend=''):
        self.host = 'https://www.shxinju.com'
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.host + '/',
            'Connection': 'keep-alive',
        }
        # 缓存
        self._home_cache = []
        self._home_cache_time = 0
        self._cat_cache = {}          # 分类页缓存 {tid_page: data}
        self._cat_cache_time = {}     # 分类页缓存时间
        self._detail_cache = {}       # 详情缓存

    # ============================================================
    # 分类配置 - 新规范15: 父分类 + 子分类筛选器
    # ============================================================

    # 父分类 + 子分类 (新规范15: 子分类用独立tid)
    classes = [
        {'type_name': '电影', 'type_id': '1'},
        {'type_name': '电视剧', 'type_id': '2'},
        {'type_name': '综艺', 'type_id': '3'},
        {'type_name': '动漫', 'type_id': '4'},
        {'type_name': '短剧', 'type_id': '5'},
    ]

    # 子分类筛选器 (新规范15.2: 始终返回filters)
    # class筛选器使用子分类tid, 选择后替换父tid
    filters = {
        '1': [
            {'key': 'class', 'name': '类型', 'value': [
                {'n': '全部', 'v': ''},
                {'n': '动作片', 'v': '6'},
                {'n': '喜剧片', 'v': '7'},
                {'n': '爱情片', 'v': '8'},
                {'n': '科幻片', 'v': '9'},
                {'n': '恐怖片', 'v': '10'},
                {'n': '剧情片', 'v': '11'},
                {'n': '战争片', 'v': '12'},
                {'n': '纪录片', 'v': '13'},
                {'n': '悬疑片', 'v': '14'},
                {'n': '犯罪片', 'v': '15'},
                {'n': '奇幻片', 'v': '16'},
                {'n': '动画片', 'v': '31'},
            ]},
            {'key': 'area', 'name': '地区', 'value': [
                {'n': '全部', 'v': ''},
                {'n': '大陆', 'v': '大陆'},
                {'n': '香港', 'v': '香港'},
                {'n': '台湾', 'v': '台湾'},
                {'n': '日本', 'v': '日本'},
                {'n': '韩国', 'v': '韩国'},
                {'n': '美国', 'v': '美国'},
                {'n': '法国', 'v': '法国'},
                {'n': '英国', 'v': '英国'},
                {'n': '其它', 'v': '其它'},
            ]},
            {'key': 'year', 'name': '年份', 'value': [
                {'n': '全部', 'v': ''},
                {'n': '2026', 'v': '2026'},
                {'n': '2025', 'v': '2025'},
                {'n': '2024', 'v': '2024'},
                {'n': '2023', 'v': '2023'},
                {'n': '2022', 'v': '2022'},
                {'n': '2021', 'v': '2021'},
                {'n': '2020', 'v': '2020'},
                {'n': '2019', 'v': '2019'},
                {'n': '2018', 'v': '2018'},
                {'n': '2017', 'v': '2017'},
                {'n': '2016', 'v': '2016'},
                {'n': '2015', 'v': '2015'},
                {'n': '2014', 'v': '2014'},
                {'n': '2013', 'v': '2013'},
                {'n': '2012', 'v': '2012'},
                {'n': '2011', 'v': '2011'},
                {'n': '2010', 'v': '2010'},
            ]},
        ],
        '2': [
            {'key': 'class', 'name': '类型', 'value': [
                {'n': '全部', 'v': ''},
                {'n': '国产剧', 'v': '17'},
                {'n': '港台剧', 'v': '18'},
                {'n': '日韩剧', 'v': '20'},
                {'n': '欧美剧', 'v': '21'},
                {'n': '海外剧', 'v': '22'},
            ]},
            {'key': 'area', 'name': '地区', 'value': [
                {'n': '全部', 'v': ''},
                {'n': '大陆', 'v': '大陆'},
                {'n': '香港', 'v': '香港'},
                {'n': '台湾', 'v': '台湾'},
                {'n': '日本', 'v': '日本'},
                {'n': '韩国', 'v': '韩国'},
                {'n': '美国', 'v': '美国'},
                {'n': '其它', 'v': '其它'},
            ]},
            {'key': 'year', 'name': '年份', 'value': [
                {'n': '全部', 'v': ''},
                {'n': '2026', 'v': '2026'},
                {'n': '2025', 'v': '2025'},
                {'n': '2024', 'v': '2024'},
                {'n': '2023', 'v': '2023'},
                {'n': '2022', 'v': '2022'},
                {'n': '2021', 'v': '2021'},
                {'n': '2020', 'v': '2020'},
                {'n': '2019', 'v': '2019'},
                {'n': '2018', 'v': '2018'},
                {'n': '2017', 'v': '2017'},
                {'n': '2016', 'v': '2016'},
                {'n': '2015', 'v': '2015'},
                {'n': '2014', 'v': '2014'},
                {'n': '2013', 'v': '2013'},
                {'n': '2012', 'v': '2012'},
                {'n': '2011', 'v': '2011'},
                {'n': '2010', 'v': '2010'},
            ]},
        ],
        '3': [
            {'key': 'class', 'name': '类型', 'value': [
                {'n': '全部', 'v': ''},
                {'n': '大陆综艺', 'v': '23'},
                {'n': '日韩综艺', 'v': '24'},
                {'n': '欧美综艺', 'v': '25'},
                {'n': '港台综艺', 'v': '26'},
            ]},
            {'key': 'year', 'name': '年份', 'value': [
                {'n': '全部', 'v': ''},
                {'n': '2026', 'v': '2026'},
                {'n': '2025', 'v': '2025'},
                {'n': '2024', 'v': '2024'},
                {'n': '2023', 'v': '2023'},
                {'n': '2022', 'v': '2022'},
                {'n': '2021', 'v': '2021'},
                {'n': '2020', 'v': '2020'},
                {'n': '2019', 'v': '2019'},
                {'n': '2018', 'v': '2018'},
                {'n': '2017', 'v': '2017'},
                {'n': '2016', 'v': '2016'},
                {'n': '2015', 'v': '2015'},
                {'n': '2014', 'v': '2014'},
                {'n': '2013', 'v': '2013'},
                {'n': '2012', 'v': '2012'},
                {'n': '2011', 'v': '2011'},
                {'n': '2010', 'v': '2010'},
            ]},
        ],
        '4': [
            {'key': 'class', 'name': '类型', 'value': [
                {'n': '全部', 'v': ''},
                {'n': '国产动漫', 'v': '27'},
                {'n': '日韩动漫', 'v': '28'},
                {'n': '欧美动漫', 'v': '29'},
                {'n': '其他动漫', 'v': '30'},
            ]},
            {'key': 'year', 'name': '年份', 'value': [
                {'n': '全部', 'v': ''},
                {'n': '2026', 'v': '2026'},
                {'n': '2025', 'v': '2025'},
                {'n': '2024', 'v': '2024'},
                {'n': '2023', 'v': '2023'},
                {'n': '2022', 'v': '2022'},
                {'n': '2021', 'v': '2021'},
                {'n': '2020', 'v': '2020'},
                {'n': '2019', 'v': '2019'},
                {'n': '2018', 'v': '2018'},
                {'n': '2017', 'v': '2017'},
                {'n': '2016', 'v': '2016'},
                {'n': '2015', 'v': '2015'},
                {'n': '2014', 'v': '2014'},
                {'n': '2013', 'v': '2013'},
                {'n': '2012', 'v': '2012'},
                {'n': '2011', 'v': '2011'},
                {'n': '2010', 'v': '2010'},
            ]},
        ],
        '5': [
            {'key': 'year', 'name': '年份', 'value': [
                {'n': '全部', 'v': ''},
                {'n': '2026', 'v': '2026'},
                {'n': '2025', 'v': '2025'},
                {'n': '2024', 'v': '2024'},
                {'n': '2023', 'v': '2023'},
                {'n': '2022', 'v': '2022'},
                {'n': '2021', 'v': '2021'},
                {'n': '2020', 'v': '2020'},
                {'n': '2019', 'v': '2019'},
                {'n': '2018', 'v': '2018'},
                {'n': '2017', 'v': '2017'},
                {'n': '2016', 'v': '2016'},
                {'n': '2015', 'v': '2015'},
                {'n': '2014', 'v': '2014'},
                {'n': '2013', 'v': '2013'},
                {'n': '2012', 'v': '2012'},
                {'n': '2011', 'v': '2011'},
                {'n': '2010', 'v': '2010'},
            ]},
        ],
    }

    PER_PAGE = 36

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    # ============================================================
    # TVBox 标准接口
    # ============================================================

    def homeContent(self, filter):
        return {
            'class': self.classes,
            'filters': self.filters,
        }

    # 新规范8: 首页精选 (直接从首页HTML解析)
    def homeVideoContent(self):
        now = int(time.time())
        if self._home_cache and now - self._home_cache_time < 300:
            return {'list': self._home_cache[:72]}

        vods = []
        try:
            html = self._fetch_html(self.host + '/', timeout=10)
            if html:
                vods = self._parse_list_html(html)
                if vods:
                    vods = vods[:72]
                    self._home_cache = vods
                    self._home_cache_time = now
        except Exception:
            pass
        return {'list': vods}

    # 新规范15.4: 读取extend切换子分类
    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg or 1)

            # 解析extend参数
            ext = {}
            if extend:
                if isinstance(extend, dict):
                    ext = extend
                elif isinstance(extend, str):
                    try:
                        ext = json.loads(extend)
                    except Exception:
                        ext = {}

            class_val = ext.get('class', '')
            area_val = ext.get('area', '')
            year_val = ext.get('year', '')

            # 子分类: class值是子分类tid, 选择后替换父tid
            actual_tid = class_val if class_val else tid

            # MacCMS筛选URL (14字段, 13个dash):
            # /shxinsw/TID-AREA-------PAGE---YEAR.html
            # 位置: 0=tid, 1=area, 2-8=空, 9=page, 10-12=空, 13=year(1=全部)
            url = self.host + '/shxinsw/%s-%s-------%d---%s.html' % (
                actual_tid,
                quote(area_val) if area_val else '',
                pg,
                year_val if year_val else '1',
            )

            html = self._fetch_html(url, timeout=15)
            if not html:
                return {'page': pg, 'pagecount': 1, 'limit': self.PER_PAGE, 'total': 0, 'list': []}

            vods = self._parse_list_html(html)

            # 解析分页 - 从pager提取真实总页数
            pagecount = self._parse_pagecount(html, pg, len(vods))

            return {
                'page': pg,
                'pagecount': pagecount,
                'limit': self.PER_PAGE,
                'total': pagecount * self.PER_PAGE,
                'list': vods,
            }
        except Exception:
            return {'page': pg, 'pagecount': 1, 'limit': self.PER_PAGE, 'total': 0, 'list': []}

    def detailContent(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        vod_id = ids[0]

        # 缓存
        cache_key = str(vod_id)
        if cache_key in self._detail_cache:
            cached = self._detail_cache[cache_key]
            if cached and time.time() - cached.get('_ts', 0) < 600:
                return {'list': [cached]}

        vod = {
            'vod_id': vod_id,
            'vod_name': vod_id,
            'vod_pic': '',
            'type_name': '',
            'vod_year': '',
            'vod_area': '',
            'vod_remarks': '',
            'vod_actor': '',
            'vod_director': '',
            'vod_content': '',
            'vod_play_from': '',
            'vod_play_url': '',
        }
        try:
            detail_url = self.host + '/shxindt/%s.html' % vod_id
            html = self._fetch_html(detail_url, timeout=15)
            if not html:
                return {'list': [vod]}

            # 解析视频信息
            vod['vod_name'] = self._extract_title(html) or vod_id
            vod['vod_pic'] = self._extract_pic(html)
            vod['vod_year'] = self._extract_info(html, '年份')
            vod['vod_area'] = self._extract_info(html, '地区')
            vod['type_name'] = self._extract_info(html, '类型')
            vod['vod_remarks'] = self._extract_info(html, '状态')
            vod['vod_actor'] = self._extract_info(html, '主演')
            vod['vod_director'] = self._extract_info(html, '导演')
            vod['vod_content'] = self._extract_info(html, '简介')

            # 解析播放线路 (新规范13: 按source分组)
            play_from, play_url = self._extract_play_sources(html, vod_id)
            vod['vod_play_from'] = '$$$'.join(play_from) if play_from else '无数据'
            vod['vod_play_url'] = '$$$'.join(play_url) if play_url else '无数据$'

            vod['_ts'] = time.time()
            self._detail_cache[cache_key] = vod
        except Exception:
            pass
        return {'list': [vod]}

    def searchContent(self, key, quick, pg='1'):
        return self.searchContentPage(key, pg)

    def searchContentPage(self, key, pg):
        pg = int(pg or 1)
        vods = []
        try:
            # MacCMS搜索URL (pager格式): /shxinsc/keyword----------page---.html
            # 共14个字段, 13个dash (实测: /shxinsc/抓娃娃----------1---.html)
            url = self.host + '/shxinsc/%s----------%d---.html' % (quote(key), pg)
            html = self._fetch_html(url, timeout=15)
            if not html:
                return {'list': vods}
            vods = self._parse_list_html(html)
        except Exception:
            pass
        return {'list': vods}

    def playerContent(self, flag, id, vipFlags):
        play_url = ''
        parse_flag = 0
        try:
            # id 可以是 play page URL 或 ID-SID-NID
            play_id = str(id)
            if play_id.startswith('http'):
                play_url_path = play_id
            elif '/' in play_id:
                play_url_path = self.host + play_id
            else:
                play_url_path = self.host + '/shxinpy/%s.html' % play_id

            html = self._fetch_html(play_url_path, timeout=15)
            if html:
                player_data = self._extract_player_aaaa(html)
                if player_data:
                    video_url = player_data.get('url', '')
                    if video_url:
                        # m3u8/mp4直链: 直接播放
                        if '.m3u8' in video_url or '.mp4' in video_url:
                            play_url = video_url
                            parse_flag = 0
                        # http链接: 交给播放器嗅探
                        elif video_url.startswith('http'):
                            play_url = video_url
                            parse_flag = 1
                        else:
                            play_url = video_url
                            parse_flag = 0
        except Exception:
            play_url = str(id)

        result = {
            'parse': parse_flag,
            'playUrl': '',
            'url': play_url,
            'header': self.header,
        }
        if '.m3u8' in play_url:
            result['format'] = 'application/x-mpegURL'
            result['contentType'] = 'application/x-mpegURL'
        return result

    def localProxy(self, params):
        return [404, 'text/plain', '']

    # ============================================================
    # 内部方法 - 数据获取
    # ============================================================

    def _fetch_html(self, url, timeout=15):
        """获取HTML页面内容 (支持SSL降级, 防止挂起)"""
        # 第一路: self.fetch (TVBox内置HTTP客户端)
        try:
            try:
                rsp = self.fetch(url, headers=self.header, timeout=timeout)
            except TypeError:
                rsp = self.fetch(url, headers=self.header)
            if rsp:
                text = rsp.text if hasattr(rsp, 'text') else str(rsp)
                if text and text.strip():
                    return text
        except Exception:
            pass
        # 第二路: urllib (SSL降级 + 超时兜底)
        try:
            import ssl
            from urllib.request import Request, urlopen
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = Request(url, headers=self.header)
            with urlopen(req, timeout=timeout, context=ctx) as r:
                data = r.read()
                # 处理gzip
                if r.headers.get('Content-Encoding') == 'gzip':
                    import gzip
                    data = gzip.decompress(data)
                if isinstance(data, bytes):
                    return data.decode('utf-8', errors='ignore')
                return str(data)
        except Exception:
            pass
        # 第三路: HTTP降级 (HTTPS不通时尝试HTTP)
        if url.startswith('https://'):
            http_url = 'http://' + url[8:]
            try:
                from urllib.request import Request, urlopen
                req = Request(http_url, headers=self.header)
                with urlopen(req, timeout=timeout) as r:
                    data = r.read()
                    if r.headers.get('Content-Encoding') == 'gzip':
                        import gzip
                        data = gzip.decompress(data)
                    if isinstance(data, bytes):
                        return data.decode('utf-8', errors='ignore')
                    return str(data)
            except Exception:
                pass
        return ''

    # ============================================================
    # 内部方法 - HTML解析
    # ============================================================

    def _parse_list_html(self, html):
        """解析视频列表HTML (兼容 hl-list-item 和 hl-br-item 两种卡片)"""
        vods = []
        seen_ids = set()

        # 主列表卡片: li.hl-list-item > a.hl-item-thumb
        # 提取: href="/shxindt/ID.html" title="名称" data-original="图片"
        # 备注: <span class="hl-lc-1 remarks">备注</span>
        pattern = (
            r'<a[^>]+class="hl-item-thumb[^"]*"[^>]*'
            r'href="/shxindt/(\d+)\.html"[^>]*'
            r'title="([^"]*)"[^>]*'
            r'data-original="([^"]*)"[^>]*>'
            r'[\s\S]*?<span[^>]*class="[^"]*remarks[^"]*">([^<]*)</span>'
        )
        matches = re.findall(pattern, html)
        for vid, name, pic, note in matches:
            if vid in seen_ids:
                continue
            seen_ids.add(vid)
            vods.append({
                'vod_id': vid,
                'vod_name': name.strip(),
                'vod_pic': self._fix_pic(pic),
                'vod_remarks': note.strip(),
            })

        # 如果主列表没匹配到, 尝试通用模式: 任何带 shxindt/ID.html 的链接
        if not vods:
            pattern2 = (
                r'<a[^>]+href="/shxindt/(\d+)\.html"[^>]*title="([^"]*)"[^>]*'
                r'data-original="([^"]*)"'
            )
            matches2 = re.findall(pattern2, html)
            for vid, name, pic in matches2:
                if vid in seen_ids:
                    continue
                seen_ids.add(vid)
                vods.append({
                    'vod_id': vid,
                    'vod_name': name.strip(),
                    'vod_pic': self._fix_pic(pic),
                    'vod_remarks': '',
                })

        # 最后兜底: 只提取链接和标题
        if not vods:
            pattern3 = r'href="/shxindt/(\d+)\.html"[^>]*title="([^"]*)"'
            matches3 = re.findall(pattern3, html)
            for vid, name in matches3:
                if vid in seen_ids:
                    continue
                seen_ids.add(vid)
                vods.append({
                    'vod_id': vid,
                    'vod_name': name.strip(),
                    'vod_pic': '',
                    'vod_remarks': '',
                })

        return vods

    def _parse_pagecount(self, html, current_pg, item_count=0):
        """解析总页数
        从pager的 hl-page-total 区域提取 "当前页/总页数页"
        没数据时返回当前页让TVBox停止加载
        """
        # 没数据: 返回当前页, TVBox停止加载
        if item_count == 0:
            return current_pg

        # 有数据: 从pager提取真实总页数
        # pager HTML: <div class="hl-page-total">1&nbsp;/&nbsp;2317页</div>
        m = re.search(r'(\d+)\s*&nbsp;/&nbsp;\s*(\d+)\s*页', html)
        if m:
            total = int(m.group(2))
            if total > 0:
                return total

        # 找不到pager: 返回高值让TVBox自己探索
        return 9999

    def _extract_title(self, html):
        """提取标题"""
        # h1/h2 标题
        for tag in ['h1', 'h2']:
            m = re.search(r'<%s[^>]*>([^<]+)</%s>' % (tag, tag), html)
            if m:
                title = m.group(1).strip()
                if title and title != '影片信息':
                    return title
        # title标签
        m = re.search(r'<title>([^<]+)</title>', html)
        if m:
            title = m.group(1).strip()
            # 去掉后缀
            title = re.sub(r'\s*[-—|].*$', '', title)
            title = title.replace('《', '').replace('》', '')
            if title:
                return title
        return ''

    def _extract_pic(self, html):
        """提取封面图"""
        # 模式1: og:image (property在前)
        m = re.search(r'og:image["\']\s+content=["\']([^"\']+)', html)
        if m:
            return self._fix_pic(m.group(1))
        # 模式2: og:image (content在前)
        m = re.search(r'content=["\']([^"\']+)["\']\s+[^>]*og:image', html)
        if m:
            return self._fix_pic(m.group(1))
        # 模式3: link rel=image_src
        m = re.search(r'rel=["\']image_src["\'][^>]*href=["\']([^"\']+)', html)
        if m:
            return self._fix_pic(m.group(1))
        # 模式4: hl-dp-thumb with data-original
        m = re.search(r'class="hl-dp-thumb[^"]*"[^>]*data-original="([^"]+)"', html)
        if m:
            return self._fix_pic(m.group(1))
        # 模式5: 任何带vod图片URL的data-original (排除static)
        pics = re.findall(r'data-original="([^"]+)"', html)
        for pic in pics:
            if 'static' not in pic and ('vod' in pic or 'pic' in pic or 'upload' in pic):
                return self._fix_pic(pic)
        # 模式6: hl-lazy img with data-original
        m = re.search(r'class="hl-lazy[^"]*"[^>]*data-original="([^"]+)"', html)
        if m:
            return self._fix_pic(m.group(1))
        return ''

    def _extract_info(self, html, label):
        """提取影片信息字段 (片名/状态/主演/导演/年份/地区/类型/简介)
        真实HTML结构: <em>片名：</em>抓娃娃  或  <em>主演：</em><a>沈腾</a>/<a>马丽</a>/
        """
        def decode_entities(text):
            """解码HTML实体"""
            text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
            text = text.replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')
            text = text.replace('&#39;', "'").replace('&apos;', "'")
            return text

        # 模式1: <em>label：</em>value (值可能包含链接, 如主演/导演)
        pattern1 = r'<em[^>]*>\s*%s[：:]\s*</em>\s*([\s\S]*?)(?:<em|</li|</div|</ul|</p)' % label
        m = re.search(pattern1, html)
        if m:
            raw = m.group(1)
            links = re.findall(r'<a[^>]*>([^<]+)</a>', raw)
            if links:
                val = '/'.join(l.strip() for l in links if l.strip())
            else:
                val = re.sub(r'<[^>]+>', '', raw).strip()
            if val:
                val = decode_entities(val).strip().rstrip('/').strip()
                if val and val != '内详' and val != '未知':
                    return val
                return val

        # 模式2: <span>label：</span>value
        pattern2 = r'<span[^>]*>\s*%s[：:]\s*</span>\s*([\s\S]*?)(?:<span|</li|</div|</ul)' % label
        m = re.search(pattern2, html)
        if m:
            raw = m.group(1)
            links = re.findall(r'<a[^>]*>([^<]+)</a>', raw)
            if links:
                val = '/'.join(l.strip() for l in links if l.strip())
            else:
                val = re.sub(r'<[^>]+>', '', raw).strip()
            if val:
                val = decode_entities(val).strip().rstrip('/').strip()
                if val:
                    return val

        # 模式3: 纯文本 label：value
        pattern3 = r'%s[：:]\s*([^<\n]+)' % label
        m = re.search(pattern3, html)
        if m:
            val = decode_entities(m.group(1).strip())
            if val:
                return val

        return ''

    def _extract_play_sources(self, html, vod_id):
        """提取播放线路和剧集 (新规范13: 按source分组)"""
        play_from = []
        play_url = []

        # MacCMS播放列表: 找所有 /shxinpy/ID-SID-NID.html 链接
        # 格式: <a href="/shxinpy/50741-1-1.html">HD</a>
        pattern = r'href="/shxinpy/%s-(\d+)-(\d+)\.html"[^>]*>([^<]+)</a>' % vod_id
        matches = re.findall(pattern, html)

        if matches:
            # 按 SID 分组
            sources = {}
            source_order = []
            for sid, nid, ep_name in matches:
                if sid not in sources:
                    sources[sid] = []
                    source_order.append(sid)
                sources[sid].append((nid, ep_name.strip()))

            # 尝试提取线路名称 (从tab标签)
            source_names = self._extract_source_names(html)

            for sid in source_order:
                eps = sources[sid]
                # 排序按NID
                eps.sort(key=lambda x: int(x[0]))
                name = source_names.get(sid, '线路%s' % sid)
                ep_list = []
                for nid, ep_name in eps:
                    play_url_str = '/shxinpy/%s-%s-%s.html' % (vod_id, sid, nid)
                    ep_list.append('%s$%s' % (ep_name, play_url_str))
                play_from.append(name)
                play_url.append('#'.join(ep_list))

        return play_from, play_url

    def _extract_source_names(self, html):
        """提取播放线路名称 (从tab标签或"当前资源来源"文本)
        真实HTML: <a class="hl-tabs-trigger" href="javascript:void(0);">大屏观影</a>
        或: 当前资源来源大屏观影 - 在线播放,无需安装播放器
        """
        names = {}

        # 模式1: <a class="hl-tabs-trigger" data-tab="1">大屏观影</a>
        pattern1 = r'data-tab="(\d+)"[^>]*>([^<]+)</a>'
        matches1 = re.findall(pattern1, html)
        if matches1:
            for sid, name in matches1:
                names[sid] = name.strip()
            if names:
                return names

        # 模式2: <a class="hl-tabs-trigger..." href="javascript:void(0);">大屏观影</a>
        pattern2 = r'class="hl-tabs-trigger[^"]*"[^>]*>([^<]+)</a>'
        matches2 = re.findall(pattern2, html)
        if matches2:
            for i, name in enumerate(matches2, 1):
                names[str(i)] = name.strip()
            if names:
                return names

        # 模式3: 从 "当前资源来源XXX - 在线播放" 提取 (支持HTML标签)
        pattern3 = r'当前资源来源([\s\S]*?)在线播放'
        matches3 = re.findall(pattern3, html)
        if matches3:
            for raw in matches3:
                # 清理HTML标签
                clean = re.sub(r'<[^>]+>', '', raw)
                # 解码HTML实体
                clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&')
                clean = clean.replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')
                # 去掉 - 和多余空格
                clean = clean.replace('-', '').strip()
                # 去掉末尾的逗号和空格
                clean = clean.rstrip(',').strip()
                if clean and clean != '无需安装播放器' and '无需' not in clean:
                    names[str(len(names) + 1)] = clean
            if names:
                return names

        # 模式4: 找播放列表区域内的 <a href="javascript:void(0);">线路名</a>
        # 先定位"播放列表"标题
        play_idx = html.find('播放列表')
        if play_idx < 0:
            play_idx = html.find('播放')
        if play_idx >= 0:
            play_section = html[play_idx:play_idx + 5000]
            pattern4 = r'<a[^>]*href="javascript:void\(0\)"[^>]*>([^<]{2,20})</a>'
            matches4 = re.findall(pattern4, play_section)
            # 过滤掉非线路名称的链接
            for name in matches4:
                name = name.strip()
                if name and name not in ['倒序', '展开全部', '展开'] and len(name) < 20:
                    names[str(len(names) + 1)] = name
            if names:
                return names

        return names

    def _extract_player_aaaa(self, html):
        """从播放页提取 player_aaaa 变量 (支持嵌套JSON)"""
        try:
            # 定位 player_aaaa = {
            idx = html.find('player_aaaa')
            if idx < 0:
                return {}
            # 找到第一个 {
            brace_start = html.find('{', idx)
            if brace_start < 0:
                return {}
            # 用括号计数法提取完整JSON (处理嵌套对象)
            depth = 0
            end = brace_start
            for i in range(brace_start, len(html)):
                c = html[i]
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            json_str = html[brace_start:end]
            data = json.loads(json_str)
            return data
        except Exception:
            pass
        return {}

    def _fix_pic(self, pic_url):
        """修复图片URL"""
        if not pic_url:
            return ''
        # 补全协议
        if pic_url.startswith('//'):
            return 'https:' + pic_url
        if not pic_url.startswith('http'):
            return 'https://' + pic_url
        return pic_url
