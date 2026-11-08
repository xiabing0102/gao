# -*- coding: utf-8 -*-
import re, json, urllib.parse
from lxml import etree
from base.spider import Spider as BaseSpider

class Spider(BaseSpider):
    def init(self, extend=""):
        self.host = "https://www.kivrus.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.host + "/"
        }
        self.categories = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "3", "type_name": "短剧"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "5", "type_name": "综艺"},
        ]

    def getName(self):
        return "光影苑视频"

    def _fetch(self, url):
        if not url.startswith('http'):
            url = self.host + url
        rsp = self.fetch(url, headers=self.headers)
        return rsp.text if rsp else ''

    def _fix(self, u):
        if not u: return ''
        if u.startswith('//'): return 'https:' + u
        if u.startswith('/'): return self.host + u
        return u

    def _parse_list(self, html):
        if not html: return []
        tree = etree.HTML(html)
        results, seen = [], set()
        items = tree.xpath('//li[contains(@class,"item")]')
        for item in items:
            try:
                a = item.xpath('.//a[contains(@class,"thumb")]')
                if not a: continue
                a = a[0]
                href = a.get('href', '')
                m = re.search(r'/video/(\d+)\.html', href)
                if not m: continue
                vid = m.group(1)
                if vid in seen: continue
                seen.add(vid)
                img = a.xpath('.//img')
                pic = self._fix(img[0].get('data-original') or img[0].get('src', '')) if img else ''
                title = a.get('title', '') or ''.join(item.xpath('.//h5/a/b/text()')).strip() or ''.join(item.xpath('.//h5/a/text()')).strip()
                remark = ''.join(item.xpath('.//span[contains(@class,"hot")]/text()')).strip()
                results.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remark
                })
            except:
                continue
        return results

    def homeContent(self, filter):
        html = self._fetch('/')
        if not html:
            return {"class": self.categories, "list": [], "filters": {}}
        tree = etree.HTML(html)
        # 提取分类（从导航栏）
        cats = []
        nav_items = tree.xpath('//ul[contains(@class,"nav-list")]/li/a')
        for a in nav_items:
            href = a.get('href', '')
            name = ''.join(a.xpath('.//text()')).strip()
            if name and '首页' not in name and 'TAG' not in name and '排行' not in name:
                m = re.search(r'/tv/(\d+)\.html', href)
                if m:
                    cats.append({"type_id": m.group(1), "type_name": name})
        if cats:
            self.categories = cats
        # 提取首页推荐列表（猜你喜欢区域）
        items = self._parse_list(html)
        return {"class": self.categories, "list": items[:20], "filters": {}}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        # 分类页URL：/tv/{tid}/page/{page}.html 或 /tv/{tid}.html
        if page == 1:
            url = f"/tv/{tid}.html"
        else:
            url = f"/tv/{tid}/page/{page}.html"
        html = self._fetch(url)
        items = self._parse_list(html) if html else []
        # 提取总页数
        pagecount = page
        if html:
            tree = etree.HTML(html)
            last = tree.xpath('//ul[contains(@class,"pagination")]/li[last()]/a/text()')
            if last:
                try:
                    pagecount = int(last[0].strip())
                except:
                    pass
        return {"page": page, "pagecount": pagecount, "limit": 36, "total": 9999, "list": items}

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0].strip()
        url = f"/video/{vid}.html"
        html = self._fetch(url)
        if not html:
            return result
        tree = etree.HTML(html)
        # 标题
        title = ''.join(tree.xpath('//div[contains(@class,"subject-row")]/h1/a/text()')).strip()
        if not title:
            title = ''.join(tree.xpath('//title/text()')).strip()
        # 图片
        pic = tree.xpath('//div[contains(@class,"thumb-wrap")]//img/@src')
        pic = self._fix(pic[0]) if pic else ''
        # 导演、演员
        director = ''.join(tree.xpath('//p[contains(@class,"director")]/span/text()')).strip()
        actor = ''.join(tree.xpath('//p[contains(@class,"performer")]/span/text()')).strip()
        # 地区、年份、备注
        area = ''.join(tree.xpath('//p[contains(@class,"country")]/span/a/text()')).strip()
        year = ''.join(tree.xpath('//p[contains(@class,"year")]/span/text()')).strip()
        remarks = ''.join(tree.xpath('//p[contains(@class,"episodes")]/span/text()')).strip()
        # 简介
        content = ''.join(tree.xpath('//div[contains(@class,"summary-con")]/p/text()')).strip()
        # 提取线路和剧集
        play_from = []
        play_urls = []
        # 获取所有线路标签
        tabs = tree.xpath('//div[contains(@class,"resource-box")]//ul[contains(@class,"nav-tabs")]/li/a')
        tab_names = [''.join(tab.xpath('.//text()')).strip() for tab in tabs]
        # 获取所有线路的剧集列表
        rb_items = tree.xpath('//div[contains(@class,"rb-item")]')
        for idx, rb in enumerate(rb_items):
            eps = []
            for a in rb.xpath('.//ul[contains(@class,"episodes-list")]/li/a'):
                href = a.get('href', '')
                name = ''.join(a.xpath('.//text()')).strip()
                if href and name:
                    eps.append(f"{name}${href}")
            if eps:
                src_name = tab_names[idx] if idx < len(tab_names) else f"线路{idx+1}"
                play_from.append(src_name)
                play_urls.append('#'.join(eps))
        # 如果没提取到线路，尝试从直接播放区域提取
        if not play_from:
            # 检查是否有直接播放链接（player_aaaa）
            m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\});', html, re.S)
            if m:
                try:
                    data = json.loads(m.group(1))
                    play_url = data.get('url', '')
                    if play_url:
                        play_from.append('高清云播')
                        play_urls.append(f"播放${play_url}")
                except:
                    pass
        vod = {
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_director": director,
            "vod_actor": actor,
            "vod_area": area,
            "vod_year": year,
            "vod_remarks": remarks,
            "vod_content": content,
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_urls)
        }
        result["list"].append(vod)
        return result

    def searchContent(self, key, quick, pg="1"):
        try:
            keyword = urllib.parse.quote(key)
        except:
            keyword = key
        page = int(pg) if pg else 1
        url = f"/search.html?wd={keyword}&page={page}"
        html = self._fetch(url)
        items = self._parse_list(html) if html else []
        return {"list": items, "page": page, "pagecount": 1, "limit": 36, "total": len(items)}

    def playerContent(self, flag, id, vipFlags):
        # 如果传入的是完整m3u8地址，直接返回
        if id.startswith('http') and ('.m3u8' in id or '.mp4' in id):
            return {"parse": 0, "url": id, "header": self.headers}
        # 否则视为播放页链接
        url = id if id.startswith('http') else self.host + id
        html = self._fetch(url)
        if not html:
            return {"parse": 1, "url": url, "header": self.headers}
        # 提取 player_aaaa 中的 url
        m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\});', html, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                play_url = data.get('url', '')
                if play_url:
                    return {"parse": 0, "url": self._fix(play_url), "header": self.headers}
            except:
                pass
        # 尝试其他模式
        patterns = [
            r'var\s+now\s*=\s*["\']([^"\']+)["\']',
            r'url:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.S)
            if m:
                val = m.group(1)
                if '.m3u8' not in val and '{' in val:
                    try:
                        pd = json.loads(val)
                        play_url = pd.get('url', '')
                        if play_url:
                            return {"parse": 0, "url": self._fix(play_url), "header": self.headers}
                    except:
                        pass
                else:
                    return {"parse": 0, "url": self._fix(val), "header": self.headers}
        return {"parse": 1, "url": url, "header": self.headers}
