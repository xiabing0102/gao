import requests
from bs4 import BeautifulSoup
import re
import sys
import json
import urllib.parse
from base.spider import Spider
from urllib.parse import urljoin

sys.path.append('..')

xurl = "https://www.hamp4.com"
headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; M2102J2SC Build/TKQ1.221114.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/144.0.7559.31 Mobile Safari/537.36',
    'Referer': xurl,
}

class Spider(Spider):
    def getName(self):
        return "影视天下"

    def init(self, extend):
        pass

    def homeContent(self, filter):
        class_items = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "剧集"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "4", "type_name": "动漫"}
        ]
        static_filters = {
            "1": [
                {"key": "cateId", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "动作片", "v": "5"}, {"n": "喜剧片", "v": "6"}, {"n": "爱情片", "v": "7"}, {"n": "科幻片", "v": "8"}, {"n": "恐怖片", "v": "9"}, {"n": "剧情片", "v": "10"}, {"n": "战争片", "v": "11"}]},
                {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"}, {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"}, {"n": "法国", "v": "法国"}, {"n": "英国", "v": "英国"}, {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"}, {"n": "泰国", "v": "泰国"}, {"n": "印度", "v": "印度"}, {"n": "西班牙", "v": "西班牙"}, {"n": "加拿大", "v": "加拿大"}, {"n": "俄罗斯", "v": "俄罗斯"}, {"n": "新加坡", "v": "新加坡"}, {"n": "其它", "v": "其它"}]},
                {"key": "year", "name": "年代", "value": [{"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"}, {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"}, {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"}, {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"}]},
                {"key": "lang", "name": "语言", "value": [{"n": "全部", "v": ""}, {"n": "国语", "v": "国语"}, {"n": "英语", "v": "英语"}, {"n": "粤语", "v": "粤语"}, {"n": "韩语", "v": "韩语"}, {"n": "日语", "v": "日语"}, {"n": "法语", "v": "法语"}, {"n": "德语", "v": "德语"}, {"n": "其它", "v": "其它"}]},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "time"}, {"n": "热门", "v": "hits"}]}
            ],
            "2": [
                {"key": "cateId", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "国产剧", "v": "12"}, {"n": "港台剧", "v": "13"}, {"n": "欧美剧", "v": "14"}, {"n": "日韩剧", "v": "15"}, {"n": "海外剧", "v": "16"}]},
                {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"}, {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"}, {"n": "法国", "v": "法国"}, {"n": "英国", "v": "英国"}, {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"}, {"n": "泰国", "v": "泰国"}, {"n": "印度", "v": "印度"}, {"n": "西班牙", "v": "西班牙"}, {"n": "加拿大", "v": "加拿大"}, {"n": "俄罗斯", "v": "俄罗斯"}, {"n": "新加坡", "v": "新加坡"}, {"n": "其它", "v": "其它"}]},
                {"key": "year", "name": "年代", "value": [{"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"}, {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"}, {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"}, {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"}]},
                {"key": "lang", "name": "语言", "value": [{"n": "全部", "v": ""}, {"n": "国语", "v": "国语"}, {"n": "英语", "v": "英语"}, {"n": "粤语", "v": "粤语"}, {"n": "韩语", "v": "韩语"}, {"n": "日语", "v": "日语"}, {"n": "法语", "v": "法语"}, {"n": "德语", "v": "德语"}, {"n": "其它", "v": "其它"}]},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "time"}, {"n": "热门", "v": "hits"}]}
            ],
            "3": [
                {"key": "cateId", "name": "类型", "value": [{"n": "全部", "v": ""}]},
                {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"}, {"n": "美国", "v": "美国"}, {"n": "台湾", "v": "台湾"}, {"n": "韩国", "v": "韩国"}, {"n": "日本", "v": "日本"}]},
                {"key": "year", "name": "年代", "value": [{"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"}, {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"}, {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"}, {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"}]},
                {"key": "lang", "name": "语言", "value": [{"n": "全部", "v": ""}, {"n": "国语", "v": "国语"}, {"n": "英语", "v": "英语"}, {"n": "粤语", "v": "粤语"}, {"n": "韩语", "v": "韩语"}, {"n": "日语", "v": "日语"}]},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "time"}, {"n": "热门", "v": "hits"}]}
            ],
            "4": [
                {"key": "cateId", "name": "类型", "value": [{"n": "全部", "v": ""}]},
                {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"}, {"n": "美国", "v": "美国"}, {"n": "台湾", "v": "台湾"}, {"n": "韩国", "v": "韩国"}, {"n": "日本", "v": "日本"}]},
                {"key": "year", "name": "年代", "value": [{"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"}, {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"}, {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"}, {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"}]},
                {"key": "lang", "name": "语言", "value": [{"n": "全部", "v": ""}, {"n": "国语", "v": "国语"}, {"n": "英语", "v": "英语"}, {"n": "粤语", "v": "粤语"}, {"n": "韩语", "v": "韩语"}, {"n": "日语", "v": "日语"}]},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "time"}, {"n": "热门", "v": "hits"}]}
            ]
        }
        return {
            "class": class_items,
            "filters": static_filters
        }

    def _fetch_html(self, url):
        resp = requests.get(url, headers=headers, timeout=10)
        encoding = resp.apparent_encoding or 'utf-8'
        if encoding.lower() == 'gb2312':
            encoding = 'gbk'
        resp.encoding = encoding
        return resp.text

    def _get_soup(self, url):
        return BeautifulSoup(self._fetch_html(url), 'lxml')

    def _parse_video_items(self, soup):
        videos = []
        seen_ids = set()
        for item in soup.select('.stui-vodlist__box'):
            a_tag = item.select_one('a')
            if not a_tag:
                continue
            href = a_tag.get('href', '')
            if not href:
                continue
            vod_id = href if href.startswith('http') else urljoin(xurl, href)
            if vod_id in seen_ids:
                continue
            seen_ids.add(vod_id)
            title = a_tag.get('title', '').strip()
            if not title:
                title = a_tag.get_text(strip=True)
            if not title:
                img = item.select_one('img')
                title = img.get('alt', '').strip() if img else ''
            if not title:
                continue
            pic = a_tag.get('data-src') or a_tag.get('data-original') or a_tag.get('src', '')
            if not pic:
                img = item.select_one('img')
                pic = img.get('data-src') or img.get('data-original') or img.get('src', '') if img else ''
            if pic.startswith('//'):
                pic = 'https:' + pic
            elif pic and not pic.startswith('http'):
                pic = urljoin(xurl, pic)
            remark_span = item.select_one('.pic-text')
            remark = remark_span.get_text(strip=True) if remark_span else ''
            videos.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark
            })
        return videos

    def homeVideoContent(self):
        return {'list': self._parse_video_items(self._get_soup(xurl))}

    def categoryContent(self, cid, pg, filter, ext):
        page = int(pg) if pg else 1
        if ext and 'cateId' in ext:
            cateId = ext['cateId']
        else:
            cateId = str(cid)
        area = urllib.parse.quote(ext.get('area', ''), safe='') if ext else ''
        by = urllib.parse.quote(ext.get('by', ''), safe='') if ext else ''
        class_ = urllib.parse.quote(ext.get('class', ''), safe='') if ext else ''
        lang = urllib.parse.quote(ext.get('lang', ''), safe='') if ext else ''
        letter = urllib.parse.quote(ext.get('letter', ''), safe='') if ext else ''
        year = urllib.parse.quote(ext.get('year', ''), safe='') if ext else ''
        url = f"{xurl}/show/{cateId}-{area}-{by}-{class_}-{lang}-{letter}---{page}---{year}.html"
        soup = self._get_soup(url)
        videos = self._parse_video_items(soup)
        return {
            'list': videos,
            'page': page,
            'pagecount': 9999,
            'limit': 30,
            'total': 999999
        }

    def detailContent(self, ids):
        did = ids[0]
        if not did.startswith('http'):
            did = urljoin(xurl, did)
        soup = self._get_soup(did)
        vod = {"vod_id": did}
        title_elem = soup.select_one('h1') or soup.select_one('.stui-content__detail .title')
        vod["vod_name"] = title_elem.get_text(strip=True) if title_elem else ''
        img = soup.select_one('.stui-content__thumb img') or soup.select_one('.pic img')
        if img:
            pic = img.get('data-original', '') or img.get('src', '') or img.get('data-src', '')
            if pic.startswith('//'):
                pic = 'https:' + pic
            elif pic and not pic.startswith('http'):
                pic = urljoin(xurl, pic)
            vod["vod_pic"] = pic
        else:
            vod["vod_pic"] = ''
        content_elem = soup.select_one('.detail-content') or soup.select_one('.detail-sketch')
        if content_elem:
            paragraphs = content_elem.find_all('p')
            if paragraphs:
                raw = ' '.join([p.get_text(strip=True) for p in paragraphs])
            else:
                raw = content_elem.get_text(strip=True)
            vod["vod_content"] = raw.replace('展开全部', '').strip()
        else:
            vod["vod_content"] = ''
        vod["type_name"] = vod["vod_area"] = vod["vod_year"] = vod["vod_remarks"] = vod["vod_director"] = vod["vod_actor"] = ''
        for p in soup.select('.stui-content__detail p'):
            text = p.get_text(strip=True)
            if not text:
                continue
            matches = re.findall(r'(类型|分类|地区|国家|年份|年代|状态|更新|导演|主演|演员|简介|剧情)[：:]\s*(.+?)(?=\s*(?:类型|分类|地区|年份|年代|状态|更新|导演|主演|演员|简介|剧情)[：:]|$)', text)
            for key, value in matches:
                value = value.strip()
                links = p.find_all('a')
                if links and key in ('导演', '主演', '演员'):
                    names = [a.get_text(strip=True) for a in links if a.get_text(strip=True)]
                    if names:
                        value = '/'.join(names)
                elif key in ('导演', '主演', '演员'):
                    names = [n.strip() for n in re.split(r'[\s\xa0,，、]+', value) if n.strip()]
                    if names:
                        value = '/'.join(names)
                if key in ('类型', '分类'):
                    vod['type_name'] = value
                elif key in ('地区', '国家'):
                    vod['vod_area'] = value
                elif key in ('年份', '年代'):
                    vod['vod_year'] = value
                elif key in ('状态', '更新'):
                    vod['vod_remarks'] = value
                elif key == '导演':
                    vod['vod_director'] = value
                elif key in ('主演', '演员'):
                    vod['vod_actor'] = value
                elif key in ('简介', '剧情'):
                    if not vod.get('vod_content'):
                        vod['vod_content'] = value
        filter_lines = ['猜您喜欢', '同类型', '相关推荐']
        filter_titles = ['1080P', 'дрр滈凊']
        ktabs, klists, seen_lines = [], [], set()

        playlists = soup.select('.stui-vodlist__head h4')
        tab_items = soup.select('.stui-content__playlist')

        for idx, tab in enumerate(playlists):
            if idx >= len(tab_items):
                break
            span = tab.select_one('span')
            line_name = span.get_text(strip=True) if span else tab.get_text(strip=True)
            if not line_name:
                line_name = f'线路{idx + 1}'
            if line_name in filter_lines or line_name in seen_lines:
                continue
            episode_links = tab_items[idx].select('li a')
            if not episode_links:
                continue
            klist = []
            for ep in episode_links:
                ep_name = ep.get_text(strip=True)
                ep_link = ep.get('href', '')
                if ep_name in filter_titles or not ep_name or not ep_link:
                    continue
                klist.append(f'{ep_name}${ep_link}')
            if klist:
                seen_lines.add(line_name)
                ktabs.append(line_name)
                klists.append('#'.join(klist))

        vod["vod_play_from"] = '$$$'.join(ktabs) if ktabs else ''
        vod["vod_play_url"] = '$$$'.join(klists) if klists else ''

        required_fields = ['vod_name', 'vod_pic', 'type_name', 'vod_area', 'vod_year', 'vod_remarks',
                           'vod_director', 'vod_actor', 'vod_content', 'vod_play_from', 'vod_play_url']
        for field in required_fields:
            if field not in vod:
                vod[field] = ''

        return {'list': [vod]}

    def playerContent(self, flag, id, vipFlags):
        try:
            play_url = id if id.startswith(('http://', 'https://')) else urljoin(xurl, id)
            html = self._fetch_html(play_url)
            video_url = ''
            m = re.search(r'var\s+player_\w+\s*=\s*(\{.*?\})\s*;?\s*</script>', html, re.DOTALL)
            if m:
                try:
                    json_str = re.sub(r',\s*}', '}', m.group(1))
                    data = json.loads(json_str)
                    enc = data.get('url', '')
                    if enc:
                        video_url = enc
                except:
                    pass
            if not video_url:
                m = re.search(r'["\']url["\']\s*:\s*["\'](https?://[^"\']+\.(?:m3u8|mp4|mkv|flv|ts)[^"\']*)["\']', html, re.I)
                if m:
                    video_url = m.group(1)
            if not video_url:
                soup = BeautifulSoup(html, 'lxml')
                iframe = soup.select_one('iframe')
                if iframe and iframe.get('src'):
                    video_url = urljoin(play_url, iframe.get('src'))
            if video_url:
                parse = 0 if re.search(r'\.(m3u8|mp4|mkv|flv|ts)(\?|$)', video_url, re.I) else 1
                if parse:
                    video_url = play_url
            else:
                parse = 1
                video_url = play_url
            return {"parse": parse, "playUrl": "", "url": video_url, "header": json.dumps(headers)}
        except Exception as e:
            print(f"player error: {e}")
            return {"parse": 1, "playUrl": "", "url": urljoin(xurl, id), "header": json.dumps(headers)}

    def searchContent(self, key, quick, page='1'):
        page = int(page) if page else 1
        encoded_key = urllib.parse.quote(key, safe='')
        url = f"{xurl}/search/{encoded_key}----------{page}---.html"
        soup = self._get_soup(url)
        videos = self._parse_video_items(soup)
        return {
            'list': videos,
            'page': page,
            'pagecount': 60,
            'limit': 30,
            'total': 999999
        }
