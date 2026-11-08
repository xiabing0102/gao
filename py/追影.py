import requests
from bs4 import BeautifulSoup
import re
from base.spider import Spider
import sys
import json
import base64
import urllib.parse
import hashlib
import time
from urllib.parse import urljoin

sys.path.append('..')

xurl = "https://zhuiying1.cc"
headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36',
    'Referer': xurl,
}


class Spider(Spider):
    global xurl
    global headerx

    def getName(self):
        return "首页"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def homeContent(self, filter):
        class_items = [
            {"type_id": "dianying", "type_name": "电影"},
            {"type_id": "dianshiju", "type_name": "电视剧"},
            {"type_id": "zongyi", "type_name": "综艺"},
            {"type_id": "dongman", "type_name": "动漫"},
            {"type_id": "duanju", "type_name": "短剧"}
        ]

        static_filters = {
            "dianying": [
            {"key":"type","name":"类型","value":[{"n":"全部","v":""},{"n":"科幻","v":"科幻"},{"n":"剧情","v":"剧情"},{"n":"惊悚","v":"惊悚"},{"n":"爱情","v":"爱情"},{"n":"古装","v":"古装"},{"n":"动作","v":"动作"},{"n":"悬疑","v":"悬疑"},{"n":"犯罪","v":"犯罪"},{"n":"谍战","v":"谍战"},{"n":"历史","v":"历史"},{"n":"喜剧","v":"喜剧"},{"n":"奇幻","v":"奇幻"},{"n":"家庭","v":"家庭"},{"n":"青春","v":"青春"},{"n":"冒险","v":"冒险"},{"n":"纪录","v":"纪录"},{"n":"动画","v":"动画"},{"n":"人物","v":"人物"},{"n":"文化","v":"文化"},{"n":"其他","v":"其他"}]},
            {"key":"area","name":"地区","value":[{"n":"全部","v":""},{"n":"大陆","v":"中国大陆"},{"n":"香港","v":"中国香港"},{"n":"台湾","v":"中国台湾"},{"n":"美国","v":"美国"},{"n":"日本","v":"日本"},{"n":"韩国","v":"韩国"},{"n":"德国","v":"德国"},{"n":"泰国","v":"泰国"},{"n":"英国","v":"英国"},{"n":"法国","v":"法国"},{"n":"意大利","v":"意大利"},{"n":"西班牙","v":"西班牙"}]},
            {"key":"year","name":"年代","value":[{"n":"全部","v":""},{"n":"2026","v":"2026"},{"n":"2025","v":"2025"},{"n":"2024","v":"2024"},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2018","v":"2018"},{"n":"2017","v":"2017"},{"n":"2016","v":"2016"},{"n":"2015","v":"2015"},{"n":"2014","v":"2014"},{"n":"2013","v":"2013"},{"n":"2012","v":"2012"},{"n":"2011","v":"2011"},{"n":"2010","v":"2010"}]},
            {"key":"by","name":"排序","value":[{"n":"时间","v":"time"},{"n":"人气","v":"hits_week"},{"n":"评分","v":"douban_score"}]}
        ],
        "dianshiju": [
            {"key":"type","name":"类型","value":[{"n":"全部","v":""},{"n":"爱情","v":"爱情"},{"n":"古装","v":"古装"},{"n":"悬疑","v":"悬疑"},{"n":"都市","v":"都市"},{"n":"喜剧","v":"喜剧"},{"n":"战争","v":"战争"},{"n":"剧情","v":"剧情"},{"n":"青春","v":"青春"},{"n":"历史","v":"历史"},{"n":"网剧","v":"网剧"},{"n":"奇幻","v":"奇幻"},{"n":"冒险","v":"冒险"},{"n":"励志","v":"励志"},{"n":"犯罪","v":"犯罪"},{"n":"商战","v":"商战"},{"n":"恐怖","v":"恐怖"},{"n":"穿越","v":"穿越"},{"n":"农村","v":"农村"},{"n":"人物","v":"人物"},{"n":"商业","v":"商业"},{"n":"生活","v":"生活"},{"n":"其他","v":"其他"}]},
            {"key":"area","name":"地区","value":[{"n":"全部","v":""},{"n":"内地","v":"中国大陆"},{"n":"香港","v":"中国香港"},{"n":"台湾","v":"中国台湾"},{"n":"美国","v":"美国"},{"n":"日本","v":"日本"},{"n":"韩国","v":"韩国"},{"n":"德国","v":"德国"},{"n":"泰国","v":"泰国"},{"n":"英国","v":"英国"},{"n":"法国","v":"法国"},{"n":"新加坡","v":"新加坡"},{"n":"其他","v":"其他"}]},
            {"key":"year","name":"年代","value":[{"n":"全部","v":""},{"n":"2026","v":"2026"},{"n":"2025","v":"2025"},{"n":"2024","v":"2024"},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2018","v":"2018"},{"n":"2017","v":"2017"},{"n":"2016","v":"2016"},{"n":"2015","v":"2015"},{"n":"2014","v":"2014"},{"n":"2013","v":"2013"},{"n":"2012","v":"2012"},{"n":"2011","v":"2011"},{"n":"2010","v":"2010"}]},
            {"key":"by","name":"排序","value":[{"n":"时间","v":"time"},{"n":"人气","v":"hits_week"},{"n":"评分","v":"douban_score"}]}
        ],
        "zongyi": [
            {"key":"type","name":"类型","value":[{"n":"全部","v":""},{"n":"真人秀","v":"真人秀"},{"n":"脱口秀","v":"脱口秀"},{"n":"喜剧","v":"喜剧"},{"n":"音乐","v":"音乐"},{"n":"爱情","v":"爱情"},{"n":"家庭","v":"家庭"},{"n":"歌舞","v":"歌舞"}]},
            {"key":"area","name":"地区","value":[{"n":"全部","v":""},{"n":"内地","v":"中国大陆"},{"n":"港台","v":"港台"},{"n":"欧美","v":"欧美"},{"n":"韩国","v":"韩国"},{"n":"其他","v":"其他"}]},
            {"key":"year","name":"年代","value":[{"n":"全部","v":""},{"n":"2026","v":"2026"},{"n":"2025","v":"2025"},{"n":"2024","v":"2024"},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2018","v":"2018"},{"n":"2017","v":"2017"},{"n":"2016","v":"2016"},{"n":"2015","v":"2015"},{"n":"2014","v":"2014"},{"n":"2013","v":"2013"},{"n":"2012","v":"2012"},{"n":"2011","v":"2011"},{"n":"2010","v":"2010"}]},
            {"key":"by","name":"排序","value":[{"n":"时间","v":"time"},{"n":"人气","v":"hits_week"},{"n":"评分","v":"douban_score"}]}
        ],
        "dongman": [
            {"key":"type","name":"类型","value":[{"n":"全部","v":""},{"n":"少年","v":"少年"},{"n":"热血","v":"热血"},{"n":"科幻","v":"科幻"},{"n":"冒险","v":"冒险"},{"n":"动画","v":"动画"},{"n":"爱情","v":"爱情"},{"n":"奇幻","v":"奇幻"},{"n":"武侠","v":"武侠"},{"n":"悬疑","v":"悬疑"},{"n":"惊悚","v":"惊悚"},{"n":"剧情","v":"剧情"},{"n":"音乐","v":"音乐"},{"n":"恐怖","v":"恐怖"},{"n":"喜剧","v":"喜剧"},{"n":"儿童","v":"儿童"}]},
            {"key":"area","name":"地区","value":[{"n":"全部","v":""},{"n":"国产","v":"中国大陆"},{"n":"欧美","v":"欧美"},{"n":"日本","v":"日本"},{"n":"其他","v":"其他"}]},
            {"key":"year","name":"年代","value":[{"n":"全部","v":""},{"n":"2026","v":"2026"},{"n":"2025","v":"2025"},{"n":"2024","v":"2024"},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2018","v":"2018"},{"n":"2017","v":"2017"},{"n":"2016","v":"2016"},{"n":"2015","v":"2015"},{"n":"2014","v":"2014"},{"n":"2013","v":"2013"},{"n":"2012","v":"2012"},{"n":"2011","v":"2011"},{"n":"2010","v":"2010"}]},
            {"key":"by","name":"排序","value":[{"n":"时间","v":"time"},{"n":"人气","v":"hits_week"},{"n":"评分","v":"douban_score"}]}
        ],
        "duanju": [
            {"key":"type","name":"类型","value":[{"n":"全部","v":""},{"n":"重生民国","v":"重生民国"},{"n":"穿越年代","v":"穿越年代"},{"n":"古装仙侠","v":"古装仙侠"},{"n":"AI漫剧","v":"AI漫剧"},{"n":"都市脑洞","v":"都市脑洞"},{"n":"现代言情","v":"现代言情"},{"n":"反转爽文","v":"反转爽文"},{"n":"女恋总裁","v":"女恋总裁"},{"n":"闪婚离婚","v":"闪婚离婚"}]},
            {"key":"area","name":"地区","value":[{"n":"全部","v":""},{"n":"中国大陆","v":"中国大陆"}]},
            {"key":"year","name":"年代","value":[{"n":"全部","v":""},{"n":"2026","v":"2026"},{"n":"2025","v":"2025"},{"n":"2024","v":"2024"},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2018","v":"2018"},{"n":"2017","v":"2017"},{"n":"2016","v":"2016"},{"n":"2015","v":"2015"},{"n":"2014","v":"2014"},{"n":"2013","v":"2013"},{"n":"2012","v":"2012"},{"n":"2011","v":"2011"},{"n":"2010","v":"2010"}]},
            {"key":"by","name":"排序","value":[{"n":"综合排序","v":"time"},{"n":"热度最高","v":"hits_week"},{"n":"最新上线","v":"id"},{"n":"最好评","v":"douban_score"}]}
        ]
        }

        return {
            "class": class_items,
            "filters": static_filters
        }

    def homeVideoContent(self):
        try:
            resp = requests.get(url=xurl, headers=headerx, timeout=10)
            resp.raise_for_status()
            源码 = BeautifulSoup(resp.text, "lxml")
            videos = []
            卡片列表 = 源码.select('a.card.js-card-item')
            for 卡片 in 卡片列表:
                标题标签 = 卡片.select_one('.card-title')
                标题 = 标题标签.get_text(strip=True) if 标题标签 else ''
                链接 = urljoin(xurl, 卡片.get('href', ''))
                img = 卡片.select_one('.card-cover img')
                图片 = img.get('src', '') if img else ''
                if 图片.startswith('//'):
                    图片 = 'https:' + 图片
                elif 图片 and not 图片.startswith('http'):
                    图片 = urljoin(xurl, 图片)
                副标题标签 = 卡片.select_one('.card-status')
                副标题 = 副标题标签.get_text(strip=True) if 副标题标签 else ""
                if 标题 and 链接:
                    video = {
                        "vod_id": 链接,
                        "vod_name": 标题,
                        "vod_pic": 图片,
                        "vod_remarks": 副标题
                    }
                    videos.append(video)
            return {'list': videos}
        except Exception as e:
            return {'list': []}

    def categoryContent(self, cid, pg, filter, ext):
        try:
            page = int(pg) if pg else 1
            cateId = cid
            area = urllib.parse.quote(ext.get('area', '')) if ext else ''
            by = urllib.parse.quote(ext.get('by', '')) if ext else ''
            class_ = urllib.parse.quote(ext.get('type', '')) if ext else ''
            lang = urllib.parse.quote(ext.get('lang', '')) if ext else ''
            letter = ''
            year = urllib.parse.quote(ext.get('year', '')) if ext else ''
            url = f"{xurl}/vodshow/{cateId}-{area}-{by}-{class_}-{lang}-{letter}---{page}---{year}.html"
            resp = requests.get(url, headers=headerx, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')
            videos = []
            卡片列表 = soup.select('a.card.js-card-item')
            for 卡片 in 卡片列表:
                标题标签 = 卡片.select_one('.card-title')
                标题 = 标题标签.get_text(strip=True) if 标题标签 else ''
                链接 = urljoin(xurl, 卡片.get('href', ''))
                img = 卡片.select_one('.card-cover img')
                图片 = img.get('src', '') if img else ''
                if 图片.startswith('//'):
                    图片 = 'https:' + 图片
                elif 图片 and not 图片.startswith('http'):
                    图片 = urljoin(xurl, 图片)
                副标题标签 = 卡片.select_one('.card-status')
                副标题 = 副标题标签.get_text(strip=True) if 副标题标签 else ""
                if 标题 and 链接:
                    video = {
                        "vod_id": 链接,
                        "vod_name": 标题,
                        "vod_pic": 图片,
                        "vod_remarks": 副标题
                    }
                    videos.append(video)
            return {
                'list': videos,
                'page': page,
                'pagecount': 9999,
                'limit': 30,
                'total': 999999
            }
        except Exception as e:
            return {'list': [], 'page': pg, 'pagecount': 0, 'limit': 30, 'total': 0}

    def detailContent(self, ids):
        did = ids[0]
        if not did.startswith('http'):
            did = urljoin(xurl, did)
        try:
            resp = requests.get(url=did, headers=headerx, timeout=10)
            resp.raise_for_status()
            源码 = BeautifulSoup(resp.text, "lxml")
            vod = {}
            vod["vod_id"] = did
            h1标签 = 源码.select_one('h1.detail-title') or 源码.find('h1')
            vod["vod_name"] = h1标签.get_text(strip=True) if h1标签 else ""
            年份标签 = 源码.select_one('.detail-year')
            if 年份标签:
                年份匹配 = re.search(r'\d{4}', 年份标签.get_text())
                vod["vod_year"] = 年份匹配.group(0) if 年份匹配 else ""
            else:
                vod["vod_year"] = ""
            类型元素 = None
            for item in 源码.select('.hero-meta-matrix .matrix-item'):
                lbl = item.find(class_='m-lbl')
                if lbl and '类型' in lbl.get_text():
                    val = item.find(class_='m-val')
                    类型元素 = val
                    break
            vod["type_name"] = 类型元素.get_text(strip=True) if 类型元素 else ""
            地区元素 = None
            for item in 源码.select('.hero-meta-matrix .matrix-item'):
                lbl = item.find(class_='m-lbl')
                if lbl and ('地区' in lbl.get_text() or '制片国家' in lbl.get_text()):
                    val = item.find(class_='m-val')
                    地区元素 = val
                    break
            vod["vod_area"] = 地区元素.get_text(strip=True) if 地区元素 else ""
            封面图标签 = 源码.select_one('.detail-poster-wrap img') or 源码.select_one('.detail-poster')
            if 封面图标签:
                封面图 = 封面图标签.get('src', '').strip()
                if 封面图.startswith('//'):
                    封面图 = 'https:' + 封面图
                elif 封面图 and not 封面图.startswith('http'):
                    封面图 = urljoin(xurl, 封面图)
            else:
                封面图 = ''
            vod["vod_pic"] = 封面图
            导演元素 = None
            for item in 源码.select('.cast-info .actor-line'):
                label = item.find(class_='label')
                if label and '导演' in label.get_text():
                    导演元素 = item
                    break
            if 导演元素:
                val = 导演元素.find(class_='val') or 导演元素.find(class_='actor-val-box')
                vod["vod_director"] = val.get_text(strip=True) if val else ""
            else:
                vod["vod_director"] = ""
            演员元素 = None
            for item in 源码.select('.cast-info .actor-line'):
                label = item.find(class_='label')
                if label and '主演' in label.get_text():
                    演员元素 = item
                    break
            if 演员元素:
                val = 演员元素.find(class_='val') or 演员元素.find(class_='actor-val-box')
                vod["vod_actor"] = val.get_text(strip=True) if val else ""
            else:
                vod["vod_actor"] = ""
            简介元素 = 源码.select_one('.synopsis-text')
            vod["vod_content"] = 简介元素.get_text(strip=True) if 简介元素 else ""
            # 提取备注（如更新至第04集）
            badge = 源码.select_one('.poster-badge')
            vod["vod_remarks"] = badge.get_text(strip=True) if badge else ""
            ktabs = []
            线路数组 = 源码.select('.source-tab .tab-name')
            for XL in 线路数组:
                线路标题 = XL.get_text(strip=True)
                if 线路标题 and 线路标题 not in ktabs:
                    ktabs.append(线路标题)
            vod["vod_play_from"] = '$$$'.join(ktabs) if ktabs else ""
            klists = []
            播放数组 = 源码.select('.ep-square-list')
            for BF in 播放数组:
                播放列表 = BF.select('a.ep-item-square')
                klist = []
                for LB in 播放列表:
                    播放标题 = LB.get('data-name', '').strip() or LB.get_text(strip=True)
                    播放链接 = LB.get('href', '')
                    if 播放标题 and 播放链接:
                        剧集 = f'{播放标题}${播放链接}'
                        klist.append(剧集)
                if klist:
                    klists.append('#'.join(klist))
            vod["vod_play_url"] = '$$$'.join(klists) if klists else ""
 
            for f in ['vod_name', 'vod_pic', 'type_name', 'vod_area', 'vod_year',
                      'vod_remarks', 'vod_director', 'vod_actor', 'vod_content',
                      'vod_play_from', 'vod_play_url']:
                if f not in vod:
                    vod[f] = ''
            return {'list': [vod]}
        except Exception as e:
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        try:
            播放链接 = id if id.startswith('http') else urljoin(xurl, id)
            if any(ext in 播放链接.lower() for ext in ['.m3u8', '.mp4', '.flv']):
                return {"parse": 0, "url": 播放链接, "header": json.dumps(headerx)}

            resp = requests.get(播放链接, headers=headerx, timeout=10)
            resp.encoding = resp.apparent_encoding or 'utf-8'
            html = resp.text

            m = re.search(r'MAC_PLAY_CONFIG\s*=\s*(\{[\s\S]*?\});', html)
            if m:
                raw = m.group(1)
                cfg = json.loads(re.sub(r'([{,]\s*)([a-zA-Z_]\w*)\s*:', r'\1"\2":', raw))
                base_key = cfg.get('baseKey', '')
                req_url = cfg.get('requestUrl', '')
                if base_key and req_url:
                    ts = str(int(time.time()))
                    ua = headerx.get('User-Agent', '')
                    token = hashlib.md5((base_key + ts + ua).encode()).hexdigest()
                    api = urljoin(xurl, '/player_api.php')
                    r = requests.post(api, data={'url': req_url, 'timestamp': ts, 'token': token},
                                      headers=headerx, timeout=15)
                    data = r.json()
                    if not data.get('error') and data.get('data'):
                        enc = data['data']
                        rev = enc[::-1]
                        pad = 0
                        while rev.startswith('='):
                            rev = rev[1:]
                            pad += 1
                        rev += '=' * pad
                        dec = json.loads(urllib.parse.unquote(base64.b64decode(rev).decode('latin-1')))
                        real = dec.get('jmurl', '')
                        if real:
                            is_direct = any(ext in real.lower() for ext in ['.m3u8', '.mp4', '.flv'])
                            return {"parse": 0 if is_direct else 1, "url": real, "header": json.dumps(headerx)}

            m = re.search(r'var\s+player_\w+\s*=\s*(\{.*?\})\s*;', html, re.DOTALL)
            if m:
                try:
                    d = json.loads(re.sub(r',\s*}', '}', m.group(1)))
                    u = d.get('url', '')
                    if u:
                        return {"parse": 0 if any(ext in u.lower() for ext in ['.m3u8', '.mp4']) else 1,
                                "url": u, "header": json.dumps(headerx)}
                except:
                    pass

            m = re.search(r'["\']url["\']\s*:\s*["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', html, re.I)
            if m:
                return {"parse": 0, "url": m.group(1), "header": json.dumps(headerx)}

            soup = BeautifulSoup(html, 'lxml')
            iframe = soup.select_one('iframe')
            if iframe and iframe.get('src'):
                src = iframe.get('src')
                if not src.startswith('http'):
                    src = urljoin(播放链接, src)
                return {"parse": 1, "url": src, "header": json.dumps(headerx)}

            return {"parse": 1, "url": 播放链接, "header": json.dumps(headerx)}

        except Exception as e:
            return {"parse": 1, "url": urljoin(xurl, id), "header": json.dumps(headerx)}

    def searchContentPage(self, key, quick, page):
        try:
            if not page:
                page = '1'
            if page == '1':
                url = f'{xurl}/vod/search/wd/{urllib.parse.quote(key)}.html'
            else:
                url = f'{xurl}/vod/search/page/{page}/wd/{urllib.parse.quote(key)}.html'
            resp = requests.get(url=url, headers=headerx, timeout=10)
            resp.raise_for_status()
            源码 = BeautifulSoup(resp.text, "lxml")
            videos = []
            卡片列表 = 源码.select('div.search-list-card')
            for 卡片 in 卡片列表:
                a标签 = 卡片.select_one('a.list-card-thumb')
                if not a标签:
                    continue
                标题标签 = 卡片.select_one('h4.list-title a')
                标题 = 标题标签.get_text(strip=True) if 标题标签 else ''
                链接 = urljoin(xurl, a标签.get('href', ''))
                img = a标签.select_one('img') or 卡片.find('img')
                图片 = img.get('src', '') if img else ''
                if 图片.startswith('//'):
                    图片 = 'https:' + 图片
                elif 图片 and not 图片.startswith('http'):
                    图片 = urljoin(xurl, 图片)
                副标题标签 = a标签.select_one('span.list-thumb-remark')
                副标题 = 副标题标签.get_text(strip=True) if 副标题标签 else ""
                if 标题 and 链接:
                    video = {
                        "vod_id": 链接,
                        "vod_name": 标题,
                        "vod_pic": 图片,
                        "vod_remarks": 副标题
                    }
                    videos.append(video)
            return {
                'list': videos,
                'page': page,
                'pagecount': 60,
                'limit': 30,
                'total': 999999
            }
        except Exception as e:
            return {'list': [], 'page': page, 'pagecount': 0, 'limit': 30, 'total': 0}

    def searchContent(self, key, quick, page='1'):
        return self.searchContentPage(key, quick, page)

    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params) if hasattr(self, 'proxyM3u8') else None
        elif params['type'] == "media":
            return self.proxyMedia(params) if hasattr(self, 'proxyMedia') else None
        elif params['type'] == "ts":
            return self.proxyTs(params) if hasattr(self, 'proxyTs') else None
        return None