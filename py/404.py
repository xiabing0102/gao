# coding=utf-8
# !/usr/bin/python
import re
import sys
import requests
import random
import html
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from base.spider import Spider

sys.path.append('..')

class Spider(Spider):

    def getName(self):
        return "404自动挡"

    def init(self, extend):
        self.xurl = self.get_domain()
        self.ua = "Mozilla/5.0 (Linux; Android 16; 2510DRK44C Build/BP2A.250605.031.A3; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.192 Mobile Safari/537.36"
        self.headerx = {
            "User-Agent": self.ua,
            "Origin": self.xurl,
            "Referer": self.xurl + "/",
        }
        self.filter_cache = {}

    def get_domain(self):
        prefix = ''.join(random.choices('0123456789', k=3))
        suffixes = []
        try:
            pub_url = "https://404xav.github.io/url8/"
            res = requests.get(pub_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            text = res.text
            urls_match = re.search(r"const\s+urls\s*=\s*\[([^\]]+)\]", text, re.DOTALL)
            if urls_match:
                urls_block = urls_match.group(1)
                found = re.findall("https://([^'\"\\s,]+)", urls_block)
                for domain in found:
                    domain = domain.strip("'\"\\,")
                    if domain and '.' in domain and domain not in suffixes:
                        suffixes.append(domain)
        except Exception:
            pass

        fallback_suffixes = ['4042604.one', '4042604.pro']
        for fs in fallback_suffixes:
            if fs not in suffixes:
                suffixes.append(fs)

        suffixes = suffixes[:2]
        domains = [f"https://{prefix}.{s}" for s in suffixes]

        for domain in domains:
            try:
                r = requests.get(domain, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                if r.status_code == 200 and len(r.text) > 100:
                    return domain
            except Exception:
                continue

        return f"https://{prefix}.4042604.one"

    def _req(self, url):
        try:
            headers = self.headerx.copy()
            headers["Referer"] = self.xurl + "/"
            res = requests.get(url=url, headers=headers, timeout=15)
            res.encoding = "utf-8"
            return res.text
        except Exception:
            return ""

    def _get_title(self, page_url):
        """从详情页提取标题（仅用于展示，不用于播放）"""
        try:
            page_html = self._req(page_url)
            title_match = re.search(r'<title>(.*?)</title>', page_html)
            if title_match:
                title = re.sub(r'[\s\u200b]+', '', title_match.group(1)).split('|')[0].strip()
                return html.unescape(title)
        except Exception:
            pass
        return ""

    def fix_url(self, url):
        url = html.unescape((url or "").strip())
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return self.xurl + url
        return self.xurl + "/" + url

    def _paged_url(self, href, page):
        page = int(page) if page else 1
        url = self.fix_url(href)
        if page <= 1 or not url:
            return url
        if re.search(r'/list/[^/]+/[^/]+/\d+\.html$', url):
            return re.sub(r'/\d+\.html$', f'/{page}.html', url)
        if re.search(r'/search/[^/]+/.+/\d+\.html$', url):
            return re.sub(r'/\d+\.html$', f'/{page}.html', url)
        if url.endswith('.html'):
            return url[:-5] + f'/{page}.html'
        return url.rstrip('/') + f'/{page}.html'

    def parse_filters(self, body, cid):
        groups = []
        try:
            doc = BeautifulSoup(body, "lxml")
            box = doc.find('div', class_='web_api_types')
            if not box:
                return groups
            for idx, ul in enumerate(box.find_all('ul')[:2]):
                key = 'cate' if idx == 0 else 'tag'
                name = '分类' if idx == 0 else '标签'
                values = [{"n": "全部", "v": ""}]
                seen = set()
                for a in ul.find_all('a', href=True):
                    href = html.unescape(a.get('href', '')).strip()
                    title = html.unescape(a.get_text(' ', strip=True)).strip()
                    if not href or not title or href in seen:
                        continue
                    if f'/list/{cid}/' not in href and f'/search/{cid}/' not in href:
                        continue
                    seen.add(href)
                    values.append({"n": title, "v": href})
                if len(values) > 1:
                    groups.append({"key": key, "name": name, "value": values[:31]})
        except Exception as e:
            print(f"[{self.getName()}] 错误: 筛选解析失败 - {e}")
        return groups

    def build_filters(self, classes):
        result = {}
        tasks = []
        def load_filter(item):
            cid = item.get('type_id', '')
            if cid in self.filter_cache:
                return cid, self.filter_cache[cid]
            body = self._req(f"{self.xurl}/list/{cid}/0/1.html")
            groups = self.parse_filters(body, cid)
            self.filter_cache[cid] = groups
            return cid, groups
        try:
            with ThreadPoolExecutor(max_workers=8) as executor:
                for item in classes:
                    tasks.append(executor.submit(load_filter, item))
                for task in as_completed(tasks):
                    try:
                        cid, groups = task.result()
                        if groups:
                            result[cid] = groups
                    except Exception:
                        continue
        except Exception as e:
            print(f"[{self.getName()}] 错误: 筛选加载失败 - {e}")
        return result

    def parse_movies(self, body):
        videos = []
        seen = set()
        try:
            doc = BeautifulSoup(body, "lxml")
            grid = doc.find('div', class_='web_grid_box')
            cells = grid.find_all('div', class_='cell_box') if grid else []
            if not cells:
                cells = doc.find_all('div', class_='cell_box')
            for cell in cells:
                try:
                    a_tag = None
                    thumb = cell.find('div', class_='v_thumb')
                    if thumb:
                        a_tag = thumb.find('a', href=True)
                    if not a_tag:
                        a_tag = cell.find('a', href=True)
                    if not a_tag:
                        continue
                    full_href = self.fix_url(a_tag.get('href', ''))
                    if not full_href or full_href in seen:
                        continue
                    seen.add(full_href)
                    title_div = cell.find('div', class_='v_title')
                    img = cell.find('img')
                    name = title_div.get_text(' ', strip=True) if title_div else (a_tag.get('title', '') or (img.get('alt', '') if img else ''))
                    pic = ''
                    if img:
                        pic = self.fix_url(img.get('data-original', '') or img.get('data-src', '') or img.get('src', ''))
                    time_div = cell.find('div', class_='v_time')
                    remark = time_div.get_text(' ', strip=True) if time_div else ''
                    videos.append({"vod_id": full_href, "vod_name": html.unescape(name), "vod_pic": pic, "vod_remarks": remark})
                except Exception:
                    continue
            if not videos:
                for a_tag in doc.select('a[href*="/detail/"]'):
                    try:
                        full_href = self.fix_url(a_tag.get('href', ''))
                        if not full_href or full_href in seen:
                            continue
                        seen.add(full_href)
                        img = a_tag.find('img')
                        name = a_tag.get('title', '') or (img.get('alt', '') if img else '') or a_tag.get_text(' ', strip=True)
                        pic = self.fix_url(img.get('data-original', '') or img.get('data-src', '') or img.get('src', '')) if img else ''
                        if name:
                            videos.append({"vod_id": full_href, "vod_name": html.unescape(name), "vod_pic": pic, "vod_remarks": ""})
                    except Exception:
                        continue
        except Exception as e:
            print(f"[{self.getName()}] 错误: 影片解析失败 - {e}")
        return videos

    def homeVideoContent(self):
        return {"list": []}

    def homeContent(self, filter):
        result = {
            "class": [
                {"type_id": "xvweb", "type_name": "xvideos"},
                {"type_id": "xnweb", "type_name": "xnxx"},
                {"type_id": "cangku", "type_name": "仓库资源"},
                {"type_id": "91web", "type_name": "91资源"},
                {"type_id": "91cnweb", "type_name": "91资源cn"},
                {"type_id": "aiwu", "type_name": "原创资源"},
                {"type_id": "jipinvip", "type_name": "极品资源"},
                {"type_id": "ckbh", "type_name": "百货仓库"},
                {"type_id": "ckll", "type_name": "伦理资源"},
                {"type_id": "hsckzy", "type_name": "HSCK资源"},
                {"type_id": "heiliao", "type_name": "黑料资源"},
                {"type_id": "dnzzy", "type_name": "大奶子资源"},
                {"type_id": "fqzy", "type_name": "番茄资源"},
                {"type_id": "yellowzy", "type_name": "黄色资源"},
                {"type_id": "sex8", "type_name": "杏吧资源"},
                {"type_id": "thzy", "type_name": "桃花资源"},
                {"type_id": "xbao", "type_name": "细胞资源"},
                {"type_id": "1mzy", "type_name": "百万资源"},
                {"type_id": "fhzy", "type_name": "番号资源"},
                {"type_id": "laosebi", "type_name": "色P资源"},
                {"type_id": "155zy", "type_name": "155资源"},
                {"type_id": "yutu", "type_name": "玉兔资源"},
                {"type_id": "jkun", "type_name": "jkun资源"},
                {"type_id": "senlin", "type_name": "森林资源"},
                {"type_id": "naixxzy", "type_name": "奶香香资源"},
                {"type_id": "dadizy", "type_name": "大地资源"},
                {"type_id": "lebo", "type_name": "乐播资源"},
                {"type_id": "lajiao", "type_name": "辣椒资源"},
                {"type_id": "didizy", "type_name": "滴滴资源"},
                {"type_id": "shayu", "type_name": "鲨鱼资源"},
                {"type_id": "jingpinx", "type_name": "精品X资源"},
                {"type_id": "xiaojizy", "type_name": "小鸡资源"},
                {"type_id": "doudou", "type_name": "豆豆资源"},
                {"type_id": "soavzy", "type_name": "SOAV资源"},
                {"type_id": "xiangjiao", "type_name": "香蕉资源"},
                {"type_id": "aosika", "type_name": "奥斯卡资源"},
                {"type_id": "msnzy", "type_name": "美少女资源"},
                {"type_id": "ysjzy", "type_name": "淫水机资源"},
                {"type_id": "xnezy", "type_name": "香奶儿资源"},
                {"type_id": "bpzy", "type_name": "白嫖资源"},
                {"type_id": "xsmzy", "type_name": "小湿妹资源"},
                {"type_id": "havzy", "type_name": "黄AV资源"},
            ],
            "list": [],
            "filters": {}
        }
        if filter:
            result["filters"] = self.build_filters(result["class"])
        return result

    def categoryContent(self, cid, pg, filter, ext):
        page = int(pg) if pg else 1
        try:
            ext = ext or {}
            href = ext.get('tag') or ext.get('cate') or ext.get('url') or ext.get('filter') or ''
            url = self._paged_url(href, page) if href else f"{self.xurl}/list/{cid}/0/{page}.html"
            body = self._req(url)
            videos = self.parse_movies(body)
            print(f"[{self.getName()}] 分类列表匹配到 {len(videos)} 个视频")
            return {'list': videos, 'page': page, 'pagecount': 9999, 'limit': 90, 'total': 999999}
        except Exception as e:
            print(f"[{self.getName()}] 错误: 分类爬取失败 - {e}")
            return {'list': [], 'page': page, 'pagecount': 1, 'limit': 90, 'total': 0}

    def detailContent(self, ids):
        did = ids[0]
        title = self._get_title(did)
        if not title:
            title = did.split('/')[-1].replace('.html', '') if '/' in did else did

        videos = [{
            "vod_id": did,
            "vod_name": title,
            "vod_pic": "",
            "type_name": "影片",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": title,
            "vod_play_from": "嗅探播放",
            "vod_play_url": f"正片${did}"
        }]
        return {"list": videos}

    def playerContent(self, flag, id, vipFlags):
        result = {}
        result["parse"] = 1
        result["playUrl"] = ""
        result["url"] = id
        result["header"] = {
            "User-Agent": self.ua,
            "Origin": self.xurl,
            "Referer": self.xurl + "/",
        }
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, page):
        url = f'{self.xurl}/search/cangku/{key}/{page}.html'
        html = self._req(url)
        videos = self.parse_movies(html)
        return {
            'list': videos,
            'page': page,
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }

    def localProxy(self, params):
        return None
