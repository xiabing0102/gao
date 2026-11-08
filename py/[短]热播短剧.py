# coding=utf-8
"""
目标站: 热播短剧 (www.nyhnbb.com)
适配说明:
1. 首页/分类/搜索列表: 使用 .module-item 卡片解析
2. 详情页: 支持 /reboduanju/{id}.html
3. 播放页: 支持 /play/{id}-{线路}-{集数}.html，优先提取 var now 里的 m3u8
"""
import json
import re
import sys
import urllib.parse
from urllib.parse import urljoin

from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        self.site_url = "https://www.nyhnbb.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.site_url + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self.categories = [
            {"type_id": "1", "type_name": "重生"},
            {"type_id": "2", "type_name": "穿越"},
            {"type_id": "3", "type_name": "爽剧"},
            {"type_id": "4", "type_name": "言情"},
            {"type_id": "5", "type_name": "都市"},
            {"type_id": "6", "type_name": "古装"},
            {"type_id": "7", "type_name": "悬疑"},
            {"type_id": "8", "type_name": "剧情"},
        ]

    def _abs_url(self, url):
        return urljoin(self.site_url, url or "")

    def _clean_text(self, text):
        return re.sub(r"\s+", " ", text or "").strip()

    def _get_html(self, url, data=None):
        try:
            if data is None:
                resp = self.fetch(url, headers=self.headers)
            else:
                headers = dict(self.headers)
                headers.update({
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Requested-With": "XMLHttpRequest",
                })
                resp = self.fetch(url, headers=headers, data=data)
            return resp.text if resp else ""
        except Exception:
            return ""

    def _parse_video_list(self, soup, max_count=0):
        video_list = []
        seen = set()

        # 主列表卡片
        items = soup.select(".module-item")
        for item in items:
            link = (
                item.select_one("a.module-item-title[href*='/reboduanju/']")
                or item.select_one(".video-name a[href*='/reboduanju/']")
                or item.select_one("a.module-item-pic[href*='/reboduanju/']")
                or item.select_one("a[href*='/reboduanju/']")
            )
            if not link:
                continue

            href = link.get("href", "")
            match = re.search(r"/reboduanju/(\d+)\.html", href)
            if not match:
                continue
            vod_id = match.group(1)
            if vod_id in seen:
                continue

            title = link.get("title", "") or link.get_text(" ", strip=True)
            if not title:
                title_node = item.select_one(".module-item-title")
                title = title_node.get("title", "") or title_node.get_text(" ", strip=True) if title_node else ""
            title = self._clean_text(title)
            if not title:
                continue

            img = item.select_one("img")
            pic = ""
            if img:
                pic = img.get("data-src", "") or img.get("data-original", "") or img.get("src", "")
                pic = self._abs_url(pic)

            remark = ""
            remark_node = item.select_one(".module-item-text")
            if remark_node:
                remark = self._clean_text(remark_node.get_text(" ", strip=True))
            if not remark:
                caption = item.select_one(".module-item-caption")
                remark = self._clean_text(caption.get_text(" ", strip=True)) if caption else ""

            seen.add(vod_id)
            video_list.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
            if max_count > 0 and len(video_list) >= max_count:
                break

        # 兜底: 页面里散落的详情链接
        if not video_list:
            for link in soup.select("a[href*='/reboduanju/']"):
                href = link.get("href", "")
                match = re.search(r"/reboduanju/(\d+)\.html", href)
                if not match:
                    continue
                vod_id = match.group(1)
                if vod_id in seen:
                    continue
                title = self._clean_text(link.get("title", "") or link.get_text(" ", strip=True))
                if not title:
                    continue
                seen.add(vod_id)
                video_list.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": "",
                    "vod_remarks": "",
                })
                if max_count > 0 and len(video_list) >= max_count:
                    break

        return video_list

    def homeContent(self, filter):
        html = self._get_html(self.site_url + "/")
        soup = BeautifulSoup(html, "html.parser")
        return {
            "class": self.categories,
            "list": self._parse_video_list(soup, max_count=36),
            "filters": {},
        }

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        if page <= 1:
            url = f"{self.site_url}/rbdj/{tid}.html"
        else:
            url = f"{self.site_url}/rbdj/{tid}-{page}.html"

        html = self._get_html(url)
        if not html and page > 1:
            # 部分模板可能使用下划线分页，做一个兼容兜底
            html = self._get_html(f"{self.site_url}/rbdj/{tid}_{page}.html")

        if not html:
            return {"list": [], "page": page, "pagecount": 1, "limit": 36, "total": 0}

        soup = BeautifulSoup(html, "html.parser")
        video_list = self._parse_video_list(soup)
        pagecount = page

        for a in soup.select(".page a, .pagination a, .myui-page a, a[href*='/rbdj/']"):
            text = self._clean_text(a.get_text())
            href = a.get("href", "")
            if text.isdigit():
                pagecount = max(pagecount, int(text))
            page_match = re.search(rf"/rbdj/{re.escape(str(tid))}[-_](\d+)\.html", href)
            if page_match:
                pagecount = max(pagecount, int(page_match.group(1)))

        return {
            "list": video_list,
            "page": page,
            "pagecount": max(pagecount, 1),
            "limit": 36,
            "total": len(video_list) * max(pagecount, 1),
        }

    def detailContent(self, ids):
        if not ids:
            return {"list": []}

        vod_id = str(ids[0])
        url = f"{self.site_url}/reboduanju/{vod_id}.html"
        html = self._get_html(url)
        if not html:
            return {"list": []}

        soup = BeautifulSoup(html, "html.parser")

        vod_name = vod_id
        title_node = (
            soup.select_one("h1")
            or soup.select_one(".video-info-title")
            or soup.select_one("meta[property='og:title']")
        )
        if title_node:
            vod_name = title_node.get("content", "") or title_node.get_text(" ", strip=True) or vod_id
            vod_name = self._clean_text(vod_name)

        vod_pic = ""
        og_img = soup.select_one("meta[property='og:image']")
        if og_img:
            vod_pic = og_img.get("content", "")
        if not vod_pic:
            img = soup.select_one(".video-cover img, .video-pic img, .module-item-pic img, img")
            if img:
                vod_pic = img.get("data-src", "") or img.get("data-original", "") or img.get("src", "")
        vod_pic = self._abs_url(vod_pic)

        vod_content = ""
        desc_node = soup.select_one(".video-info-content, .desc, .content_desc, meta[property='og:description']")
        if desc_node:
            vod_content = desc_node.get("content", "") or desc_node.get_text(" ", strip=True)
        if not vod_content:
            text = soup.get_text(" ", strip=True)
            match = re.search(r"剧情[：:]\s*(.+?)(?:播放列表|《.+?》剧情介绍|$)", text)
            if match:
                vod_content = match.group(1)
        vod_content = self._clean_text(vod_content)

        vod_actor = ""
        vod_director = ""
        vod_area = ""
        vod_year = ""
        vod_class = ""

        meta_map = {
            "vod_actor": "meta[property='og:video:actor']",
            "vod_director": "meta[property='og:video:director']",
            "vod_area": "meta[property='og:video:area']",
            "vod_class": "meta[property='og:video:class']",
        }
        meta_actor = soup.select_one(meta_map["vod_actor"])
        meta_director = soup.select_one(meta_map["vod_director"])
        meta_area = soup.select_one(meta_map["vod_area"])
        meta_class = soup.select_one(meta_map["vod_class"])
        if meta_actor:
            vod_actor = meta_actor.get("content", "")
        if meta_director:
            vod_director = meta_director.get("content", "")
        if meta_area:
            vod_area = meta_area.get("content", "")
        if meta_class:
            vod_class = meta_class.get("content", "")

        year_match = re.search(r"(?:上映|年份)[：:\s]+(\d{4})", soup.get_text(" ", strip=True))
        if year_match:
            vod_year = year_match.group(1)

        play_from_list = []
        play_url_list = []

        # 标签名和播放列表对应: href="#playlist2" -> div#playlist2
        line_names = {}
        for a in soup.select("a[href^='#playlist']"):
            anchor = a.get("href", "").replace("#", "")
            name = self._clean_text(a.get_text(" ", strip=True))
            if anchor and name and "排序" not in name:
                name = re.sub(r"\(\d+\)", "", name).strip() or name
                line_names[anchor] = name

        blocks = soup.select(".tab-pane[id^='playlist']")
        if not blocks:
            blocks = soup.select(".sort-list")

        for idx, block in enumerate(blocks):
            anchor = block.get("id", "")
            line_name = line_names.get(anchor) or f"线路{idx + 1}"
            episodes = []
            seen_ep = set()
            for a in block.select("a[href*='/play/']"):
                href = a.get("href", "")
                ep_name = self._clean_text(a.get("title", "") or a.get_text(" ", strip=True))
                if not href or not ep_name:
                    continue
                href = self._abs_url(href)
                if href in seen_ep:
                    continue
                seen_ep.add(href)
                episodes.append(f"{ep_name}${href}")
            if episodes:
                play_from_list.append(line_name)
                play_url_list.append("#".join(episodes))

        if not play_url_list:
            episodes = []
            seen_ep = set()
            for a in soup.select("a[href*='/play/']"):
                href = self._abs_url(a.get("href", ""))
                ep_name = self._clean_text(a.get("title", "") or a.get_text(" ", strip=True))
                if not href or not ep_name or href in seen_ep:
                    continue
                seen_ep.add(href)
                episodes.append(f"{ep_name}${href}")
            if episodes:
                play_from_list.append("默认线路")
                play_url_list.append("#".join(episodes))

        vod = {
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_actor": vod_actor,
            "vod_director": vod_director,
            "vod_area": vod_area,
            "vod_year": vod_year,
            "vod_class": vod_class,
            "vod_play_from": "$$$".join(play_from_list) if play_from_list else "默认线路",
            "vod_play_url": "$$$".join(play_url_list) if play_url_list else f"播放${url}",
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        encoded_key = urllib.parse.quote(key)
        url = f"{self.site_url}/search.php?searchword={encoded_key}"
        if page > 1:
            url += f"&page={page}"

        html = self._get_html(url)
        if not html or "页面加载中" in html:
            html = self._get_html(
                f"{self.site_url}/search.php",
                data=f"searchword={encoded_key}&page={page}",
            )

        if not html:
            return {"list": [], "page": page, "pagecount": 1}

        soup = BeautifulSoup(html, "html.parser")
        return {
            "list": self._parse_video_list(soup),
            "page": page,
            "pagecount": 1,
        }

    def playerContent(self, flag, id, vipFlags):
        play_url = str(id)
        if play_url.startswith("http"):
            url = play_url
        elif play_url.startswith("/"):
            url = self._abs_url(play_url)
        elif re.match(r"^\d+-\d+-\d+$", play_url):
            url = f"{self.site_url}/play/{play_url}.html"
        elif re.match(r"^\d+$", play_url):
            url = f"{self.site_url}/play/{play_url}-1-0.html"
        else:
            url = self._abs_url(play_url)

        html = self._get_html(url)
        if not html:
            return {"parse": 1, "url": url, "header": self.headers}

        # 该站播放页通常直接写入: var now="https://.../index.m3u8"
        now_match = re.search(r'var\s+now\s*=\s*["\']([^"\']+)["\']', html)
        if now_match:
            video_url = now_match.group(1).strip()
            if video_url:
                return {
                    "parse": 0,
                    "url": video_url,
                    "header": {
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": url,
                    },
                }

        # 兼容 MacCMS 常见 player_aaaa
        player_match = re.search(r"var\s+player_aaaa\s*=\s*(\{.*?\})\s*</script>", html, re.S)
        if player_match:
            try:
                data = json.loads(player_match.group(1))
                video_url = data.get("url", "")
                if video_url:
                    return {"parse": 0, "url": video_url, "header": self.headers}
            except Exception:
                pass

        # 通用兜底
        m3u8 = re.search(r'(https?://[^\s"\'<>]+?\.m3u8[^\s"\'<>]*)', html)
        if m3u8:
            return {"parse": 0, "url": m3u8.group(1), "header": self.headers}

        mp4 = re.search(r'(https?://[^\s"\'<>]+?\.mp4[^\s"\'<>]*)', html)
        if mp4:
            return {"parse": 0, "url": mp4.group(1), "header": self.headers}

        iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
        if iframe:
            iframe_url = self._abs_url(iframe.group(1))
            return {"parse": 1, "url": iframe_url, "header": self.headers}

        return {"parse": 1, "url": url, "header": self.headers}
