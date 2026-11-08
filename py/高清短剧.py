# -*- coding: utf-8 -*-
# 高清短剧（indymoms.com）· TVBox 爬虫源
# CMS: 苹果CMS v10
# 分类: 重生/穿越/爽剧/言情/都市/古装/悬疑/剧情
# 支持: 分类浏览 + 年份筛选 + 排序 + 搜索 + 播放解析

import sys
sys.path.append('..')
from base.spider import Spider as BaseSpider

import re
import requests
from urllib.parse import quote


BASE_URL = "https://www.indymoms.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": BASE_URL + "/",
}


class Spider(BaseSpider):
    """高清短剧 TVBox 爬虫"""

    # 分类映射（type_id -> (名称, tid)）
    CATE_MAP = {
        "1": ("重生", 1),
        "2": ("穿越", 2),
        "3": ("爽剧", 3),
        "4": ("言情", 4),
        "5": ("都市", 5),
        "6": ("古装", 6),
        "7": ("悬疑", 7),
        "8": ("剧情", 8),
    }

    # 年份筛选
    YEARS = ["2025", "2024", "2023", "2022", "2021",
             "2020", "2019", "2018", "2017", "2016", "2015", "2014"]

    # 排序方式
    ORDERS = {
        "time": "按时间",
        "hit": "按人气",
        "commend": "按推荐",
    }

    def __init__(self):
        super().__init__()
        self.name = "高清短剧"
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def init(self, extend=""):
        pass

    def getName(self):
        return self.name

    def isVideoFormat(self, url):
        if not url:
            return False
        video_exts = ['.m3u8', '.mp4', '.flv', '.mkv', '.avi', '.ts', '.mpg']
        return any(ext in url.lower() for ext in video_exts)

    def manualVideoCheck(self):
        return False

    # ==================== 工具方法 ====================
    def _get(self, url, timeout=15):
        """安全 GET 请求"""
        try:
            r = self.session.get(url, timeout=timeout, allow_redirects=True)
            r.encoding = 'utf-8'
            return r.text if r.status_code == 200 else ""
        except Exception as e:
            print(f"[高清短剧] GET {url} 失败: {e}")
            return ""

    def _clean(self, s):
        """清洗 HTML 标签"""
        if not s:
            return ""
        s = re.sub(r'<[^>]+>', '', s)
        s = s.replace('&nbsp;', ' ').replace('&amp;', '&')
        s = s.replace('&lt;', '<').replace('&gt;', '>')
        s = s.replace('&quot;', '"').replace('&#39;', "'")
        s = s.replace('&ldquo;', '“').replace('&rdquo;', '”')
        s = s.replace('&hellip;', '…').replace('&mdash;', '—')
        return s.strip()

    def _fix_pic(self, url):
        """修正图片 URL"""
        if not url:
            return ""
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('/'):
            return BASE_URL + url
        return url

    def _extract_field(self, html, labels):
        """通用字段提取"""
        for label in labels:
            patterns = [
                rf'<(?:span|strong|em|label)[^>]*>\s*{label}\s*[：:]\s*</(?:span|strong|em|label)>\s*'
                rf'((?:<a[^>]*>[^<]*</a>\s*)+)',
                rf'<(?:span|strong|em|label|li|p|div|a)[^>]*>\s*{label}\s*[：:]\s*([^<]+)</(?:span|strong|em|label|li|p|div|a)>',
                rf'{label}\s*[：:]\s*((?:<a[^>]*>[^<]*</a>|[^<\n])+)',
            ]
            for pat in patterns:
                m = re.search(pat, html, re.S | re.I)
                if m:
                    raw = m.group(1)
                    names = re.findall(r'<a[^>]*>([^<]+)</a>', raw)
                    if names:
                        return ','.join(n.strip() for n in names if n.strip())
                    cleaned = self._clean(raw)
                    cleaned = cleaned.split('\n')[0].strip()
                    if cleaned and cleaned not in ['', '未知', '暂无']:
                        return cleaned
        return ""

    def _extract_meta(self, html, name):
        """从 meta 标签提取信息"""
        patterns = [
            rf'<meta[^>]*property="og:{name}"[^>]*content="([^"]*)"',
            rf'<meta[^>]*name="{name}"[^>]*content="([^"]*)"',
            rf'<meta[^>]*content="([^"]*)"[^>]*property="og:{name}"',
            rf'<meta[^>]*content="([^"]*)"[^>]*name="{name}"',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.I)
            if m:
                return self._clean(m.group(1))
        return ""

    # ==================== 首页 ====================
    def homeContent(self, filter):
        """返回分类列表 + 筛选器"""
        classes = []
        for tid, (name, _) in self.CATE_MAP.items():
            classes.append({'type_id': tid, 'type_name': name})

        result = {'class': classes}

        if filter:
            filters = {}
            for tid in self.CATE_MAP.keys():
                filters[tid] = [
                    {
                        "key": "year",
                        "name": "年份",
                        "value": [{"n": "全部", "v": ""}] +
                                 [{"n": y, "v": y} for y in self.YEARS]
                    },
                    {
                        "key": "order",
                        "name": "排序",
                        "value": [{"n": v, "v": k} for k, v in self.ORDERS.items()]
                    }
                ]
            result['filters'] = filters

        return result

    def homeVideoContent(self):
        """首页推荐（取穿越分类第一页）"""
        try:
            html = self._get(f"{BASE_URL}/gaoqing/2.html")
            return {'list': self._parse_list(html)}
        except Exception as e:
            print(f"[高清短剧] homeVideoContent: {e}")
            return {'list': []}

    # ==================== 列表解析 ====================
    def _parse_list(self, html):
        """解析视频列表 HTML（苹果CMS 通用结构）"""
        videos = []
        if not html:
            return videos

        pattern = re.compile(
            r'<a[^>]*class="fed-list-pics[^"]*"[^>]*'
            r'href="(/duanju/(\d+)\.html)"[^>]*'
            r'(?:data-original|src)="([^"]*)"[^>]*'
            r'title="([^"]*)"[^>]*>.*?'
            r'<span class="fed-list-remarks[^"]*">([^<]*)</span>',
            re.S | re.I
        )
        for m in pattern.finditer(html):
            href, vid, pic, title, remark = m.groups()
            videos.append({
                "vod_id": vid,
                "vod_name": title.strip(),
                "vod_pic": self._fix_pic(pic),
                "vod_remarks": remark.strip() if remark else "",
            })

        if not videos:
            pattern2 = re.compile(
                r'<a[^>]*href="/duanju/(\d+)\.html"[^>]*title="([^"]*)"[^>]*>.*?'
                r'(?:data-original|src)="([^"]*)"',
                re.S | re.I
            )
            seen = set()
            for m in pattern2.finditer(html):
                vid, title, pic = m.groups()
                if vid in seen:
                    continue
                seen.add(vid)
                videos.append({
                    "vod_id": vid,
                    "vod_name": title.strip(),
                    "vod_pic": self._fix_pic(pic),
                    "vod_remarks": "",
                })

        if not videos:
            pattern3 = re.compile(
                r'<a[^>]*href="/duanju/(\d+)\.html"[^>]*title="([^"]*)"',
                re.S
            )
            seen = set()
            for vid, title in pattern3.findall(html):
                if vid in seen:
                    continue
                seen.add(vid)
                videos.append({
                    "vod_id": vid,
                    "vod_name": title.strip(),
                    "vod_pic": "",
                    "vod_remarks": "",
                })

        return videos

    # ==================== 分类 ====================
    def categoryContent(self, tid, pg, filter, extend):
        """分类页内容（支持年份+排序筛选）"""
        try:
            tid = str(tid)
            pg = int(pg) if pg else 1

            if tid not in self.CATE_MAP:
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 30, 'total': 0}

            _, tid_num = self.CATE_MAP[tid]

            year = extend.get("year", "") if extend else ""
            order = extend.get("order", "") if extend else ""

            if year or order:
                url = f"{BASE_URL}/search.php?page={pg}&searchtype=5&tid={tid_num}"
                if year:
                    url += f"&year={year}"
                if order:
                    url += f"&order={order}"
            else:
                if pg == 1:
                    url = f"{BASE_URL}/gaoqing/{tid_num}.html"
                else:
                    url = f"{BASE_URL}/gaoqing/{tid_num}-{pg}.html"

            html = self._get(url)
            videos = self._parse_list(html)

            has_next = False
            if html:
                if re.search(rf'{pg + 1}\.html', html) or '下页' in html:
                    has_next = True

            return {
                'list': videos,
                'page': pg,
                'pagecount': pg + 1 if has_next else pg,
                'limit': 30,
                'total': 999999,
            }
        except Exception as e:
            print(f"[高清短剧] categoryContent: {e}")
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 0, 'total': 0}

    # ==================== 详情 ====================
    def detailContent(self, array):
        """详情页解析（含演员/导演/剧情/分类等元数据）"""
        try:
            tid = array[0] if array else ""
            if not tid:
                return {'list': []}

            url = f"{BASE_URL}/duanju/{tid}.html"
            html = self._get(url)
            if not html:
                return {'list': []}

            # ---------- 标题 ----------
            title_m = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
            if not title_m:
                title_m = re.search(r'<title>([^<]+)</title>', html)
            title = self._clean(title_m.group(1)).split('-')[0] if title_m else tid

            # ---------- 图片 ----------
            pic_m = re.search(r'<img[^>]*class="[^"]*(?:pic|poster|thumb)[^"]*"[^>]*src="([^"]*)"', html)
            if not pic_m:
                pic_m = re.search(r'<img[^>]*src="([^"]*)"[^>]*class="[^"]*(?:pic|poster|thumb)[^"]*"', html)
            if not pic_m:
                pic_m = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]*)"', html)
            pic = self._fix_pic(pic_m.group(1)) if pic_m else ""

            # ---------- 元数据 ----------
            info_area = html
            info_m = re.search(
                r'<div[^>]*class="[^"]*(?:fed-detail-info|detail-info|stui-content__detail|module-info|info)[^"]*"[^>]*>(.*?)</div>\s*</div>',
                html, re.S | re.I
            )
            if info_m:
                info_area = info_m.group(1)

            actor = self._extract_field(info_area, ["主演", "演员", "主演明星"]) or \
                    self._extract_field(html, ["主演", "演员"])
            director = self._extract_field(info_area, ["导演"]) or \
                       self._extract_field(html, ["导演"])
            type_name = self._extract_field(info_area, ["类型", "分类", "频道"]) or \
                        self._extract_field(html, ["类型", "分类"])
            year = self._extract_field(info_area, ["年份", "年代", "上映"]) or \
                   self._extract_field(html, ["年份", "年代"])
            area = self._extract_field(info_area, ["地区", "国家", "产地"]) or \
                   self._extract_field(html, ["地区", "国家"])
            lang = self._extract_field(info_area, ["语言", "对白"]) or \
                   self._extract_field(html, ["语言"])

            remarks = self._extract_field(info_area, ["状态", "更新", "备注"])
            if not remarks:
                remarks_m = re.search(r'<span[^>]*class="[^"]*remarks[^"]*"[^>]*>([^<]*)</span>', html, re.I)
                remarks = self._clean(remarks_m.group(1)) if remarks_m else ""

            # ---------- 剧情介绍（重点修复）----------
            desc = self._extract_desc(html)

            # ---------- 播放列表 ----------
            play_from = []
            play_url = []

            play_area = html
            play_list_m = re.search(
                r'<ul[^>]*class="[^"]*(?:fed-play|playlist|play-list|stui-content__playlist|content__playlist)[^"]*"[^>]*>(.*?)</ul>',
                html, re.S | re.I
            )
            if play_list_m:
                play_area = play_list_m.group(1)
            else:
                play_div_m = re.search(
                    r'<div[^>]*class="[^"]*(?:fed-play|playlist|play-list|stui-content__playlist|playlist-content|content__playlist)[^"]*"[^>]*>(.*?)</div>',
                    html, re.S | re.I
                )
                if play_div_m:
                    play_area = play_div_m.group(1)

            plays = re.findall(
                r'<a[^>]*href="(/play/(\d+)-(\d+)-(\d+)\.html)"[^>]*>([^<]+)</a>',
                play_area, re.S
            )

            if not plays:
                all_plays = re.findall(
                    r'<a[^>]*href="(/play/(\d+)-(\d+)-(\d+)\.html)"[^>]*>([^<]+)</a>',
                    html, re.S
                )
                plays = []
                for href, vid, sid, eid, ep_name in all_plays:
                    if '立即播放' in ep_name or '立即' in ep_name:
                        continue
                    plays.append((href, vid, sid, eid, ep_name))

            if plays:
                sources = {}
                for href, vid, sid, eid, ep_name in plays:
                    src_name = f"线路{sid}"
                    if src_name not in sources:
                        sources[src_name] = []
                    ep = f"{ep_name.strip()}${href}"
                    if ep not in sources[src_name]:
                        sources[src_name].append(ep)

                for src_name in sources:
                    sources[src_name].sort(key=lambda x: self._extract_ep_num(x))

                for src_name, eps in sources.items():
                    play_from.append(src_name)
                    play_url.append('#'.join(eps))

            if not play_from:
                m3u8_m = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', html)
                if m3u8_m:
                    play_from = ["默认"]
                    play_url = [f"正片${m3u8_m.group(1)}"]

            vod = {
                "vod_id": tid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_content": desc,
                "vod_play_from": '$$$'.join(play_from) if play_from else "默认",
                "vod_play_url": '$$$'.join(play_url) if play_url else "",
                "vod_actor": actor,
                "vod_director": director,
                "vod_type": type_name,
                "vod_year": year,
                "vod_area": area,
                "vod_lang": lang,
                "vod_remarks": remarks,
            }
            return {'list': [vod]}
        except Exception as e:
            print(f"[高清短剧] detailContent: {e}")
            return {'list': []}

    def _extract_desc(self, html):
        """
        专门提取剧情介绍，多重策略兜底
        """
        # 策略1：优先定位"剧情介绍"标签后的内容块
        # 苹果CMS常见结构：<div class="fed-pannel"><div class="fed-pannel-head"><h2>剧情介绍</h2></div><div class="fed-pannel-body">内容</div></div>
        desc_label_patterns = [
            # "剧情介绍"标题后面的内容块
            r'剧情介绍\s*[:：]?\s*</[^>]+>\s*<[^>]+[^>]*>(.*?)</(?:div|p|span)>',
            # <h2>剧情介绍</h2> 后跟内容
            r'<h[1-6][^>]*>\s*(?:剧情介绍|剧情简介|内容简介|简介|剧情)\s*</h[1-6]>\s*'
            r'(?:</div>)?\s*<div[^>]*>(.*?)</div>',
            # 标签为"剧情介绍："后直接跟内容
            r'(?:剧情介绍|剧情简介|内容简介)\s*[：:]\s*(.*?)</(?:div|p|span|li)>',
        ]
        for pat in desc_label_patterns:
            m = re.search(pat, html, re.S | re.I)
            if m:
                desc = self._clean(m.group(1))
                if desc and len(desc) > 5 and '剧情' not in desc[:6]:
                    return desc

        # 策略2：定位包含"剧情"相关 class 的容器
        desc_class_patterns = [
            r'<div[^>]*class="[^"]*(?:fed-detail-content|detail-content|stui-content__desc|module-info-introduction|introduction|plot|desc-content|vod-content|content-desc)[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*id="[^"]*(?:desc|content|detail|introduction|plot)[^"]*"[^>]*>(.*?)</div>',
            r'<span[^>]*class="[^"]*(?:fed-detail-content|detail-content|desc|content|introduction)[^"]*"[^>]*>(.*?)</span>',
            r'<p[^>]*class="[^"]*(?:desc|content|detail|introduction|plot)[^"]*"[^>]*>(.*?)</p>',
        ]
        for pat in desc_class_patterns:
            m = re.search(pat, html, re.S | re.I)
            if m:
                desc = self._clean(m.group(1))
                # 过滤掉明显的导航/标签内容
                if desc and len(desc) > 10 and not self._is_noise(desc):
                    return desc

        # 策略3：meta description（og:description 优先）
        desc = self._extract_meta(html, "description")
        if desc and len(desc) > 5 and not self._is_noise(desc):
            return desc

        desc = self._extract_meta(html, "og:description")
        if desc and len(desc) > 5 and not self._is_noise(desc):
            return desc

        # 策略4：全局兜底 - 找页面中最大段的文本
        # 尝试匹配详情区域中的长文本
        long_text_patterns = [
            r'<div[^>]*class="[^"]*(?:fed-pannel-body|pannel-body|panel-body|module-content)[^"]*"[^>]*>(.*?)</div>',
            r'<article[^>]*>(.*?)</article>',
        ]
        for pat in long_text_patterns:
            m = re.search(pat, html, re.S | re.I)
            if m:
                desc = self._clean(m.group(1))
                if desc and len(desc) > 15 and not self._is_noise(desc):
                    return desc

        return ""

    def _is_noise(self, text):
        """判断提取的文本是否是噪音（导航、标签等）"""
        if not text:
            return True
        noise_keywords = [
            '首页', '分类', '搜索', '登录', '注册', '版权', '友情链接',
            'Copyright', '©', 'APP', '下载', '导航', '菜单',
        ]
        # 如果包含多个噪音关键词，判定为噪音
        count = sum(1 for kw in noise_keywords if kw in text)
        if count >= 3:
            return True
        # 如果文本太短且不含中文句子特征
        if len(text) < 15:
            return True
        return False

    def _extract_ep_num(self, ep_str):
        """从剧集字符串中提取集数用于排序"""
        try:
            m = re.search(r'第(\d+)集', ep_str)
            if m:
                return int(m.group(1))
            m = re.search(r'(\d+)', ep_str)
            if m:
                return int(m.group(1))
        except:
            pass
        return 0

    # ==================== 搜索 ====================
    def searchContent(self, key, quick, pg="1"):
        """搜索（苹果CMS 标准接口 /search.php?searchword=xxx）"""
        try:
            url = f"{BASE_URL}/search.php?searchword={quote(key)}&page={pg}"
            html = self._get(url)
            return {'list': self._parse_list(html)}
        except Exception as e:
            print(f"[高清短剧] searchContent: {e}")
            return {'list': []}

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags):
        """播放解析"""
        try:
            if id.startswith('http'):
                url = id
            elif id.startswith('/'):
                url = BASE_URL + id
            else:
                if re.match(r'^\d+$', id):
                    url = f"{BASE_URL}/play/{id}-1-1.html"
                else:
                    url = f"{BASE_URL}/play/{id}"

            html = self._get(url)
            if not html:
                return {"parse": 1, "url": url, "header": HEADERS}

            m3u8_m = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', html)
            if m3u8_m:
                return {
                    "parse": 0,
                    "url": m3u8_m.group(1),
                    "header": {"User-Agent": HEADERS["User-Agent"], "Referer": BASE_URL}
                }

            mp4_m = re.search(r'["\'](https?://[^"\']+\.mp4[^"\']*)["\']', html)
            if mp4_m:
                return {
                    "parse": 0,
                    "url": mp4_m.group(1),
                    "header": {"User-Agent": HEADERS["User-Agent"], "Referer": BASE_URL}
                }

            iframe_m = re.search(r'<iframe[^>]*src="([^"]*)"', html)
            if iframe_m:
                real = iframe_m.group(1)
                if real.startswith('//'):
                    real = 'https:' + real
                elif real.startswith('/'):
                    real = BASE_URL + real
                if '.m3u8' in real or '.mp4' in real:
                    return {"parse": 0, "url": real, "header": HEADERS}
                return {"parse": 1, "url": real, "header": HEADERS}

            return {"parse": 1, "url": url, "header": HEADERS}
        except Exception as e:
            print(f"[高清短剧] playerContent: {e}")
            return {"parse": 1, "url": id, "header": HEADERS}


# ==================== TVBox 标准入口 ====================
def get_spider():
    return Spider()