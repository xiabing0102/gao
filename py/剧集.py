# -*- coding: utf-8 -*-
import re, json, urllib.parse, base64
from lxml import etree
from base.spider import Spider as BaseSpider

class Spider(BaseSpider):
    def init(self, extend=""):
        self.host = "https://m.ikjuji.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.host + "/"
        }
        self.categories = [
            {"type_id": "1", "type_name": "韩剧"},
            {"type_id": "6", "type_name": "陆剧"},
            {"type_id": "2", "type_name": "日剧"},
            {"type_id": "3", "type_name": "美剧"},
            {"type_id": "4", "type_name": "泰剧"},
            {"type_id": "7", "type_name": "港剧"},
            {"type_id": "8", "type_name": "台剧"},
            {"type_id": "9", "type_name": "短剧"},
        ]

    def getName(self):
        return "剧集TV"

    def _fetch(self, url):
        if not url.startswith('http'):
            url = self.host + url
        rsp = self.fetch(url, headers=self.headers)
        return rsp.text if rsp else ''

    def _fix(self, u):
        if not u: return ''
        u = u.replace('&amp;', '&').strip()
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.host + u
        return u

    def _proxy_img(self, url):
        if not url:
            return ''
        if 'getProxyUrl' in url or 'type=pic' in url:
            return url
        b64 = base64.b64encode(url.encode('utf-8')).decode('ascii')
        return f"{self.getProxyUrl()}&type=pic&url={b64}"

    def _parse_list(self, html):
        if not html: return []
        tree = etree.HTML(html)
        results, seen = [], set()
        items = tree.xpath('//li[contains(@class, "m-item")]')
        if not items:
            items = tree.xpath('//div[contains(@class, "m-item")]')
        for item in items:
            try:
                a = item.xpath('.//a[contains(@href, "/detail/")]')
                if not a: continue
                a = a[0]
                href = a.get('href', '')
                m = re.search(r'/detail/(\d+)\.html', href)
                if not m: continue
                vid = m.group(1)
                if vid in seen: continue
                seen.add(vid)
                img = a.xpath('.//img')
                pic = ''
                if img:
                    img = img[0]
                    pic = img.get('data-original') or img.get('data-src') or img.get('src', '')
                    if 'blank' in pic or not pic:
                        lazy_img = item.xpath('.//img[contains(@class, "lazy")]')
                        if lazy_img:
                            pic = lazy_img[0].get('data-original') or lazy_img[0].get('data-src') or ''
                    pic = self._fix(pic)
                    pic = self._proxy_img(pic)
                title_el = item.xpath('.//h3[contains(@class, "title")]/a')
                title = ''.join(title_el[0].xpath('.//text()')).strip() if title_el else ''
                if not title:
                    title = a.get('title', '') or ''.join(a.xpath('.//text()')).strip()
                remark = ''
                remark_el = item.xpath('.//span[contains(@class, "label")]')
                if remark_el:
                    remark = ''.join(remark_el[0].xpath('.//text()')).strip()
                if not remark:
                    br_el = item.xpath('.//div[contains(@class, "icon-br")]//span')
                    if br_el:
                        remark = ''.join(br_el[0].xpath('.//text()')).strip()
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
        items = self._parse_list(html) if html else []
        return {"class": self.categories, "list": items[:30], "filters": {}}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        if page == 1:
            url = f"/list/{tid}.html"
        else:
            url = f"/list/{tid}-{page}.html"
        html = self._fetch(url)
        items = self._parse_list(html) if html else []
        pagecount = page
        if html:
            tree = etree.HTML(html)
            page_links = tree.xpath('//div[contains(@class, "pagination")]//a')
            for a in page_links:
                text = a.text.strip() if a.text else ''
                if text.isdigit():
                    num = int(text)
                    if num > pagecount:
                        pagecount = num
        return {"page": page, "pagecount": pagecount, "limit": 36, "total": 9999, "list": items}

    def detailContent(self, ids):
        result = {"list": []}
        raw_id = ids[0].strip()
        m = re.search(r'(\d+)', raw_id)
        if not m:
            return result
        vid = m.group(1)
        url = f"/detail/{vid}.html"
        html = self._fetch(url)
        if not html:
            return result
        tree = etree.HTML(html)
        title = ''.join(tree.xpath('//h1/text()')).strip()
        if not title:
            title = ''.join(tree.xpath('//title/text()')).strip()
        pic = tree.xpath('//div[contains(@class, "detail-poster")]//img/@data-original')
        if not pic:
            pic = tree.xpath('//div[contains(@class, "detail-poster")]//img/@src')
        pic = self._fix(pic[0]) if pic else ''
        pic = self._proxy_img(pic)
        content = ''.join(tree.xpath('//div[contains(@class, "detail-content")]/text()')).strip()
        if not content:
            meta = tree.xpath('//meta[@name="description"]/@content')
            if meta:
                content = meta[0]
        director = ''
        actor = ''
        info_items = tree.xpath('//div[contains(@class, "detail-info")]//li')
        for li in info_items:
            text = ''.join(li.xpath('.//text()')).strip()
            if '导演' in text:
                director = text.replace('导演：', '').replace('导演', '').strip()
            elif '主演' in text:
                actor = text.replace('主演：', '').replace('主演', '').strip()
        play_from = []
        play_urls = []
        line_tabs = tree.xpath('//ul[contains(@class, "detail-playfrom-list")]/li')
        line_names = []
        for li in line_tabs:
            name = ''.join(li.xpath('.//text()')).strip()
            if name:
                line_names.append(name)
        panels = tree.xpath('//div[contains(@class, "detail-play-panel")]')
        for idx, panel in enumerate(panels):
            eps = []
            for a in panel.xpath('.//a[contains(@href, "/play/")]'):
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
            for a in tree.xpath('//a[contains(@href, "/play/")]'):
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
        url = f"/search/-------------.html?wd={keyword}&page={page}"
        html = self._fetch(url)
        items = self._parse_list(html) if html else []
        return {"list": items, "page": page, "pagecount": 1, "limit": 36, "total": len(items)}

    def playerContent(self, flag, id, vipFlags):
        url = id if id.startswith('http') else self.host + id
        html = self._fetch(url)
        if not html:
            return {"parse": 1, "url": url, "header": self.headers}
        m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\});', html, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                play_url = data.get('url', '')
                if play_url:
                    return {"parse": 0, "url": self._fix(play_url), "header": self.headers}
            except:
                pass
        m = re.search(r'<video[^>]+src="([^"]+)"', html)
        if m:
            return {"parse": 0, "url": self._fix(m.group(1)), "header": self.headers}
        m = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if m:
            iframe_url = self._fix(m.group(1))
            iframe_html = self._fetch(iframe_url)
            if iframe_html:
                m2 = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', iframe_html)
                if m2:
                    return {"parse": 0, "url": self._fix(m2.group(1)), "header": self.headers}
            return {"parse": 1, "url": iframe_url, "header": self.headers}
        m = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
        if m:
            return {"parse": 0, "url": self._fix(m.group(1)), "header": self.headers}
        return {"parse": 1, "url": url, "header": self.headers}
