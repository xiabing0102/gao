# coding=utf-8
"""
目标站: 555电影 (555dy3.com)
站点: https://555dy3.com/
海洋CMS架构 - 深度修复剧名显示 + 播放解析 + 选集命名
"""
import re
import sys
import json
import base64
import urllib.parse
from html import unescape
from collections import OrderedDict
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    # 备注文本，绝不当作剧名（更新至xx集 / 全集 / 已完结 / 第N集 / 正片 …）
    _NOTE_TITLE_RE = re.compile(
        r'^('
        r'更新|全集|完结|已完结|全\d+集|第\d+集|正片|HD|高清|超清|蓝光|4K|'
        r'预告|花絮|特辑|番外|TC|TS|抢先|未删减|会员|独播|\d+集|共\d+集'
        r')'
    )

    def init(self, extend=""):
        self.site_url = "https://555dy3.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        self.categories = self._fetch_categories()

    # ==================== 分类 ====================
    def _fetch_categories(self):
        try:
            resp = self.fetch(self.site_url, headers=self.headers)
            if not resp:
                return self._default_categories()
            soup = BeautifulSoup(resp.text, 'html.parser')
            nav_links = soup.select('.navbar-items .navbar-item a.links, .navbar-items a.links')
            categories = []
            seen = set()
            exclude = ['首页', 'Netflix', '追剧周表', '今日更新', '专题列表', '排行榜',
                       '回家地址', '午夜蓝光', '留言求片', 'APP', '福利']
            for a in nav_links:
                href = a.get('href', '')
                match = re.search(r'/vodtype/(\d+)\.html', href)
                if not match:
                    continue
                tid = match.group(1)
                name = a.get_text(strip=True)
                if not name or tid in seen or name in exclude:
                    continue
                seen.add(tid)
                categories.append({"type_id": tid, "type_name": name})
            if categories:
                return categories
        except Exception as e:
            print(f"[555电影] 获取分类失败: {e}")
        return self._default_categories()

    def _default_categories(self):
        return [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "连续剧"},
            {"type_id": "126", "type_name": "擦边短剧"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "3", "type_name": "综艺纪录"},
        ]

    def _fix_url(self, url):
        if not url:
            return ""
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if not url.startswith("http"):
            return urllib.parse.urljoin(self.site_url + "/", url)
        return url

    # ==================== 文本清洗 & 备注识别 ====================
    def _clean_text(self, s):
        """剥离残留HTML标签 + 实体解码 + strip
        处理 img.alt="<em>都市</em>古仙医" 这类脏数据
        """
        if not s:
            return ''
        s = re.sub(r'<[^>]+>', '', s)   # 去掉 <em>...</em>
        try:
            s = unescape(s)
        except Exception:
            pass
        return s.strip()

    def _is_note_title(self, text):
        """判断文本是否是备注（更新至xx集 / 全集 / 已完结 / 第N集）"""
        if not text:
            return True
        text = text.strip()
        if len(text) < 2:
            return True
        return bool(self._NOTE_TITLE_RE.match(text))

    # ==================== 列表解析（核心修复） ====================
    def _parse_video_list(self, html):
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        items = OrderedDict()  # vid -> {vod_id, vod_name, vod_pic, vod_remarks}

        # ① 主策略：按"卡片元素"遍历，每卡一次，剧名只从标题节点取
        card_sel = ('div.module-card-item, div.module-list-item, '
                    'div.public-list-box, div.module-item, '
                    'li.vod-item, div.video-item, div.stui-vodlist__box')
        for card in soup.select(card_sel):
            # 定位详情链接：优先标题区，其次海报
            link = (card.select_one('.module-card-item-title a[href*="/voddetail/"]')
                    or card.select_one('.module-title a[href*="/voddetail/"]')
                    or card.select_one('.public-list-title a[href*="/voddetail/"]')
                    or card.select_one('a[href*="/voddetail/"]'))
            if not link:
                continue
            m = re.search(r'/voddetail/(\d+)\.html', link.get('href', ''))
            if not m:
                continue
            vid = m.group(1)
            if vid in items:
                continue

            # 剧名：只认标题节点，其余一律不要
            title = ''
            title_el = card.select_one(
                '.module-card-item-title, .module-title, '
                '.public-list-title, .vod-title, h3, h4')
            if title_el:
                title = self._clean_text(title_el.get_text(' ', strip=True))

            # 兜底：img.alt（同样要清洗 <em>）
            if not title or self._is_note_title(title):
                img = card.select_one('img')
                if img:
                    alt = self._clean_text(img.get('alt') or '')
                    if alt and not self._is_note_title(alt):
                        title = alt

            # 仍不可用 → 丢弃该卡，绝不拿集数冒充剧名
            if not title or self._is_note_title(title):
                continue

            # 封面
            pic = ''
            img = card.select_one('img')
            if img:
                pic = (img.get('data-original') or img.get('data-src')
                       or img.get('src') or '')
            if not pic:
                for el in card.select('[style*="url("]'):
                    bg = re.search(r'url\(([^)]+)\)', el.get('style', ''))
                    if bg:
                        pic = bg.group(1).strip('"').strip("'")
                        break

            items[vid] = {
                "vod_id": vid,
                "vod_name": title,           # ← 真实剧名
                "vod_pic": self._fix_url(pic),
                "vod_remarks": "",           # ← 屏蔽其它所有显示
            }

        if items:
            return list(items.values())

        # ② 兜底：只认标题区链接
        for a in soup.select(
            '.module-card-item-title a[href*="/voddetail/"], '
            '.module-title a[href*="/voddetail/"], '
            '.public-list-title a[href*="/voddetail/"]'
        ):
            m = re.search(r'/voddetail/(\d+)\.html', a.get('href', ''))
            if not m:
                continue
            vid = m.group(1)
            if vid in items:
                continue
            title = self._clean_text(a.get_text(' ', strip=True))
            if not title or self._is_note_title(title):
                continue
            items[vid] = {
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": "",
                "vod_remarks": "",
            }
        return list(items.values())

    # ==================== 首页 ====================
    def homeContent(self, filter):
        resp = self.fetch(self.site_url + "/", headers=self.headers)
        video_list = []
        if resp:
            video_list = self._parse_video_list(resp.text)[:30]
        return {"class": self.categories, "list": video_list, "filters": {}}

    def homeVideoContent(self):
        return self.homeContent(False)

    # ==================== 分页辅助 ====================
    def _parse_pagecount(self, html, current=1):
        try:
            soup = BeautifulSoup(html, 'html.parser')
            nums = []
            for a in soup.select('#page a, .page a, .pagination a, .page-link'):
                t = a.get_text(strip=True)
                if t.isdigit():
                    nums.append(int(t))
                else:
                    m = re.search(r'----------(\d+)---\.html', a.get('href', ''))
                    if m:
                        nums.append(int(m.group(1)))
                    m2 = re.search(r'[?&]page=(\d+)', a.get('href', ''))
                    if m2:
                        nums.append(int(m2.group(1)))
            if nums:
                return max(nums)
        except Exception:
            pass
        return current

    # ==================== 分类页 ====================
    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        urls_to_try = []
        for base in (f"{self.site_url}/vodtype/{tid}",
                     f"{self.site_url}/vodshow/{tid}",
                     f"{self.site_url}/vodlist/{tid}"):
            if page == 1:
                urls_to_try.append(base + ".html")
            else:
                urls_to_try.append(base + f"-{page}.html")
                urls_to_try.append(base + f".html?page={page}")
        html_text = ""
        for url in urls_to_try:
            resp = self.fetch(url, headers=self.headers)
            if resp:
                html_text = resp.text
                break
        if not html_text:
            return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}
        video_list = self._parse_video_list(html_text)
        pagecount = self._parse_pagecount(html_text, page)
        return {
            "list": video_list,
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": len(video_list) * pagecount
        }

    # ==================== 详情 + 选集命名 ====================
    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = ids[0]
        url = f"{self.site_url}/voddetail/{vod_id}.html"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": []}
        soup = BeautifulSoup(resp.text, 'html.parser')

        # ---- 剧名：多层级兜底，确保取到真实剧名 ----
        vod_name = ''
        # ① 最可靠：h1 / .module-info-heading h1
        for sel in ('h1', '.module-info-heading h1', '.vod-title',
                    '.module-info-heading', '.detail-title'):
            el = soup.select_one(sel)
            if el:
                t = self._clean_text(el.get_text(' ', strip=True))
                if t and not self._is_note_title(t):
                    vod_name = t
                    break
        # ② 兜底：页面 title 标签
        if not vod_name:
            title_tag = soup.select_one('title')
            if title_tag:
                t = self._clean_text(title_tag.get_text(strip=True))
                # 去掉 "- 555电影" 等后缀
                t = re.sub(r'\s*[-–—|]\s*555.*$', '', t).strip()
                if t and not self._is_note_title(t):
                    vod_name = t
        # ③ 最终兜底
        if not vod_name:
            vod_name = vod_id

        vod_pic = ''
        img_elem = soup.select_one(
            '.vod-pic img, .detail-pic img, .cover img, .module-item-pic img')
        if img_elem:
            vod_pic = (img_elem.get('data-original')
                       or img_elem.get('data-src')
                       or img_elem.get('src') or '')
            vod_pic = self._fix_url(vod_pic)

        vod_content = ''
        content_elem = soup.select_one(
            '.vod-content, .detail-content, .desc, .module-info-introduction')
        if content_elem:
            vod_content = content_elem.get_text(' ', strip=True)

        vod_actor = ''
        actor_elem = soup.select_one('.vod-actor, .actor')
        if actor_elem:
            vod_actor = (actor_elem.get_text(strip=True)
                         .replace('主演：', '').replace('主演:', '').strip())

        vod_director = ''
        director_elem = soup.select_one('.vod-director, .director')
        if director_elem:
            vod_director = (director_elem.get_text(strip=True)
                            .replace('导演：', '').replace('导演:', '').strip())

        vod_year = ''
        year_elem = soup.select_one('.vod-year, .year')
        if year_elem:
            vod_year = (year_elem.get_text(strip=True)
                        .replace('年份：', '').replace('年份:', '').strip())

        # ---- 播放列表：按线路 sid 分组 ----
        groups = OrderedDict()
        for a in soup.select('a[href*="/vodplay/"]'):
            m = re.search(r'/vodplay/(\d+)-(\d+)-(\d+)\.html', a.get('href', ''))
            if not m:
                continue
            sid = m.group(2)
            try:
                nid = int(m.group(3))
            except Exception:
                nid = 0
            name = a.get_text(strip=True)
            groups.setdefault(sid, []).append((nid, name, a.get('href', '')))

        play_from_list = []
        play_url_list = []

        for idx, sid in enumerate(groups.keys()):
            eps = sorted(groups[sid], key=lambda x: x[0])
            filtered = [e for e in eps
                        if not re.match(r'^(立即播放|点击播放|在线播放|立即观看|播放)$',
                                        (e[1] or '').strip())]
            if filtered:
                eps = filtered
            if not eps:
                continue

            line_name = f"线路{idx + 1}"
            episodes = []

            if len(eps) == 1:
                nid, name, href = eps[0]
                name = (name or '').strip()
                if not name or not re.search(
                        r'(正片|HD|高清|超清|蓝光|4K|完整版|预告|花絮|特辑|番外)',
                        name, re.I):
                    name = '正片'
                episodes.append(f"{name}${self._fix_url(href)}")
            else:
                for i, (nid, name, href) in enumerate(eps, 1):
                    episodes.append(f"第{i}集${self._fix_url(href)}")

            play_from_list.append(line_name)
            play_url_list.append('#'.join(episodes))

        if not play_url_list:
            vod_play_from = ''
            vod_play_url = ''
        else:
            vod_play_from = '$$$'.join(play_from_list)
            vod_play_url = '$$$'.join(play_url_list)

        return {"list": [{
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
        }]}

    # ==================== 搜索 ====================
    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        encoded_key = urllib.parse.quote(key)
        url = f"{self.site_url}/vodsearch/{encoded_key}----------{page}---.html"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1}
        video_list = self._parse_video_list(resp.text)
        pagecount = self._parse_pagecount(resp.text, page)
        return {"list": video_list, "page": page, "pagecount": pagecount}

    # ==================== 播放解析 ====================
    def playerContent(self, flag, id, vipFlags):
        play_url = self._fix_url(id)
        headers = dict(self.headers)
        headers['Referer'] = self.site_url + '/'

        if re.search(r'\.(m3u8|mp4|flv|mkv)(\?|$)', play_url, re.I):
            return {"parse": 0, "url": play_url, "header": headers}

        visited = set()
        max_depth = 8

        def _try_decode(u):
            if not u:
                return u
            if u.startswith('http'):
                return u
            for fn in (base64.urlsafe_b64decode, base64.b64decode):
                try:
                    padded = u + '=' * (-len(u) % 4)
                    d = fn(padded).decode('utf-8', errors='ignore')
                    if d.startswith('http'):
                        return d
                except Exception:
                    pass
            if u.startswith('ptth'):
                d = u[::-1]
                if d.startswith('http'):
                    return d
            try:
                d = urllib.parse.unquote(u)
                if d.startswith('http'):
                    return d
            except Exception:
                pass
            return u

        def _extract(url, depth=0):
            if depth > max_depth or url in visited:
                return None
            visited.add(url)
            if re.search(r'\.(m3u8|mp4|flv|mkv)(\?|$)', url, re.I):
                return url
            resp = self.fetch(url, headers=headers)
            if not resp:
                return None
            html = resp.text

            m = (re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*;?\s*(?:</script>|$)',
                           html, re.DOTALL)
                 or re.search(r'player_aaaa\s*=\s*(\{.*?\})\s*;', html, re.DOTALL))
            if m:
                try:
                    data = json.loads(m.group(1))
                    url_val = _try_decode(data.get('url', '') or '')
                    if url_val and re.search(r'\.(m3u8|mp4|flv|mkv)', url_val, re.I):
                        return url_val
                    if url_val and url_val.startswith('http'):
                        r = _extract(self._fix_url(url_val), depth + 1)
                        if r:
                            return r
                    link = data.get('link', '') or ''
                    if link:
                        link_url = self._fix_url(link)
                        if link_url != url and link_url not in visited:
                            r = _extract(link_url, depth + 1)
                            if r:
                                return r
                except Exception as e:
                    print(f"[555电影] player_aaaa 解析失败: {e}")

            iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html)
            if iframe:
                iframe_url = self._fix_url(iframe.group(1))
                if iframe_url != url and iframe_url not in visited:
                    r = _extract(iframe_url, depth + 1)
                    if r:
                        return r

            for pat in (r'<video[^>]+src=["\']([^"\']+)["\']',
                        r'<source[^>]+src=["\']([^"\']+)["\']'):
                vm = re.search(pat, html)
                if vm:
                    v = vm.group(1)
                    if v.startswith('//'):
                        v = 'https:' + v
                    if re.search(r'\.(m3u8|mp4|flv)', v, re.I):
                        return v

            m3u8 = re.search(r'((?:https?:)?//[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
            if m3u8:
                u = m3u8.group(1)
                return 'https:' + u if u.startswith('//') else u

            for pat in (r'["\']url["\']\s*:\s*["\']([^"\']+)["\']',
                        r'["\']link["\']\s*:\s*["\']([^"\']+)["\']',
                        r'var\s+playurl\s*=\s*["\']([^"\']+)["\']',
                        r'var\s+video\s*=\s*["\']([^"\']+)["\']',
                        r'var\s+src\s*=\s*["\']([^"\']+)["\']'):
                vm = re.search(pat, html, re.I)
                if vm:
                    v = _try_decode(vm.group(1))
                    if re.search(r'\.(m3u8|mp4|flv)', v, re.I):
                        return v
            return None

        final_url = _extract(play_url)
        if final_url:
            final_url = self._fix_url(final_url)
            if re.search(r'\.(m3u8|mp4|flv|mkv)', final_url, re.I):
                return {"parse": 0, "url": final_url, "header": headers}
            if final_url != play_url and final_url not in visited:
                return self.playerContent(flag, final_url, vipFlags)

        return {"parse": 1, "url": play_url, "header": headers}