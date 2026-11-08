# -*- coding: utf-8 -*-
import re, json, urllib.parse
from lxml import etree
from base.spider import Spider as BaseSpider

class Spider(BaseSpider):
    def init(self, extend=""):
        self.host = "https://www.stopsmoker.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.host + "/"
        }
        self.categories = [
            {"type_id": "1", "type_name": "最新韩剧"},
            {"type_id": "2", "type_name": "韩国电影"},
            {"type_id": "3", "type_name": "韩国综艺"},
            {"type_id": "4", "type_name": "韩国动漫"},
        ]

    def getName(self):
        return "新韩剧网"

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
        """解析列表，支持多种选择器，适配首页和分类页"""
        if not html: return []
        tree = etree.HTML(html)
        results, seen = [], set()
        
        # 尝试多种选择器，按优先级
        selectors = [
            '//div[contains(@class,"module-item")]',
            '//li[contains(@class,"module-item")]',
            '//div[contains(@class,"module-items")]//div[contains(@class,"module-item")]',
            '//a[contains(@href,"/xinhanju/") and .//img]'  # 最通用
        ]
        items = []
        for sel in selectors:
            items = tree.xpath(sel)
            if items:
                break
        
        # 如果最后选中的是 a 标签，需要特殊处理
        if items and items[0].tag == 'a':
            # 直接处理 a 标签
            for a in items:
                try:
                    href = a.get('href', '')
                    m = re.search(r'/xinhanju/(\d+)\.html', href)
                    if not m: continue
                    vid = m.group(1)
                    if vid in seen: continue
                    seen.add(vid)
                    img = a.xpath('.//img')
                    pic = self._fix(img[0].get('data-src') or img[0].get('src', '')) if img else ''
                    title = a.get('title', '') or ''.join(a.xpath('.//text()')).strip()
                    if not title:
                        # 尝试从父级找标题
                        parent = a.getparent()
                        if parent is not None:
                            title_el = parent.xpath('.//div[contains(@class,"module-item-titlebox")]/a')
                            if title_el:
                                title = ''.join(title_el[0].xpath('.//text()')).strip()
                    # 备注
                    remark = ''
                    parent = a.getparent()
                    if parent is not None:
                        remark_el = parent.xpath('.//div[contains(@class,"module-item-text")]')
                        if remark_el:
                            remark = ''.join(remark_el[0].xpath('.//text()')).strip()
                    results.append({
                        "vod_id": vid,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": remark
                    })
                except:
                    continue
            return results
        
        # 原有逻辑：处理 div.module-item
        for item in items:
            try:
                a = item.xpath('.//div[contains(@class,"module-item-pic")]/a')
                if not a:
                    # 如果没有 module-item-pic，直接找 a
                    a = item.xpath('.//a[contains(@href,"/xinhanju/")]')
                if not a: continue
                a = a[0]
                href = a.get('href', '')
                m = re.search(r'/xinhanju/(\d+)\.html', href)
                if not m: continue
                vid = m.group(1)
                if vid in seen: continue
                seen.add(vid)
                img = a.xpath('.//img')
                pic = self._fix(img[0].get('data-src') or img[0].get('src', '')) if img else ''
                title_el = item.xpath('.//div[contains(@class,"module-item-titlebox")]/a')
                if not title_el:
                    title_el = item.xpath('.//a[contains(@class,"module-item-title")]')
                if not title_el:
                    title_el = item.xpath('.//a[contains(@href,"/xinhanju/")]')
                title = ''.join(title_el[0].xpath('.//text()')).strip() if title_el else ''
                remark_el = item.xpath('.//div[contains(@class,"module-item-text")]')
                remark = ''.join(remark_el[0].xpath('.//text()')).strip() if remark_el else ''
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
        items = self._parse_list(html)
        return {"class": self.categories, "list": items[:20], "filters": {}}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        if page == 1:
            url = f"/xhj/{tid}.html"
        else:
            url = f"/xhj/{tid}-{page}.html"
        html = self._fetch(url)
        items = self._parse_list(html) if html else []
        pagecount = page
        if html:
            tree = etree.HTML(html)
            page_links = tree.xpath('//div[contains(@class,"pagination")]//a')
            for a in page_links:
                text = a.text.strip() if a.text else ''
                if text.isdigit():
                    num = int(text)
                    if num > pagecount:
                        pagecount = num
            if pagecount == page:
                last = tree.xpath('//a[contains(text(),"尾页")]/@href')
                if last:
                    m = re.search(r'-(\d+)\.html', last[0])
                    if m:
                        pagecount = int(m.group(1))
        return {"page": page, "pagecount": pagecount, "limit": 36, "total": 9999, "list": items}

    def detailContent(self, ids):
        result = {"list": []}
        raw_id = ids[0].strip()
        m = re.search(r'(\d+)', raw_id)
        if not m:
            return result
        vid = m.group(1)
        url = f"/xinhanju/{vid}.html"
        html = self._fetch(url)
        if not html:
            return result
        tree = etree.HTML(html)

        # 标题
        title = ''.join(tree.xpath('//h1[contains(@class,"page-title")]/text()')).strip()
        if not title:
            title = ''.join(tree.xpath('//title/text()')).strip()

        # 图片
        pic = tree.xpath('//div[contains(@class,"video-cover")]//img/@src')
        if not pic:
            pic = tree.xpath('//div[contains(@class,"video-cover")]//img/@data-src')
        pic = self._fix(pic[0]) if pic else ''

        # 导演、主演、简介等
        director = ''.join(tree.xpath('//div[contains(@class,"video-info-items")][span[contains(text(),"导演：")]]/div[contains(@class,"video-info-item")]/a/text()')).strip()
        actor = ''.join(tree.xpath('//div[contains(@class,"video-info-items")][span[contains(text(),"主演：")]]/div[contains(@class,"video-info-item")]/a/text()')).strip()
        content = ''.join(tree.xpath('//div[contains(@class,"video-info-content")]/text()')).strip()
        area = ''.join(tree.xpath('//div[contains(@class,"video-info-items")][span[contains(text(),"地区")]]/div[contains(@class,"video-info-item")]/text()')).strip()
        year = ''.join(tree.xpath('//div[contains(@class,"video-info-items")][span[contains(text(),"上映")]]/div[contains(@class,"video-info-item")]/text()')).strip()
        remark = ''.join(tree.xpath('//div[contains(@class,"video-info-items")][span[contains(text(),"更新")]]/div[contains(@class,"video-info-item")]/text()')).strip()

        # 提取线路和剧集
        play_from = []
        play_urls = []
        tabs = tree.xpath('//ul[contains(@class,"nav-tabs")]/li/a')
        line_names = []
        for tab in tabs:
            name = ''.join(tab.xpath('.//text()')).strip()
            name = re.sub(r'\s*\(\d+\)', '', name).strip()
            if name:
                line_names.append(name)

        panes = tree.xpath('//div[contains(@class,"tab-pane")]')
        if not panes:
            panes = tree.xpath('//div[contains(@class,"rb-item")]')

        for idx, pane in enumerate(panes):
            eps = []
            for a in pane.xpath('.//ul/li/a'):
                href = a.get('href', '')
                name = ''.join(a.xpath('.//text()')).strip()
                if href and name:
                    eps.append(f"{name}${href}")
            if eps:
                src_name = line_names[idx] if idx < len(line_names) else f"线路{idx+1}"
                play_from.append(src_name)
                play_urls.append('#'.join(eps))

        if not play_from:
            all_eps = []
            for ul in tree.xpath('//ul[contains(@class,"myui-content__list")]'):
                for a in ul.xpath('.//li/a'):
                    href = a.get('href', '')
                    name = ''.join(a.xpath('.//text()')).strip()
                    if href and name:
                        all_eps.append(f"{name}${href}")
            if all_eps:
                play_from.append("默认线路")
                play_urls.append('#'.join(all_eps))

        vod = {
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_director": director,
            "vod_actor": actor,
            "vod_area": area,
            "vod_year": year,
            "vod_remarks": remark,
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
        url = f"/search.php?searchword={keyword}&page={page}"
        html = self._fetch(url)
        items = self._parse_list(html) if html else []
        return {"list": items, "page": page, "pagecount": 1, "limit": 36, "total": len(items)}

    def playerContent(self, flag, id, vipFlags):
        url = id if id.startswith('http') else self.host + id
        html = self._fetch(url)
        if not html:
            return {"parse": 1, "url": url, "header": self.headers}
        # 提取 player_aaaa
        m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\});', html, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                play_url = data.get('url', '')
                if play_url:
                    return {"parse": 0, "url": self._fix(play_url), "header": self.headers}
            except:
                pass
        # 其他模式
        m = re.search(r'var\s+now\s*=\s*["\']([^"\']+)["\']', html)
        if m:
            return {"parse": 0, "url": self._fix(m.group(1)), "header": self.headers}
        m = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
        if m:
            return {"parse": 0, "url": self._fix(m.group(1)), "header": self.headers}
        return {"parse": 1, "url": url, "header": self.headers}
