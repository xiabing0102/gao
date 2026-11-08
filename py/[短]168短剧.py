# coding=utf-8
# !/usr/bin/python

"""

 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容

"""

from urllib.parse import unquote, quote
from base.spider import Spider
from bs4 import BeautifulSoup
import requests
import time
import json
import sys
import re

sys.path.append('..')

xurl = "https://www.xzyx168.com"

headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36',
    'Referer': 'https://www.xzyx168.com/',
    'Origin': 'https://www.xzyx168.com',
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

_session = requests.Session()
_session.headers.update(headerx)

play_header = {
    'User-Agent': headerx['User-Agent'],
    'Referer': 'https://www.xzyx168.com/',
    'Origin': 'https://www.xzyx168.com',
}

# 真实视频源域名白名单
VIDEO_HOST_WHITELIST = (
    'hhuus.com', 'ijycnd.com', 'jinyingimage.com',
    'hd.', 'play.', 'vip.', 'cdn.',
)

# 广告 / 登录 / 跳转页特征黑名单
AD_KEYWORDS = (
    'login', 'register', 'signin', 'signup',
    'jump', 'redirect', 'goto',
    '/ad/', '/ads/', '/adv/', 'advert',
    'popup', 'popunder',
    'kefu', 'weixin', 'wechat',
    '/vip/', 'pay.', 'buy.',
    'shierbdz', 'cdn555', 'dmskin', 'lunarcalendar',
    '/user/', '/member/', 'auth',
)

# ------------------------------------------------------------------
# 需要屏蔽的播放线路名（命中即丢弃）
# 说明：站点的"云播"线路来自 hd.ijycnd.com，经常夹带广告/慢速，
#       这里统一屏蔽，只保留"闪播"等主线路。
# ------------------------------------------------------------------
BLOCKED_SOURCE_NAMES = ('云播', '云线路', '备用', '广告', '福利', '登录')


def _is_blocked_source(name: str) -> bool:
    """线路名是否在黑名单里"""
    if not name:
        return True
    return any(k in name for k in BLOCKED_SOURCE_NAMES)


def _is_ad_url(u: str) -> bool:
    if not u:
        return True
    ul = u.lower()
    # 真实视频域名一律放行（优先级高于黑名单）
    if any(h in ul for h in VIDEO_HOST_WHITELIST):
        for k in AD_KEYWORDS:
            if k in ul:
                return True
        return False
    if ul.endswith('.m3u8') or '.m3u8?' in ul:
        return False
    return any(k in ul for k in AD_KEYWORDS)


def _unwrap_m3u8(u: str) -> str:
    """反复解包中间层 /m3u8/?url=xxx 或 ?url=xxx"""
    if not u:
        return ''
    for _ in range(5):
        if '/m3u8/?url=' in u:
            inner = u.split('/m3u8/?url=', 1)[1]
            inner = unquote(inner)
            if inner.startswith('http'):
                u = inner
                continue
        m = re.search(r'[?&]url=([^&\s]+)', u)
        if m:
            inner = unquote(m.group(1))
            if inner.startswith('http') and inner != u:
                u = inner
                continue
        break
    return u


class Spider(Spider):
    global xurl
    global headerx
    global play_header

    def getName(self):
        return "首页"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    # ============================================================
    # 通用工具
    # ============================================================
    def extract_middle_text(self, text, start_str, end_str, pl,
                            start_index1: str = '', end_index2: str = ''):
        if pl == 3:
            plx = []
            while True:
                start_index = text.find(start_str)
                if start_index == -1:
                    break
                end_index = text.find(end_str, start_index + len(start_str))
                if end_index == -1:
                    break
                middle_text = text[start_index + len(start_str):end_index]
                plx.append(middle_text)
                text = text.replace(start_str + middle_text + end_str, '')
            if len(plx) > 0:
                purl = ''
                for i in range(len(plx)):
                    matches = re.findall(start_index1, plx[i])
                    output = ""
                    for match in matches:
                        match3 = re.search(r'(?:^|[^0-9])(\d+)(?:[^0-9]|$)', match[1])
                        if match3:
                            number = match3.group(1)
                        else:
                            number = 0
                        if 'http' not in match[0]:
                            output += f"#{match[1]}${number}{xurl}{match[0]}"
                        else:
                            output += f"#{match[1]}${number}{match[0]}"
                    output = output[1:]
                    purl = purl + output + "$$$"
                purl = purl[:-3]
                return purl
            else:
                return ""
        else:
            start_index = text.find(start_str)
            if start_index == -1:
                return ""
            end_index = text.find(end_str, start_index + len(start_str))
            if end_index == -1:
                return ""

        if pl == 0:
            middle_text = text[start_index + len(start_str):end_index]
            return middle_text.replace("\\", "")

        if pl == 1:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                jg = ' '.join(matches)
                return jg

        if pl == 2:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                new_list = [f'{item}' for item in matches]
                jg = '$$$'.join(new_list)
                return jg

    def _parse_vod_list(self, doc):
        videos = []
        for vod in doc.find_all('a', class_='stui-vodlist__thumb'):
            href = vod.get('href')
            title = vod.get('title')
            if not href or not title:
                continue
            if _is_ad_url(href) or '广告' in title or '福利' in title:
                continue

            pic = vod.get('data-original') or vod.get('data-src') or ''
            if not pic:
                m = re.search(r'url\(["\']?([^)"\']+)', vod.get('style', ''))
                if m:
                    pic = m.group(1)
            remark = ''
            span = vod.find('span', class_='pic-text')
            if span:
                remark = span.get_text(strip=True)
            videos.append({
                "vod_id": href,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": '▶️' + remark
            })
        return videos

    # ============================================================
    # 首页分类
    # ============================================================
    def homeContent(self, filter):
        result = {"class": []}
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                detail = _session.get(url=xurl + "/xzyxvt/duanjun.html", timeout=8)
                detail.encoding = "utf-8"
                doc = BeautifulSoup(detail.text, "lxml")

                seen_ids = set()

                menu = doc.find('ul', class_='stui-header__menu')
                if menu:
                    for li in menu.find_all('li'):
                        a = li.find('a')
                        if not a or not a.get('href') or not a.get('title'):
                            continue
                        if "都市短剧" in a['title'] or a['href'] in seen_ids:
                            continue
                        if _is_ad_url(a['href']):
                            continue
                        seen_ids.add(a['href'])
                        result["class"].append({
                            "type_id": a['href'],
                            "type_name": "🌠" + a['title']
                        })

                for head in doc.find_all('div', class_='stui-pannel__head'):
                    a = head.find('a')
                    if not a or not a.get('href') or not a.get('title'):
                        continue
                    href = a['href']
                    if '/xzyxvs/' not in href:
                        continue
                    if href in seen_ids or _is_ad_url(href):
                        continue
                    seen_ids.add(href)
                    result["class"].append({
                        "type_id": href,
                        "type_name": "🎬" + a['title']
                    })

                return result
            except Exception:
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(0.5)
                else:
                    return result

    def homeVideoContent(self):
        try:
            detail = _session.get(url=xurl + "/xzyxvt/duanjun.html", timeout=8)
            detail.encoding = "utf-8"
            doc = BeautifulSoup(detail.text, "lxml")
            return {'list': self._parse_vod_list(doc)}
        except Exception:
            return {'list': []}

    # ============================================================
    # 分类列表
    # ============================================================
    def categoryContent(self, cid, pg, filter, ext):
        page = int(pg) if pg else 1

        if 'zmn' in cid:
            fenge = cid.split("zmn")
            url = f'{xurl}{fenge[0]}{str(page)}zmn.html'
        else:
            base = cid.replace('.html', '')
            url = f'{xurl}{cid}' if page == 1 else f'{xurl}{base}{page}.html'

        retries = 3
        for attempt in range(retries):
            try:
                detail = _session.get(url=url, timeout=8)
                detail.encoding = "utf-8"
                doc = BeautifulSoup(detail.text, "lxml")
                videos = self._parse_vod_list(doc)

                result = {'list': videos}
                result['page'] = pg
                result['pagecount'] = 9999
                result['limit'] = 90
                result['total'] = 999999
                return result
            except Exception:
                if attempt < retries - 1:
                    time.sleep(0.5)
                else:
                    return {'list': []}

    # ============================================================
    # 详情 + 线路采集（屏蔽云播线路）
    # ============================================================
    def detailContent(self, ids):
        did = ids[0]
        result = {}
        videos = []

        if 'http' not in did:
            did = xurl + did

        try:
            res = _session.get(url=did, timeout=8)
            res.encoding = "utf-8"
            res = res.text
            doc = BeautifulSoup(res, "lxml")

            content = director = actor = remarks = year = area = ''

            detail_box = doc.find('div', class_='stui-content__detail')
            if detail_box:
                for p in detail_box.find_all('p', class_='data'):
                    for span in p.find_all('span', class_='text-muted'):
                        label = span.get_text(strip=True).replace('：', '').replace(':', '')
                        value = ''
                        sib = span.next_sibling
                        while sib:
                            if hasattr(sib, 'name') and sib.name == 'span':
                                break
                            value += str(sib)
                            sib = sib.next_sibling
                        value = value.strip().strip('，,').strip()
                        if not value:
                            continue
                        if label == '类型':
                            remarks = value
                        elif label == '地区':
                            area = value
                        elif label == '年份':
                            year = value
                        elif label == '主演':
                            actor = value
                        elif label == '导演':
                            director = value

                desc = detail_box.find('p', class_='desc')
                if desc:
                    sp = desc.find('span')
                    if sp:
                        sp.extract()
                    content = desc.get_text(strip=True)

            play_sources = []
            play_urls = []

            head = None
            for h in doc.find_all('div', class_='stui-pannel__head'):
                if h.get_text() and '播放线路' in h.get_text():
                    head = h
                    break

            # 记录 nav_tabs 中每一条线路在 DOM 里的原始顺序（含被屏蔽的）
            # 因为 playlist1 / playlist2 是按原始顺序编号的，
            # 所以必须拿原始序号去匹配对应 pane，再按需跳过。
            nav_tabs = head.find('ul', class_='nav-tabs') if head else None
            if nav_tabs:
                idx = 0
                for li in nav_tabs.find_all('li'):
                    a = li.find('a')
                    if not a:
                        continue
                    name = a.get_text(strip=True)
                    idx += 1
                    if not name:
                        continue
                    # === 关键：屏蔽云播及其他黑名单线路 ===
                    if _is_blocked_source(name):
                        continue

                    pane = doc.find('div', id=f'playlist{idx}')
                    if not pane:
                        continue
                    eps = []
                    for sub_li in pane.find_all('li'):
                        sub_a = sub_li.find('a')
                        if not sub_a or not sub_a.get('href'):
                            continue
                        pid = sub_a['href']
                        if 'http' not in pid:
                            pid = xurl + pid
                        if _is_ad_url(pid):
                            continue
                        pname = sub_a.get_text(strip=True) or sub_a.get('title', '').strip()
                        eps.append(f"{pname}${pid}")
                    if eps:
                        play_sources.append(name)
                        play_urls.append('#'.join(eps))

            # 若 nav-tabs 不存在，退回直接抓第一个 playlist，但也过滤黑名单线路名
            if not play_sources:
                playlist = doc.find('ul', class_='stui-content__playlist')
                if playlist:
                    eps = []
                    for li in playlist.find_all('li'):
                        a = li.find('a')
                        if not a or not a.get('href'):
                            continue
                        pid = a['href']
                        if 'http' not in pid:
                            pid = xurl + pid
                        if _is_ad_url(pid):
                            continue
                        pname = a.get_text(strip=True) or a.get('title', '').strip()
                        eps.append(f"{pname}${pid}")
                    if eps:
                        play_sources.append('闪播')
                        play_urls.append('#'.join(eps))

            videos.append({
                "vod_id": did,
                "vod_director": director,
                "vod_actor": actor,
                "vod_remarks": remarks,
                "vod_year": year,
                "vod_area": area,
                "vod_content": content,
                "vod_play_from": '$$$'.join(play_sources),
                "vod_play_url": '$$$'.join(play_urls)
            })

            result['list'] = videos
            return result

        except Exception:
            result['list'] = []
            return result

    # ============================================================
    # 播放地址解析
    # ============================================================
    def _extract_player_url(self, html: str) -> str:
        url = ''

        # 模式 1：player_aaaa = {...}
        m = re.search(r'player_aaaa\s*=\s*(\{.*?\})\s*(?:;|</script>|\n)',
                      html, re.DOTALL)
        if not m:
            m = re.search(r'player_aaaa\s*=\s*(\{[^\n]+\})', html)
        if m:
            try:
                data = json.loads(m.group(1))
                url = data.get('url', '') or ''
                if not url:
                    url = data.get('url_next', '') or ''
            except Exception:
                m2 = re.search(r'"url"\s*:\s*"([^"]+)"', m.group(1))
                if m2:
                    url = m2.group(1)

        # 模式 2：MacPlayer.PlayUrl = "..."
        if not url:
            m = re.search(r'MacPlayer\.PlayUrl\s*=\s*["\']([^"\']+)["\']', html)
            if m:
                url = m.group(1)

        # 模式 3：},"url":"..."
        if not url:
            m = re.search(r'\},"url"\s*:\s*"([^"]+)"', html)
            if m:
                url = m.group(1)

        # 模式 4：通用 "url":"..."
        if not url:
            m = re.search(r'"url"\s*:\s*"([^"]+)"', html)
            if m:
                url = m.group(1)

        # 模式 5：兜底 m3u8
        if not url:
            m = re.search(r'(https?://[^"\'\s<>]+\.m3u8[^"\'\s<>]*)', html)
            if m:
                url = m.group(1)

        url = url.replace('\\/', '/').replace('\\', '')
        if url.startswith('//'):
            url = 'https:' + url
        return url

    def playerContent(self, flag, id, vipFlags):
        result = {
            "parse": 0,
            "playUrl": '',
            "url": '',
            "header": play_header
        }

        try:
            # === 关键 1：若 id 本身指向云播链接（云播 n2m1），直接拒绝 ===
            # 播放链接规律：/xzyxvp/{vid}n{sid}m{nid}.html
            # sid=2 即云播，直接返回空 URL
            m_sid = re.search(r'/xzyxvp/\d+n(\d+)m\d+\.html', id)
            if m_sid and m_sid.group(1) == '2':
                return result

            res = _session.get(url=id, timeout=8)
            res.encoding = "utf-8"
            html = res.text

            # === 关键 2：flag（线路名）若命中黑名单，也拒绝 ===
            if _is_blocked_source(flag):
                return result

            # 抽真实 m3u8
            url = self._extract_player_url(html)

            if not url:
                m = re.search(r'src=["\']/m3u8/\?url=([^"\']+)["\']', html)
                if m:
                    url = unquote(m.group(1))

            url = _unwrap_m3u8(url)

            if '/m3u8/' in url.lower() and '?url=' not in url.lower():
                url = ''

            if _is_ad_url(url):
                url = ''

            if url and not url.lower().startswith('http'):
                url = ''

            # === 关键 3：最终结果若指向云播源（ijycnd），也屏蔽 ===
            if url and 'ijycnd.com' in url.lower():
                url = ''

            result["url"] = url
            return result

        except Exception:
            return result

    # ============================================================
    # 搜索
    # ============================================================
    def searchContentPage(self, key, quick, pg):
        result = {}
        page = int(pg) if pg else 1
        url = f'{xurl}/xzyxvc/{key}-wdyswzqun{str(page)}num.html'

        videos = []
        try:
            detail = _session.get(url=url, timeout=8)
            detail.encoding = "utf-8"
            doc = BeautifulSoup(detail.text, "lxml")
            videos = self._parse_vod_list(doc)
        except Exception:
            pass

        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, '1')

    # ============================================================
    # 本地代理
    # ============================================================
    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        elif params['type'] == "media":
            return self.proxyMedia(params)
        elif params['type'] == "ts":
            return self.proxyTs(params)
        return None