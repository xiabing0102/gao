# -*- coding: utf-8 -*-
import re, json, urllib.parse
from lxml import etree
from base.spider import Spider as BaseSpider

class Spider(BaseSpider):
    def init(self, extend=""):
        self.host = "https://www.xieyiwh.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.host + "/"
        }
        self.categories = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "20", "type_name": "短剧"},
            {"type_id": "36", "type_name": "动画片"},
        ]

    def getName(self):
        return '花花影院'

    def _fetch(self, url):
        if not url.startswith('http'):
            url = self.host + url
        rsp = self.fetch(url, headers=self.headers)
        return rsp.text if rsp else ''

    def _fix_pic(self, u):
        if not u: return ''
        if u.startswith('//'): return 'https:' + u
        return u.replace('&amp;', '&')

    def _parse_list(self, html):
        if not html: return []
        tree = etree.HTML(html)
        results, seen = [], set()
        items = tree.xpath('//div[contains(@class,"stui-vodlist__box")]//a[contains(@class,"stui-vodlist__thumb")]')
        for item in items:
            try:
                href = item.get('href', '')
                m = re.search(r'/voddetail/(\d+)\.html', href)
                if not m or m.group(1) in seen:
                    continue
                seen.add(m.group(1))
                pic = item.get('data-original', '') or item.get('src', '')
                pic = self._fix_pic(pic)
                title = item.get('title', '') or ''
                remark = item.xpath('.//span[contains(@class,"pic-text")]/text()')
                remark = remark[0].strip() if remark else ''
                results.append({
                    "vod_id": m.group(1),
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
        items = []
        for box in tree.xpath('//div[contains(@class,"stui-vodlist__box")]'):
            a = box.xpath('.//a[contains(@class,"stui-vodlist__thumb")]')
            if not a: continue
            a = a[0]
            href = a.get('href', '')
            m = re.search(r'/voddetail/(\d+)\.html', href)
            if not m: continue
            vid = m.group(1)
            pic = a.get('data-original', '') or a.get('src', '')
            pic = self._fix_pic(pic)
            title = a.get('title', '') or ''
            items.append({"vod_id": vid, "vod_name": title, "vod_pic": pic})
        return {"class": self.categories, "list": items[:20], "filters": {}}

    def categoryContent(self, tid, pg, filter, extend):
        url = f"/vodshow/{tid}--------{pg}---.html"
        html = self._fetch(url)
        items = self._parse_list(html)
        pagecount = int(pg)
        if html:
            tree = etree.HTML(html)
            last = tree.xpath('//li[contains(@class,"active")]/following-sibling::li[last()]/a/text()')
            if last:
                try:
                    pagecount = int(last[0].strip())
                except:
                    pass
        return {"page": int(pg), "pagecount": pagecount, "limit": 36, "total": 9999, "list": items}

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0].split(',')[0].strip()
        try:
            html = self._fetch(f'/voddetail/{vid}.html')
            if not html: return result
            tree = etree.HTML(html)
            # 标题
            name = ''.join(tree.xpath('//div[contains(@class,"stui-content__detail")]//h1/text()')).strip()
            if not name:
                name = ''.join(tree.xpath('//h1/text()')).strip()
            # 图片
            pic = tree.xpath('//div[contains(@class,"stui-content__thumb")]//img/@data-original')
            if not pic:
                pic = tree.xpath('//div[contains(@class,"stui-content__thumb")]//img/@src')
            pic = self._fix_pic(pic[0]) if pic else ''
            # 导演、演员、简介
            director = ''
            actor = ''
            content = ''
            info_items = tree.xpath('//div[contains(@class,"stui-content__detail")]//p')
            for p in info_items:
                text = ''.join(p.xpath('.//text()')).strip()
                if '导演：' in text:
                    director = text.replace('导演：', '').strip()
                elif '主演：' in text or '演员：' in text:
                    actor = text.replace('主演：', '').replace('演员：', '').strip()
            content_el = tree.xpath('//div[contains(@class,"stui-content__detail")]//span[contains(@class,"detail-content")]')
            if content_el:
                content = ''.join(content_el[0].xpath('.//text()')).strip()
            # 提取播放列表 - 修正选择器
            play_from = []
            play_url = []
            # 查找所有播放列表容器（可能有多个线路，但当前页面通常只有一个）
            playlist_uls = tree.xpath('//ul[contains(@class,"stui-content__playlist")]')
            if not playlist_uls:
                # 兜底：查找任何包含播放链接的ul
                playlist_uls = tree.xpath('//div[contains(@class,"stui-content__playlist")]//ul')
            # 线路名称：取上方h3或tab标题，如果没有则默认"高清云播"
            line_names = []
            for ul in playlist_uls:
                # 尝试找前一个兄弟或父级中的标题
                parent = ul.getparent()
                if parent is not None:
                    h3 = parent.xpath('.//h3[@class="title"]/text()')
                    if h3:
                        line_names.append(h3[0].strip())
                    else:
                        line_names.append("高清云播")
                else:
                    line_names.append("高清云播")
            # 如果线路名称数量不匹配，补齐
            if len(line_names) < len(playlist_uls):
                for i in range(len(playlist_uls) - len(line_names)):
                    line_names.append(f"线路{len(line_names)+1}")
            # 处理每个播放列表
            for idx, ul in enumerate(playlist_uls):
                eps = []
                for a in ul.xpath('.//li/a'):
                    href = a.get('href', '')
                    title_ep = ''.join(a.xpath('.//text()')).strip()
                    if href and title_ep:
                        eps.append(f"{title_ep}${href}")
                if eps:
                    play_from.append(line_names[idx] if idx < len(line_names) else f"线路{idx+1}")
                    play_url.append('#'.join(eps))
            result["list"].append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_director": director,
                "vod_actor": actor,
                "vod_content": content,
                "vod_play_from": "$$$".join(play_from),
                "vod_play_url": "$$$".join(play_url)
            })
        except Exception as e:
            print(f"detail error: {e}")
        return result

    def searchContent(self, key, quick, pg="1"):
        try:
            decoded = urllib.parse.unquote(key)
        except:
            decoded = key
        url = f"/vodsearch/-------------.html?wd={urllib.parse.quote(decoded)}&page={pg}"
        html = self._fetch(url)
        items = self._parse_list(html)
        return {"list": items, "page": int(pg), "pagecount": 1, "limit": 36, "total": len(items)}

    def playerContent(self, flag, id, vipFlags):
        url = id if id.startswith('http') else self.host + id
        html = self._fetch(url)
        if not html:
            return {"parse": 0, "url": url, "header": json.dumps(self.headers)}
        patterns = [
            r'var\s+now\s*=\s*["\']([^"\']+)["\']',
            r'var\s+player_data\s*=\s*(\{.*?\})',
            r'url:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
            r'(https?://[^\s"\']+\.mp4[^\s"\']*)',
        ]
        play_url = ''
        for pat in patterns:
            m = re.search(pat, html, re.S)
            if m:
                val = m.group(1)
                if '.m3u8' not in val and '.mp4' not in val and '{' in val:
                    try:
                        pd = json.loads(val)
                        play_url = pd.get('url', '')
                    except:
                        pass
                else:
                    play_url = val
                break
        if play_url:
            return {"parse": 0, "url": self._fix_pic(play_url), "header": json.dumps(self.headers)}
        return {"parse": 1, "url": url}
