# coding=utf-8
"""
目标站: 全能短剧 (www.semtong.com)
SeaCMS (海洋CMS) 架构，动态分类、精准播放解析
"""
import re
import sys
import json
import base64
import urllib.parse
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        self.site_url = "https://www.semtong.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        self.categories = [
            {"type_id": "1", "type_name": "重生"},
            {"type_id": "2", "type_name": "穿越"},
            {"type_id": "3", "type_name": "爽剧"},
            {"type_id": "4", "type_name": "言情"},
            {"type_id": "5", "type_name": "都市"},
            {"type_id": "6", "type_name": "古装"},
            {"type_id": "7", "type_name": "悬疑"},
            {"type_id": "8", "type_name": "剧情"}
        ]
        # 播放结果缓存
        self._play_cache = {}

    # ---------------- 通用工具 ----------------
    def _is_video(self, url):
        if not url:
            return False
        u = url.lower().split('?')[0].split('#')[0]
        return u.endswith(('.m3u8', '.mp4', '.flv', '.ts'))

    def _decode_url(self, url, encrypt):
        if not url:
            return ""
        try:
            enc = int(encrypt) if encrypt else 0
            if enc == 1:
                return urllib.parse.unquote(url)
            if enc == 2:
                return urllib.parse.unquote(
                    base64.b64decode(url).decode('utf-8', 'ignore')
                )
        except Exception:
            pass
        return url

    def _parse_player_json(self, html):
        """状态机截取 player_aaaa / player_data JSON"""
        m = re.search(r'(?:var\s+)?player_(?:aaaa|data)\s*=\s*', html)
        if not m:
            return None
        start = html.find('{', m.end())
        if start < 0:
            return None
        depth = 0
        in_str = False
        quote_char = ''
        esc = False
        for i in range(start, len(html)):
            c = html[i]
            if in_str:
                if esc:
                    esc = False
                elif c == '\\':
                    esc = True
                elif c == quote_char:
                    in_str = False
                continue
            if c in ('"', "'"):
                in_str = True
                quote_char = c
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    raw = html[start:i + 1]
                    try:
                        return json.loads(raw)
                    except Exception:
                        try:
                            return json.loads(re.sub(r',\s*([}\]])', r'\1', raw))
                        except Exception:
                            return None
        return None

    def _resolve_url(self, url, header, depth=1):
        """解析 iframe / 播放页，返回直链；限制深度避免死循环"""
        if depth <= 0 or not url:
            return ""
        try:
            r = self.fetch(url, headers=header, timeout=5)
        except Exception:
            return ""
        if not r or not r.text:
            return ""
        h = r.text

        # ① player_aaaa JSON
        d = self._parse_player_json(h)
        if d and d.get('url'):
            u = self._decode_url(d['url'], d.get('encrypt', 0))
            if u.startswith('//'):
                u = 'https:' + u
            if self._is_video(u):
                return u

        # ② var now = "直链"
        m = re.search(r'var\s+now\s*=\s*"([^"]+)"', h)
        if m and self._is_video(m.group(1)):
            return m.group(1)

        # ③ 嵌套 iframe（深入一层）
        m = re.search(r'<iframe[^>]+src="([^"]+)"', h)
        if m:
            nested = m.group(1)
            if not nested.startswith('http'):
                nested = (self.site_url + nested if nested.startswith('/')
                          else self.site_url + '/' + nested)
            if nested != url:
                return self._resolve_url(nested, header, depth - 1)

        # ④ 硬搜
        m = re.search(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4|flv)[^\s"\'<>]*)', h)
        if m:
            return m.group(1)
        return ""

    # ---------------- 列表解析 ----------------
    def _parse_video_list(self, soup, max_count=0):
        video_list = []
        seen = set()
        items = soup.select('li.fed-list-item') or soup.select('.fed-list-info li')

        if not items:
            items = soup.select('.fed-list-pics')
            for link in items:
                href = link.get('href', '')
                m = re.search(r'/duanju/(\d+)\.html', href)
                if not m:
                    continue
                vid = m.group(1)
                if vid in seen:
                    continue
                seen.add(vid)
                video_list.append({
                    "vod_id": vid,
                    "vod_name": link.get('title', ''),
                    "vod_pic": link.get('data-original', ''),
                    "vod_remarks": ''
                })
            return video_list

        for item in items:
            link = item.select_one('a.fed-list-pics') or item.select_one('a[href*="/duanju/"]')
            if not link:
                continue
            href = link.get('href', '')
            m = re.search(r'/duanju/(\d+)\.html', href)
            if not m:
                continue
            vid = m.group(1)
            if vid in seen:
                continue

            title = link.get('title', '')
            if not title:
                t = item.select_one('.fed-list-title a') or item.select_one('a[title]')
                if t:
                    title = t.get('title', '') or t.get_text(strip=True)
            if not title:
                continue

            pic = link.get('data-original', '')
            if not pic:
                img = link.select_one('img')
                if img:
                    pic = img.get('data-original', '') or img.get('src', '')

            remark = ''
            r = link.select_one('.fed-list-remarks')
            if r:
                remark = r.get_text(strip=True)

            seen.add(vid)
            video_list.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark
            })
            if max_count > 0 and len(video_list) >= max_count:
                break
        return video_list

    # ---------------- 首页 ----------------
    def homeContent(self, filter):
        url = self.site_url + "/"
        resp = self.fetch(url, headers=self.headers, timeout=8)
        video_list = []
        if resp:
            soup = BeautifulSoup(resp.text, 'html.parser')
            video_list = self._parse_video_list(soup, max_count=36)
        return {"class": self.categories, "list": video_list, "filters": {}}

    def homeVideoContent(self):
        return self.homeContent(False)

    # ---------------- 分类 ----------------
    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        if page <= 1:
            url = f"{self.site_url}/quanneng/{tid}.html"
        else:
            url = f"{self.site_url}/quanneng/{tid}_{page}.html"
        resp = self.fetch(url, headers=self.headers, timeout=8)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1, "limit": 30, "total": 0}

        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = self._parse_video_list(soup)

        pagecount = page
        for a in (soup.select('.fed-page-info a') or soup.select('.fed-page a')):
            text = a.get_text(strip=True)
            if text.isdigit():
                pagecount = max(pagecount, int(text))

        total = 0
        tm = re.search(r'共\s*(\d+)\s*个影片', soup.get_text())
        if tm:
            total = int(tm.group(1))
            pagecount = max(pagecount, (total + 29) // 30)

        return {
            "list": video_list,
            "page": page,
            "pagecount": pagecount,
            "limit": 30,
            "total": total if total else len(video_list) * pagecount
        }

    # ---------------- 详情 ----------------
    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = ids[0]
        url = f"{self.site_url}/duanju/{vod_id}.html"
        resp = self.fetch(url, headers=self.headers, timeout=8)
        if not resp:
            return {"list": []}

        soup = BeautifulSoup(resp.text, 'html.parser')

        vod_name = vod_id
        title_elem = (soup.select_one('.fed-deta-content h1 a')
                      or soup.select_one('h1 a')
                      or soup.select_one('h1'))
        if title_elem:
            vod_name = title_elem.get('title', '') or title_elem.get_text(strip=True)
        if vod_name == vod_id:
            og = soup.select_one('meta[property="og:title"]')
            if og:
                vod_name = og.get('content', vod_id)

        vod_pic = ''
        og = soup.select_one('meta[property="og:image"]')
        if og:
            vod_pic = og.get('content', '')
        if not vod_pic:
            img = soup.select_one('.fed-deta-images img') or soup.select_one('.fed-list-pics img')
            if img:
                vod_pic = img.get('data-original', '') or img.get('src', '')

        vod_content = ''
        d = soup.select_one('.fed-deta-content .fed-part-esan') or soup.select_one('.fed-part-esan')
        if d:
            vod_content = d.get_text(' ', strip=True)
        if not vod_content:
            og = soup.select_one('meta[property="og:description"]')
            if og:
                vod_content = og.get('content', '')

        vod_actor = vod_director = vod_area = vod_year = ''

        for li in (soup.select('.fed-deta-content li') or soup.select('dl.fed-deta-info dd li')):
            text = li.get_text(strip=True)
            if '主演' in text:
                vod_actor = text.split('：', 1)[-1].strip() if '：' in text else text.replace('主演', '').strip()
            elif '导演' in text:
                vod_director = text.split('：', 1)[-1].strip() if '：' in text else text.replace('导演', '').strip()
            elif '地区' in text:
                vod_area = text.split('：', 1)[-1].strip() if '：' in text else text.replace('地区', '').strip()
            elif '年份' in text:
                vod_year = text.split('：', 1)[-1].strip() if '：' in text else text.replace('年份', '').strip()

        play_from_list = []
        play_url_list = []

        # ① tab 结构
        tab_anchors = soup.select('.fed-tabs a')
        tab_names = {}
        for a in tab_anchors:
            href = a.get('href', '')
            name = a.get_text(strip=True)
            if name and name != '↑↓ 排序' and '#playlist' in href:
                tab_names[href.split('#')[-1]] = name

        if tab_names:
            for anchor, line_name in tab_names.items():
                block = soup.select_one(f'#{anchor}') or soup.select_one(f'[id="{anchor}"]')
                if not block:
                    continue
                episodes = []
                for a in block.select('a'):
                    href = a.get('href', '')
                    if not href or 'javascript:' in href or href.startswith('#'):
                        continue
                    ep_name = a.get_text(strip=True)
                    if not ep_name:
                        continue
                    if not href.startswith('http'):
                        href = self.site_url + href if href.startswith('/') else self.site_url + '/' + href
                    episodes.append(f"{ep_name}${href}")
                if episodes:
                    play_from_list.append(line_name)
                    play_url_list.append('#'.join(episodes))

        # ② 兜底：直接用 /play/ 链接
        if not play_url_list:
            episodes = []
            seen = set()
            for a in soup.select('a[href*="/play/"]'):
                href = a.get('href', '')
                ep_name = a.get_text(strip=True)
                if not href or not ep_name or href in seen:
                    continue
                seen.add(href)
                if not href.startswith('http'):
                    href = self.site_url + href if href.startswith('/') else self.site_url + '/' + href
                episodes.append(f"{ep_name}${href}")
            if episodes:
                play_from_list.append('默认线路')
                play_url_list.append('#'.join(episodes))

        vod_play_from = '$$$'.join(play_from_list) if play_from_list else '默认源'
        vod_play_url = '$$$'.join(play_url_list) if play_url_list else f"播放${vod_id}"

        return {"list": [{
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_actor": vod_actor,
            "vod_director": vod_director,
            "vod_area": vod_area,
            "vod_year": vod_year,
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url
        }]}

    # ---------------- 搜索 ----------------
    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        encoded_key = urllib.parse.quote(key)
        url = f"{self.site_url}/search.php?searchword={encoded_key}"
        if page > 1:
            url += f"&page={page}"

        resp = self.fetch(url, headers=self.headers, timeout=8)
        if not resp or '页面加载中' in resp.text:
            try:
                resp = self.fetch(url, headers={
                    **self.headers,
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                }, data=f"searchword={encoded_key}&page={page}", timeout=8)
            except Exception:
                resp = None

        if not resp or '页面加载中' in (resp.text if resp else ''):
            return {"list": [], "page": page, "pagecount": 1}

        soup = BeautifulSoup(resp.text, 'html.parser')
        return {"list": self._parse_video_list(soup), "page": page, "pagecount": 1}

    # ---------------- 播放（核心修复） ----------------
    def playerContent(self, flag, id, vipFlags):
        # 构造播放页 URL
        if id.startswith('http'):
            play_url = id
        elif id.startswith('/'):
            play_url = self.site_url + id
        elif re.match(r'\d+-\d+-\d+', id):
            play_url = f"{self.site_url}/play/{id}.html"
        elif re.match(r'\d+', id):
            play_url = f"{self.site_url}/play/{id}-1-0.html"
        else:
            play_url = f"{self.site_url}/play/{id}.html"

        # 缓存命中
        cached = self._play_cache.get(play_url)
        if cached:
            return cached

        resp = self.fetch(play_url, headers=self.headers, timeout=8)
        if not resp or not resp.text:
            return {"parse": 1, "url": play_url, "header": self.headers}

        html = resp.text
        header_direct = {
            'User-Agent': self.headers['User-Agent'],
            'Referer': play_url,
            'Origin': self.site_url
        }

        # ① var now = "直链"
        m = re.search(r'var\s+now\s*=\s*"([^"]+)"', html)
        if m and m.group(1).startswith('http') and self._is_video(m.group(1)):
            result = {"parse": 0, "url": m.group(1), "header": header_direct}
            self._play_cache[play_url] = result
            return result

        # ② player_aaaa / player_data JSON
        data = self._parse_player_json(html)
        if data and data.get('url'):
            u = self._decode_url(data['url'], data.get('encrypt', 0))
            if u.startswith('//'):
                u = 'https:' + u
            # 直链
            if self._is_video(u):
                result = {"parse": 0, "url": u, "header": header_direct}
                self._play_cache[play_url] = result
                return result
            # 解析器地址 → 再解析一层
            if u.startswith('http'):
                sub = self._resolve_url(u, header_direct, depth=1)
                if sub:
                    result = {"parse": 0, "url": sub, "header": header_direct}
                    self._play_cache[play_url] = result
                    return result

        # ③ iframe（只深入一层）
        m = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if m:
            iu = m.group(1)
            if not iu.startswith('http'):
                iu = self.site_url + iu if iu.startswith('/') else self.site_url + '/' + iu
            sub = self._resolve_url(iu, header_direct, depth=1)
            if sub:
                result = {"parse": 0, "url": sub, "header": header_direct}
                self._play_cache[play_url] = result
                return result

        # ④ 页面硬搜 m3u8 / mp4
        m = re.search(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4|flv)[^\s"\'<>]*)', html)
        if m:
            result = {"parse": 0, "url": m.group(1), "header": header_direct}
            self._play_cache[play_url] = result
            return result

        # ⑤ 兜底：交给 TVBox 嗅探
        return {"parse": 1, "url": play_url, "header": self.headers}