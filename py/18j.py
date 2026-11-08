# -*- coding: utf-8 -*-
# 18J.TV py 源（按用户 18j.json 规则重写：自动域名 + 女优/标签/黑料/自定义词条）
# 发布页: https://91fby.cc/18j/ → 提取域名 → 主页url
import re
import json
import requests
import warnings
from urllib.parse import quote

try:
    warnings.filterwarnings('ignore')
    requests.packages.urllib3.disable_warnings()
except Exception:
    pass

from base.spider import Spider

UA = ('Mozilla/5.0 (Linux; Android 16; 2510DRK44C Build/BP2A.250605.031.A3) '
      'AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.192 Mobile Safari/537.36')

PUBLISH_PAGE = 'https://91fby.cc/18j/'

# 主分类（对应 cn/show/{id}）
MAIN_CATS = [
    ('国产', 'show/1'), ('日韩', 'show/2'), ('欧美', 'show/3'), ('伦理', 'show/4'),
    ('H漫', 'show/5'), ('另类', 'show/6'),
]

# 类型筛选（子分类，对应 show/{id}）
TYPE_FILTERS = {
    'show/1': [('', '全部'), ('12', '国产自拍'), ('13', '网爆吃瓜'), ('14', '国产探花'),
               ('15', '主播大秀'), ('16', '乱伦系列'), ('17', '偷拍偷窥'), ('18', '成人抖音'),
               ('19', '国产AV'), ('20', '福利姬')],
    'show/2': [('', '全部'), ('21', '日韩自拍'), ('22', '日本无码'), ('23', '中文字幕'), ('24', 'av解说')],
    'show/3': [('', '全部'), ('25', '欧美大片')],
    'show/4': [('', '全部'), ('26', '港台三级'), ('27', '日韩三级'), ('28', '欧美伦理')],
    'show/5': [('', '全部'), ('29', '3D成人动漫'), ('30', '成人动漫')],
    'show/6': [('', '全部'), ('32', '女同百合'), ('31', '男同系列'), ('33', '重口味'),
               ('34', '伪娘系列'), ('35', 'AI明星')],
}

# 地区（URL 编码）
AREAS = [
    ('', '全部'), ('%E5%A4%A7%E9%99%86', '大陆'), ('%E5%8F%B0%E6%B9%BE', '台湾'),
    ('%E9%A6%99%E6%B8%AF', '香港'), ('%E7%BE%8E%E5%9B%BD', '美国'),
    ('%E6%97%A5%E6%9C%AC', '日本'), ('%E8%B6%8A%E5%8D%97', '越南'),
]

# 排序（分类用）
SORTS = [('', '最近更新'), ('hits_day', '今日热播'), ('up_day', '今日点赞'), ('up', '好评榜')]

# 顺序（黑料用）
ORDERS = [('time', '最新'), ('hits_day', '今日'), ('hits_week', '本周'), ('hits_month', '本月')]

# 排列（女优用）
RANKS = [('time', '最新收录'), ('hits_day', '今日最火'), ('hits_week', '本周热门'), ('hits_month', '本月人气')]

# 选择（标签用）
CHOICES = [('time', '最新'), ('hits', '最热')]

# 自定义词条
KEYWORDS = ['春药', '人妻', '精油', '男同']


class Spider(Spider):
    def getName(self):
        return '18J自动挡'

    def init(self, extend=''):
        self.header = {'User-Agent': UA}
        # 先直接用已知可用域名（保证羊壳立即有内容），再后台尝试自动解析
        self.host = 'https://18rf.life'
        try:
            resolved = self._resolve_domain()
            if resolved:
                self.host = resolved
        except Exception:
            pass
        # 分类先设置（黑料 → 女优 → 标签，后两者是文件夹）
        self.classes = [{'type_id': 'c:' + cid, 'type_name': name}
                        for name, cid in MAIN_CATS]
        self.classes.append({'type_id': 'art', 'type_name': '黑料'})
        self.classes.append({'type_id': 'actor', 'type_name': '📌女优'})
        self.classes.append({'type_id': 'tag', 'type_name': '📌标签'})

    # ============ 域名自动挡 ============
    def _resolve_domain(self):
        """发布页提取域名 → 测活（分类页结构验证）→ 返回可用域名"""
        try:
            r = requests.get(PUBLISH_PAGE, headers=self.header, timeout=5, verify=False)
            r.encoding = 'utf-8'
            html = r.text
            domains = re.findall(r'https?://([a-z0-9]+\.(?:life|tv|vip))', html)
            domains += ['18j.tv']
            seen = set()
            for d in domains:
                if d in seen:
                    continue
                seen.add(d)
                url = 'https://' + d
                try:
                    # 用分类页验证（根路径无卡片）
                    r2 = requests.get(url + '/cn/show/1/page/1/', headers=self.header, timeout=3, verify=False)
                    if r2.status_code == 200 and 'class="box"' in r2.text:
                        return url
                except Exception:
                    continue
        except Exception:
            pass
        # 保底：尝试已知可用域名
        for d in ['18rf.life', '18rd.life', '18qh.life', '18j.tv']:
            try:
                r2 = requests.get(f'https://{d}/cn/show/1/page/1/', headers=self.header, timeout=3, verify=False)
                if r2.status_code == 200 and 'class="box"' in r2.text:
                    return 'https://' + d
            except Exception:
                continue
        return ''

    # ============ 请求 ============
    def _req(self, url, timeout=10):
        try:
            r = requests.get(url, headers=self.header, timeout=timeout, verify=False)
            r.encoding = 'utf-8'
            return r.text
        except Exception:
            return ''

    # ============ 首页 ============
    def homeContent(self, filter):
        classes = [{'type_id': 'c:' + cid, 'type_name': name}
                   for name, cid in MAIN_CATS]
        classes.append({'type_id': 'art', 'type_name': '黑料'})
        classes.append({'type_id': 'actor', 'type_name': '📌女优'})
        classes.append({'type_id': 'tag', 'type_name': '📌标签'})
        # filters：类型筛选（挂主分类）
        filters = {}
        for name, cid in MAIN_CATS:
            filters['c:' + cid] = [{
                'key': 'sub', 'name': '分类',
                'value': [{'v': v, 'n': n} for v, n in TYPE_FILTERS.get(cid, [('', '全部')])]}]
            filters['c:' + cid].append({
                'key': 'by', 'name': '排序',
                'value': [{'v': v, 'n': n} for v, n in SORTS]})
        # 女优：地区+排列
        filters['actor'] = [
            {'key': 'area', 'name': '地区',
             'value': [{'v': v, 'n': n} for v, n in AREAS]},
            {'key': 'rank', 'name': '排列',
             'value': [{'v': v, 'n': n} for v, n in RANKS]}]
        # 标签：最新/最热
        filters['tag'] = [{
            'key': 'choose', 'name': '选择',
            'value': [{'v': v, 'n': n} for v, n in CHOICES]}]
        # 黑料：顺序
        filters['art'] = [{
            'key': 'order', 'name': '顺序',
            'value': [{'v': v, 'n': n} for v, n in ORDERS]}]
        # 首页列表
        lst = []
        try:
            html = self._req(self.host + '/cn/show/1/page/1/')
            lst = self._parse_videos(html)
        except Exception:
            pass
        return {'class': classes, 'filters': filters, 'list': lst}

    def homeVideoContent(self):
        try:
            html = self._req(self.host + '/cn/show/1/page/1/')
            return {'list': self._parse_videos(html)}
        except Exception:
            return {}

    # ============ 列表解析 ============
    def _parse_videos(self, html):
        vods = []
        if not html:
            return vods
        blocks = re.findall(r'<li class="[^"]*">\s*<div class="box">[\s\S]*?</li>', html)
        for block in blocks:
            m = re.search(r'href="([^"]*)"\s+title="([^"]*)"', block)
            if not m:
                continue
            href, title = m.group(1), m.group(2).strip()
            vid = href.strip('/').split('/')[-1]
            pm = re.search(r'data-original="([^"]+)"', block) or re.search(r'<img[^>]+src="([^"]+)"', block)
            sm = re.search(r'<span>\s*([^<]*)\s*</span>', block)
            vods.append({
                'vod_id': 'v:' + vid,
                'vod_name': title,
                'vod_pic': pm.group(1).strip() if pm else '',
                'vod_remarks': sm.group(1).strip() if sm else '',
            })
            if len(vods) >= 30:
                break
        return vods

    # ============ 分类 ============
    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg) if str(pg).isdigit() else 1
            # ========== 二级：点击 folder（女优/标签）→ 内容列表（missav 写法） ==========
            if isinstance(tid, str) and (tid.startswith('/actor/detail/') or tid.startswith('/s/tag/')):
                href = tid  # /actor/detail/xxx/ 或 /s/tag/xxx/
                html = self._req(self.host + href)
                if '/s/tag/' in href:
                    # 标签 → 该标签视频列表
                    vods = self._parse_videos(html)
                    return {'list': vods, 'page': page, 'pagecount': 100,
                            'limit': 30, 'total': 9999}
                # 女优 → 该演员所有作品（先搜索）
                # ① 取演员名字
                name = ''
                if html:
                    hm = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
                    if hm:
                        name = hm.group(1).split('(')[0].split('（')[0].strip()
                # ② 用名字搜索该演员所有作品
                if name:
                    shtml = self._req(self.host + f'/cn/s/page/{page}/wd/{quote(name)}/')
                    vods = self._parse_videos(shtml)
                    real = [v for v in vods if name in v['vod_name']]
                    if real:
                        return {'list': real, 'page': page, 'pagecount': 100,
                                'limit': 30, 'total': 9999}
                # ③ 搜索失败则解析详情页作品
                works = self._parse_videos(html)
                seen = set()
                uniq = []
                for w in works:
                    if w['vod_id'] in seen:
                        continue
                    seen.add(w['vod_id'])
                    uniq.append(w)
                return {'list': uniq, 'page': page, 'pagecount': 100,
                        'limit': 30, 'total': 9999}
            if tid == 'actor':
                return self._actor_list(page, filter, extend)
            if tid == 'tag':
                return self._tag_list(page, filter, extend)
            if tid == 'art':
                return self._art_list(page, filter, extend)
            if tid.startswith('c:'):
                cid = tid.split(':', 1)[1]
            else:
                cid = tid
            # 筛选合并
            by = ''
            sub = ''
            for d in [filter, extend]:
                if isinstance(d, dict):
                    if d.get('by'):
                        by = str(d['by'])
                    if d.get('sub'):
                        sub = str(d['sub'])
            if sub:
                cid = 'show/' + sub
            url = f"{self.host}/cn/{cid}/"
            if by:
                url = f"{self.host}/cn/{cid}/by/{by}/"
            url = f"{url}page/{page}/"
            html = self._req(url)
            vods = self._parse_videos(html)
            return {'list': vods, 'page': page, 'pagecount': 100,
                    'limit': 30, 'total': 9999}
        except Exception:
            return {'list': []}

    # ============ 📌女优 ============
    def _actor_list(self, page, filter, extend):
        try:
            area = ''
            rank = 'time'
            for d in [filter, extend]:
                if isinstance(d, dict):
                    if d.get('area'):
                        area = str(d['area'])
                    if d.get('rank'):
                        rank = str(d['rank'])
            if area:
                url = f"{self.host}/cn/modol/area/{area}/by/{rank}/id/8/page/{page}/"
            else:
                url = f"{self.host}/cn/modol/by/{rank}/id/8/page/{page}/"
            html = self._req(url)
            actors = []
            pattern = re.compile(
                r'<a class="box" href="/actor/detail/([^"/]+)/"[\s\S]*?'
                r'data-original="([^"]+)"[\s\S]*?'
                r'class="title">([^<]+)</div>')
            for m in pattern.finditer(html):
                slug, pic, name = m.groups()
                actors.append({
                    'vod_id': '/actor/detail/' + slug + '/',  # missav 写法：href 直接作 id
                    'vod_name': name.strip(),
                    'vod_pic': pic.strip(),
                    'vod_remarks': '女优',
                    'vod_tag': 'folder',  # 标记为文件夹，壳点击后调 categoryContent
                })
                if len(actors) >= 30:
                    break
            return {'list': actors, 'page': page, 'pagecount': 100,
                    'limit': 30, 'total': 9999}
        except Exception:
            return {'list': []}

    # ============ 📌标签 ============
    def _tag_list(self, page, filter, extend):
        try:
            choose = 'time'
            for d in [filter, extend]:
                if isinstance(d, dict) and d.get('choose'):
                    choose = str(d['choose'])
            url = f"{self.host}/cn/label/tag/by/{choose}/page/{page}/"
            html = self._req(url)
            tags = []
            # 标签: <a href="/s/tag/{url编码}/" class="text-nord13">标签名</a>
            pattern = re.compile(r'<a href="(/s/tag/[^"/]+/)"[^>]*>([^<]{1,15})</a>')
            for m in pattern.finditer(html):
                href, name = m.groups()
                tags.append({
                    'vod_id': href,  # missav 写法：href 直接作 id，点击标签 → 该标签视频列表
                    'vod_name': name.strip(),
                    'vod_pic': '',
                    'vod_remarks': '标签',
                    'vod_tag': 'folder',
                })
                if len(tags) >= 30:
                    break
            return {'list': tags, 'page': page, 'pagecount': 100,
                    'limit': 30, 'total': 9999}
        except Exception:
            return {'list': []}

    # ============ 黑料（图文） ============
    def _art_list(self, page, filter, extend):
        try:
            order = 'time'
            for d in [filter, extend]:
                if isinstance(d, dict) and d.get('order'):
                    order = str(d['order'])
            url = f"{self.host}/cn/art/by/{order}/page/{page}/"
            html = self._req(url)
            arts = []
            # 文章卡片: <li><a href="/artdetail-209/"><article...>
            # <div style="background-image: url('...');">
            # <div class="post-item-title"><h2>标题</h2>
            blocks = re.findall(r'<li>\s*<a href="(/artdetail-\d+/)"[\s\S]*?</li>', html)
            # 分块提取
            pattern = re.compile(
                r'<a href="(/artdetail-\d+/)"[\s\S]*?'
                r'background-image: url\(&quot;([^&]+)&quot;\)[\s\S]*?'
                r'post-item-title[\s\S]*?<h2[^>]*>([^<]+)</h2>')
            for m in pattern.finditer(html):
                href, pic, title = m.groups()
                arts.append({
                    'vod_id': 'art:' + re.search(r'\d+', href).group(),
                    'vod_name': title.strip(),
                    'vod_pic': pic.strip(),
                    'vod_remarks': '黑料',
                })
                if len(arts) >= 30:
                    break
            return {'list': arts, 'page': page, 'pagecount': 100,
                    'limit': 30, 'total': 9999}
        except Exception:
            return {'list': []}

    # ============ 自定义词条 ============
    def _keyword_list(self, kw, page):
        try:
            url = f"{self.host}/cn/s/page/{page}/wd/{quote(kw)}/"
            html = self._req(url)
            vods = self._parse_videos(html)
            return {'list': vods, 'page': page, 'pagecount': 100,
                    'limit': 30, 'total': 9999}
        except Exception:
            return {'list': []}

    # ============ 详情 ============
    def detailContent(self, ids):
        try:
            if isinstance(ids, list):
                ids = ids[0]
            vid = str(ids)
            if vid.startswith('/actor/detail/') or vid.startswith('/s/tag/'):
                # 兼容：folder 走 categoryContent，这里也处理（防壳调 detailContent）
                try:
                    return self.categoryContent(vid, 1, '', {})
                except Exception:
                    return {'list': []}
            if vid.startswith('tag:'):
                # 兼容旧格式：点击标签 → 该标签的视频列表
                tname = vid.split(':', 1)[1]
                html = self._req(self.host + f'/s/tag/{quote(tname)}/')
                vods = self._parse_videos(html)
                return {'list': vods}
            if vid.startswith('art:'):
                # 黑料文章 → 文章内容 + 视频播放
                aid = vid.split(':', 1)[1]
                html = self._req(self.host + f'/artdetail-{aid}/')
                if not html:
                    return {'list': []}
                tm = re.search(r'<h1[^>]*>([^<]+)</h1>', html) or \
                     re.search(r'<title>([^<]+)</title>', html)
                title = tm.group(1).strip() if tm else f'文章{aid}'
                pm = re.search(r'background-image: url\(&quot;([^&]+)&quot;\)', html) or \
                     re.search(r'<img[^>]+src="([^"]+)"', html)
                pic = pm.group(1) if pm else ''
                sm = re.search(r"const source = '([^']+\.m3u8[^']*)'", html)
                play_url = sm.group(1) if sm else ''
                if not play_url:
                    return {'list': [{'vod_id': 'art:' + aid, 'vod_name': title,
                                      'vod_pic': pic, 'vod_play_from': '',
                                      'vod_play_url': ''}]}
                return {'list': [{
                    'vod_id': 'art:' + aid, 'vod_name': title, 'vod_pic': pic,
                    'vod_play_from': '18J',
                    'vod_play_url': '正片$' + play_url,
                }]}
            if vid.startswith('v:'):
                vid = vid.split(':', 1)[1]
            else:
                vid = vid.split(':')[-1]
            html = self._req(self.host + f'/v/{vid}/')
            if not html:
                return {'list': []}
            tm = re.search(r'<h1[^>]*>([^<]+)</h1>', html) or \
                 re.search(r'<title>([^<]+)</title>', html)
            title = tm.group(1).strip() if tm else f'视频{vid}'
            pm = re.search(r'<img[^>]+src="([^"]+)"[^>]*class="lazy"', html) or \
                 re.search(r'<video[^>]+poster="([^"]+)"', html) or \
                 re.search(r'data-original="([^"]+)"', html)
            pic = pm.group(1) if pm else ''
            sm = re.search(r"const source = '([^']+\.m3u8[^']*)'", html)
            if not sm:
                sm = re.search(r"source\s*=\s*'([^']+\.m3u8[^']*)'", html)
            play_url = sm.group(1) if sm else ''
            if not play_url:
                return {'list': [{'vod_id': vid, 'vod_name': title,
                                  'vod_pic': pic, 'vod_play_from': '',
                                  'vod_play_url': ''}]}
            return {'list': [{
                'vod_id': vid, 'vod_name': title, 'vod_pic': pic,
                'vod_play_from': '18J',
                'vod_play_url': '正片$' + play_url,
            }]}
        except Exception:
            return {'list': []}

    # ============ 女优详情（点击先搜索该演员所有内容） ============
    def _actor_detail(self, slug):
        try:
            # ① 先取演员名字（从详情页 h1）
            name = ''
            html = self._req(f"{self.host}/actor/detail/{slug}/")
            if html:
                hm = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
                if hm:
                    name = hm.group(1).split('(')[0].split('（')[0].strip()
            # ② 用名字搜索该演员所有作品（搜索结果必须含该名字，防热门填充）
            if name:
                shtml = self._req(self.host + f'/cn/s/page/1/wd/{quote(name)}/')
                vods = self._parse_videos(shtml)
                # 过滤：只保留标题含演员名字的结果
                real = [v for v in vods if name in v['vod_name']]
                if real:
                    return {'list': real}
            # ③ 搜索失败则解析详情页作品
            works = self._parse_videos(html)
            seen = set()
            uniq = []
            for w in works:
                if w['vod_id'] in seen:
                    continue
                seen.add(w['vod_id'])
                uniq.append(w)
            return {'list': uniq}
        except Exception:
            return {'list': []}

    # ============ 搜索 ============
    def searchContent(self, key, quick, pg='1'):
        try:
            page = int(pg) if str(pg).isdigit() else 1
            html = self._req(self.host + f'/cn/s/page/{page}/wd/{quote(key)}/')
            vods = self._parse_videos(html)
            return {'list': vods, 'page': page}
        except Exception:
            return {'list': []}

    # ============ 播放 ============
    def playerContent(self, flag, id, vipFlags):
        url = str(id or '').strip()
        if url.startswith('v:'):
            try:
                vid = url.split(':', 1)[1]
                html = self._req(self.host + f'/v/{vid}/')
                sm = re.search(r"const source = '([^']+\.m3u8[^']*)'", html)
                if not sm:
                    sm = re.search(r"source\s*=\s*'([^']+\.m3u8[^']*)'", html)
                if sm:
                    url = sm.group(1)
            except Exception:
                pass
        if url.startswith('//'):
            url = 'https:' + url
        return {'parse': 0, 'playUrl': '', 'url': url, 'header': self.header}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass
