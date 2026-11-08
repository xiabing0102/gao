# coding=utf-8
"""
目标站: 哈密瓜动漫 (hmgdm.com)
站点: https://hmgdm.com/
动漫站 - 分类为字符串标识 -
"""
import re
import sys
import json
import urllib.parse
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.site_url = "https://hmgdm.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        self.categories = self._fetch_categories()
        # 构建筛选选项（仅用于展示）
        self.filters = {
            "watched": [
                {"key": "sort", "name": "排序", "value": [
                    {"n": "最新更新", "v": "time"},
                    {"n": "最多播放", "v": "hits"}
                ]}
            ],
            "rhdm": [
                {"key": "sort", "name": "排序", "value": [
                    {"n": "最新更新", "v": "time"},
                    {"n": "最多播放", "v": "hits"}
                ]}
            ],
            "gcdm": [
                {"key": "sort", "name": "排序", "value": [
                    {"n": "最新更新", "v": "time"},
                    {"n": "最多播放", "v": "hits"}
                ]}
            ],
            "omdm": [
                {"key": "sort", "name": "排序", "value": [
                    {"n": "最新更新", "v": "time"},
                    {"n": "最多播放", "v": "hits"}
                ]}
            ],
            "dmdy": [
                {"key": "sort", "name": "排序", "value": [
                    {"n": "最新更新", "v": "time"},
                    {"n": "最多播放", "v": "hits"}
                ]}
            ],
            "dtmh": [
                {"key": "sort", "name": "排序", "value": [
                    {"n": "最新更新", "v": "time"},
                    {"n": "最多播放", "v": "hits"}
                ]}
            ]
        }

    def _fetch_categories(self):
        """从首页导航栏解析分类"""
        try:
            resp = self.fetch(self.site_url, headers=self.headers)
            if not resp:
                return self._default_categories()
            soup = BeautifulSoup(resp.text, 'html.parser')
            nav_links = soup.select('nav .type, .small-nav .type')
            categories = []
            seen = set()
            for a in nav_links:
                href = a.get('href', '')
                match = re.search(r'/(type|watched)(?:/([^/]+))?', href)
                if not match:
                    continue
                if match.group(1) == 'watched':
                    tid = 'watched'
                    name = a.get_text(strip=True)
                else:
                    tid = match.group(2) if match.group(2) else ''
                    name = a.get_text(strip=True)
                if not tid or tid in seen:
                    continue
                seen.add(tid)
                categories.append({"type_id": tid, "type_name": name})
            if categories:
                return categories
        except Exception as e:
            print(f"[哈密瓜动漫] 获取分类失败: {e}")
        return self._default_categories()

    def _default_categories(self):
        return [
            {"type_id": "watched", "type_name": "大家在看"},
            {"type_id": "rhdm", "type_name": "日本动漫"},
            {"type_id": "gcdm", "type_name": "国产动漫"},
            {"type_id": "omdm", "type_name": "欧美动漫"},
            {"type_id": "dmdy", "type_name": "动漫电影"},
            {"type_id": "dtmh", "type_name": "动态漫画"}
        ]

    def _fix_url(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if not url.startswith("http"):
            return urllib.parse.urljoin(self.site_url + "/", url)
        return url

    def _parse_video_list(self, html):
        """从HTML中解析视频列表"""
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        seen = set()
        items = soup.select('a.video')
        for item in items:
            href = item.get('href', '')
            vod_id = re.search(r'/details/(\d+)', href)
            if not vod_id:
                continue
            vid = vod_id.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            title_elem = item.select_one('.desc .title p')
            title = title_elem.get_text(strip=True) if title_elem else ''
            if not title:
                title = item.get('title', '')
            if not title:
                continue
            img_box = item.select_one('.img-box')
            pic = ''
            if img_box:
                pic = img_box.get('data', '') or img_box.get('style', '')
                if pic and not pic.startswith('http'):
                    bg_match = re.search(r'url\(([^)]+)\)', pic)
                    if bg_match:
                        pic = bg_match.group(1).strip('"').strip("'")
            if not pic:
                img = item.select_one('.img-box img')
                if img:
                    pic = img.get('src', '')
            remark = ''
            remark_elem = item.select_one('.desc .desc')
            if remark_elem:
                remark = remark_elem.get_text(strip=True)
            results.append({
                "vod_id": vid,
                "vod_name": title.strip(),
                "vod_pic": self._fix_url(pic),
                "vod_remarks": remark
            })
        return results

    def homeContent(self, filter):
        url = self.site_url + "/"
        resp = self.fetch(url, headers=self.headers)
        video_list = []
        if resp:
            video_list = self._parse_video_list(resp.text)
            video_list = video_list[:30]
        return {
            "class": self.categories,
            "list": video_list,
            "filters": self.filters
        }

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        if tid == 'watched':
            url = f"{self.site_url}/watched"
        else:
            url = f"{self.site_url}/type/{tid}"
        if page > 1:
            url += f"?page={page}"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}
        video_list = self._parse_video_list(resp.text)
        pagecount = page
        soup = BeautifulSoup(resp.text, 'html.parser')
        pagination = soup.select('.pagination a, .page a')
        if pagination:
            nums = []
            for a in pagination:
                text = a.get_text(strip=True)
                if text.isdigit():
                    nums.append(int(text))
            if nums:
                pagecount = max(nums)
        return {
            "list": video_list,
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": len(video_list) * pagecount
        }

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = ids[0]
        url = f"{self.site_url}/details/{vod_id}"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": []}

        soup = BeautifulSoup(resp.text, 'html.parser')
        title_elem = soup.select_one('.detail-title h1') or soup.select_one('h1')
        vod_name = title_elem.get_text(strip=True) if title_elem else vod_id
        vod_pic = ''
        img_elem = soup.select_one('.detail-pic img')
        if img_elem:
            vod_pic = img_elem.get('src', '')
            vod_pic = self._fix_url(vod_pic)
        vod_content = ''
        content_elem = soup.select_one('.detail-desc')
        if content_elem:
            vod_content = content_elem.get_text(' ', strip=True)
        vod_actor = ''
        vod_director = ''
        vod_year = ''

        play_from_list = []
        play_url_list = []

        # 解析播放列表数据（从 <script> 中提取 episodesData）
        script_text = ''
        for script in soup.select('script'):
            if script.string and 'episodesData' in script.string:
                script_text = script.string
                break

        if script_text:
            data_match = re.search(r'const\s+episodesData\s*=\s*({[^;]+})', script_text, re.DOTALL)
            if data_match:
                try:
                    data = json.loads(data_match.group(1))
                    for channel_name, episodes in data.items():
                        if not episodes:
                            continue
                        ep_list = []
                        for ep in episodes:
                            path = ep.get('path', '')
                            name = ep.get('name', f"第{len(ep_list)+1}集")
                            if path:
                                full_url = self._fix_url(path)
                                ep_list.append(f"{name}${full_url}")
                        if ep_list:
                            play_from_list.append(channel_name)
                            play_url_list.append('#'.join(ep_list))
                except Exception as e:
                    print(f"[哈密瓜动漫] 解析播放列表失败: {e}")

        # 如果没有解析到，尝试从页面中直接找 a[href^="/player/"]
        if not play_url_list:
            player_links = soup.select('a[href^="/player/"]')
            if player_links:
                episodes = []
                for a in player_links:
                    href = a.get('href', '')
                    name = a.get_text(strip=True) or f"第{len(episodes)+1}集"
                    if href:
                        full_url = self._fix_url(href)
                        episodes.append(f"{name}${full_url}")
                if episodes:
                    play_from_list.append('默认线路')
                    play_url_list.append('#'.join(episodes))

        vod_play_from = '$$$'.join(play_from_list) if play_from_list else '默认源'
        vod_play_url = '$$$'.join(play_url_list) if play_url_list else f"播放${vod_id}"

        result = [{
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_actor": vod_actor,
            "vod_director": vod_director,
            "vod_area": "",
            "vod_year": vod_year,
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url
        }]
        return {"list": result}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        encoded_key = urllib.parse.quote(key)
        url = f"{self.site_url}/search?kw={encoded_key}"
        if page > 1:
            url += f"&page={page}"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1}
        video_list = self._parse_video_list(resp.text)
        return {"list": video_list, "page": page, "pagecount": 1}

    # ================= 修复播放解析 =================
    def playerContent(self, flag, id, vipFlags):
        """
        直接访问播放页（如 /player/200114533/7），从页面源码中提取 initDplayer 的 m3u8 URL。
        """
        play_url = self._fix_url(id)

        # 如果已经是直链，直接返回
        if re.search(r'\.(m3u8|mp4|flv)(\?|$)', play_url, re.I):
            return {"parse": 0, "url": play_url, "header": self.headers}

        headers = dict(self.headers)
        headers['Referer'] = self.site_url
        resp = self.fetch(play_url, headers=headers)
        if not resp:
            return {"parse": 1, "url": play_url, "header": headers}

        html = resp.text

        # 1. 提取 initDplayer 调用中的第一个参数（m3u8 URL）
        # 格式: initDplayer("https://hd.ijycnd.com/play/axk2Z9ze/index.m3u8", ...)
        match = re.search(r'initDplayer\s*\(\s*["\']([^"\']+\.m3u8[^"\']*)["\']', html, re.IGNORECASE)
        if match:
            m3u8_url = match.group(1)
            return {"parse": 0, "url": m3u8_url, "header": headers}

        # 2. 尝试提取 DPlayer 视频源（备用）
        dp = re.search(r'DPlayer\s*\(\s*({[^}]+})\)', html, re.DOTALL)
        if dp:
            try:
                data = json.loads(dp.group(1))
                video = data.get('video', {})
                if video.get('url'):
                    return {"parse": 0, "url": video['url'], "header": headers}
            except:
                pass

        # 3. 直接匹配 m3u8 链接
        m3u8 = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
        if m3u8:
            return {"parse": 0, "url": m3u8.group(1), "header": headers}

        # 4. 查找 iframe
        iframe = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if iframe:
            iframe_url = self._fix_url(iframe.group(1))
            if iframe_url != play_url:
                return self.playerContent(flag, iframe_url, vipFlags)

        # 5. 兜底：交给客户端解析
        return {"parse": 1, "url": play_url, "header": headers}