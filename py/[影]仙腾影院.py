# -*- coding: utf-8 -*-
# 仙腾影院 m.slwgb.com — OK影视 / TvBox Python 源
# 修复版 v4（2026-10-12）
#   1. 修复线路匹配：sid_expected = int(tab_id)（原 -1 是 bug）
#   2. 修复 fallback 无效 ID：___1___1（原 ___0___0）
#   3. 播放：直接返回 m3u8，绕过 iframe 解析器弹窗广告
#   4. 播放：根据播放域名动态设置 Referer
#   5. 海报文字：详情/列表备注来自 pic-text（更新至第X集/完结）
#   6. 字段：类型/地区/年份/主演/导演 用精确正则
#   7. 搜索：改用 /search/-------------.html?wd=

import sys
sys.path.append('..')
from base.spider import Spider
import json
import re
import html as html_mod
from urllib.parse import quote, unquote, urlparse
import time


def cache(ttl=300):
    def decorator(func):
        cache_data = {}
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            now = time.time()
            if key in cache_data:
                data, timestamp = cache_data[key]
                if now - timestamp < ttl:
                    return data
            result = func(*args, **kwargs)
            cache_data[key] = (result, now)
            return result
        return wrapper
    return decorator


class Spider(Spider):

    HOST = "https://m.slwgb.com"

    # 播放域名 → Referer 映射（防盗链）
    PLAY_REFERERS = {
        "fengbao":  "https://fengbao12.com/",
        "vipuuvip": "https://vip.vipuuvip.com/",
    }

    CATE = {
        "电影":   "dianying",
        "电视剧": "dianshiju",
        "综艺":   "zongyi",
        "动漫":   "dongman",
        "短剧":   "xiaoshipin",
    }

    SUB_CATE = {
        "dianying": [
            {"n": "全部", "v": ""}, {"n": "喜剧", "v": "喜剧"}, {"n": "爱情", "v": "爱情"},
            {"n": "恐怖", "v": "恐怖"}, {"n": "动作", "v": "动作"}, {"n": "科幻", "v": "科幻"},
            {"n": "剧情", "v": "剧情"}, {"n": "战争", "v": "战争"}, {"n": "警匪", "v": "警匪"},
            {"n": "犯罪", "v": "犯罪"}, {"n": "动画", "v": "动画"}, {"n": "奇幻", "v": "奇幻"},
            {"n": "武侠", "v": "武侠"}, {"n": "冒险", "v": "冒险"}, {"n": "枪战", "v": "枪战"},
            {"n": "悬疑", "v": "悬疑"}, {"n": "惊悚", "v": "惊悚"}, {"n": "经典", "v": "经典"},
            {"n": "青春", "v": "青春"}, {"n": "文艺", "v": "文艺"}, {"n": "微电影", "v": "微电影"},
            {"n": "古装", "v": "古装"}, {"n": "历史", "v": "历史"}, {"n": "运动", "v": "运动"},
            {"n": "农村", "v": "农村"}, {"n": "儿童", "v": "儿童"}, {"n": "网络电影", "v": "网络电影"},
        ],
        "dianshiju": [
            {"n": "全部", "v": ""}, {"n": "古装", "v": "古装"}, {"n": "战争", "v": "战争"},
            {"n": "青春偶像", "v": "青春偶像"}, {"n": "喜剧", "v": "喜剧"}, {"n": "家庭", "v": "家庭"},
            {"n": "犯罪", "v": "犯罪"}, {"n": "动作", "v": "动作"}, {"n": "奇幻", "v": "奇幻"},
            {"n": "剧情", "v": "剧情"}, {"n": "历史", "v": "历史"}, {"n": "经典", "v": "经典"},
            {"n": "乡村", "v": "乡村"}, {"n": "情景", "v": "情景"}, {"n": "商战", "v": "商战"},
            {"n": "网剧", "v": "网剧"}, {"n": "其他", "v": "其他"},
        ],
        "zongyi": [
            {"n": "全部", "v": ""}, {"n": "选秀", "v": "选秀"}, {"n": "美食", "v": "美食"},
            {"n": "旅游", "v": "旅游"}, {"n": "娱乐", "v": "娱乐"}, {"n": "生活", "v": "生活"},
            {"n": "脱口秀", "v": "脱口秀"}, {"n": "音乐", "v": "音乐"}, {"n": "时尚", "v": "时尚"},
            {"n": "访谈", "v": "访谈"}, {"n": "情感", "v": "情感"}, {"n": "游戏互动", "v": "游戏互动"},
            {"n": "晚会", "v": "晚会"}, {"n": "播报", "v": "播报"}, {"n": "其他", "v": "其他"},
        ],
        "dongman": [
            {"n": "全部", "v": ""}, {"n": "热血", "v": "热血"}, {"n": "科幻", "v": "科幻"},
            {"n": "搞笑", "v": "搞笑"}, {"n": "冒险", "v": "冒险"}, {"n": "校园", "v": "校园"},
            {"n": "动作", "v": "动作"}, {"n": "机战", "v": "机战"}, {"n": "运动", "v": "运动"},
            {"n": "战争", "v": "战争"}, {"n": "少年", "v": "少年"}, {"n": "少女", "v": "少女"},
            {"n": "社会", "v": "社会"}, {"n": "原创", "v": "原创"}, {"n": "亲子", "v": "亲子"},
            {"n": "益智", "v": "益智"}, {"n": "励志", "v": "励志"}, {"n": "其他", "v": "其他"},
        ],
        "xiaoshipin": [
            {"n": "全部", "v": ""}, {"n": "短剧", "v": "短剧"}, {"n": "微电影", "v": "微电影"},
        ],
    }

    YEAR_FILTERS = [
        {"n": "全部", "v": ""},
        {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"},
        {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"},
        {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"}, {"n": "2018", "v": "2018"},
        {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"}, {"n": "2015", "v": "2015"},
        {"n": "更早", "v": "2014"},
    ]

    UA = ("Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36")

    # ── 预编译正则 ──
    RE_THUMB      = re.compile(r'ewave-vodlist__thumb')
    RE_TITLE_ATTR = re.compile(r'title="([^"]*)"')
    RE_DATA_ORIG  = re.compile(r'data-original="([^"]*)"')
    RE_DATA_SRC   = re.compile(r'data-src="([^"]*)"')
    RE_BG = re.compile(r'background(?:-image)?\s*:\s*url\(\s*["\']?([^"\')]+)["\']?\s*\)', re.I)
    RE_PIC_TEXT   = re.compile(r'pic-text[^>]*>([^<]*)')
    RE_THUMB_LINK = re.compile(r'thumb-link[^>]*href="([^"]*)"')
    RE_ANY_HREF   = re.compile(r'href="([^"]*\.html)"')
    RE_TEXT_ITEM  = re.compile(
        r'top-line-dot[^>]*?href="([^"]*)"[^>]*?title="([^"]*)"[^>]*>'
        r'(?:<span[^>]*>([^<]*)</span>)?([^<]*)</a>', re.S)

    RE_H1_TITLE    = re.compile(r'<h1\s+class="title"><span[^>]*>(.*?)</span>', re.S)
    RE_TITLE_TAG   = re.compile(r'<title>《([^》]*)》')
    RE_SCORE       = re.compile(r'class="score[^"]*"[^>]*>([\d.]+)</span>')
    RE_OG_IMAGE    = re.compile(r'<meta[^>]*og:image[^>]*content="([^"]+)"', re.I)
    RE_V_THUMB     = re.compile(r'v-thumb')

    # 详情字段精确提取
    RE_TYPE     = re.compile(r'<span class="text-muted">类型：</span>\s*<a[^>]*>([^<]*)</a>')
    RE_AREA     = re.compile(r'<span class="text-muted hidden-xs">地区：</span>\s*<a[^>]*>([^<]*)</a>')
    RE_YEAR     = re.compile(r'<span class="text-muted hidden-xs">年份：</span>\s*<a[^>]*>([^<]*)</a>')
    RE_ACTOR    = re.compile(r'<span class="text-muted">主演：</span>\s*([^<]*)')
    RE_DIRECTOR = re.compile(r'<span class="text-muted">导演：</span>\s*([^<]*)')
    RE_REMARK   = re.compile(r'<span class="pic-text text-right">([^<]*)</span>')
    RE_DESC     = re.compile(r'<p class="col-pd">\s*(.*?)</p>', re.S)

    # 播放列表
    RE_PLAY_TAB  = re.compile(r'href="#playlist(\d+)"[^>]*>\s*([^<]*)\s*</a>', re.S)
    RE_PLAY_EP   = re.compile(
        r'href="/pianduo/(\d+)-(\d+)-(\d+)\.html"[^>]*>\s*([^<]*)\s*</a>', re.S)
    RE_PLAY_LIST = re.compile(r'<div[^>]*id="playlist(\d+)"[^>]*>(.*?)</div>', re.S)
    RE_PLAY_ITEM = re.compile(r'<a[^>]*href="/pianduo/(\d+)-(\d+)-(\d+)\.html"[^>]*>([^<]*)</a>', re.S)

    # 播放器 JSON
    RE_PLAYER_AAAA  = re.compile(r'player_aaaa\s*=\s*(\{.*?\})\s*</script>', re.S)
    RE_PLAYER_DATA  = re.compile(r'player_data\s*=\s*(\{.*?\})\s*[;<]', re.S)
    RE_PLAYER_GEN   = re.compile(r'(player_\w+)\s*=\s*(\{[^}]+\})', re.S)

    RE_MEDIA_M3U8 = re.compile(r'(https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*)', re.I)
    RE_MEDIA_MP4  = re.compile(r'(https?://[^\s"\'<>\\]+\.mp4[^\s"\'<>\\]*)', re.I)
    RE_MEDIA_FLV  = re.compile(r'(https?://[^\s"\'<>\\]+\.flv[^\s"\'<>\\]*)', re.I)

    RE_PLACEHOLDER = re.compile(r'(load|placeholder|blank|icon|logo|default)', re.I)
    RE_VID         = re.compile(r'(\d+)\.html')
    RE_PAGECOUNT   = re.compile(r'/prew/\w+--------(\d+)---[\w.]*\.html')

    REM_TAG = re.compile(r'<[^>]+>')

    # 验证码/弹窗特征
    CHALLENGE_SIGNS = (
        'cf-browser-verification', 'cf_chl_opt', 'challenge-platform',
        'verify you are human', '请完成安全验证', '滑动验证', '访问受限'
    )

    _WINDOW = 900

    def __init__(self):
        super().__init__()

    def getName(self):
        return "仙腾影院"

    def init(self, extend=""):
        pass

    # ════════════ 首页 ════════════

    def homeContent(self, filter):
        result = {
            'class': [{'type_name': n, 'type_id': self.CATE[n]} for n in self.CATE]
        }
        if filter:
            filters = {}
            for name, cid in self.CATE.items():
                flist = []
                if cid in self.SUB_CATE:
                    flist.append({"key": "genre", "name": "按剧情",
                                  "value": self.SUB_CATE[cid]})
                flist.append({"key": "year", "name": "年份",
                              "value": self.YEAR_FILTERS})
                filters[cid] = flist
            result['filters'] = filters
        return result

    def homeVideoContent(self):
        try:
            html = self._fetch_html(self.HOST + "/prew/dianying-----------.html")
            return {'list': self._parse_list_html(html)[:30]}
        except Exception:
            return {'list': []}

    # ════════════ 分类 ════════════

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        result = {'list': [], 'page': page, 'pagecount': 1,
                  'limit': 30, 'total': 0}
        try:
            year  = (extend or {}).get('year', '') or ''
            genre = (extend or {}).get('genre', '') or ''

            if genre and year:
                url = "{0}/prew/{1}---{2}--------{3}---{4}.html".format(
                    self.HOST, tid, genre, page, year)
            elif genre:
                url = "{0}/prew/{1}---{2}--------{3}---.html".format(
                    self.HOST, tid, genre, page)
            elif year:
                url = "{0}/prew/{1}-----------{2}.html".format(
                    self.HOST, tid, year)
            else:
                url = "{0}/prew/{1}-----------.html".format(self.HOST, tid)

            html = self._fetch_html(url)
            result['list'] = self._parse_list_html(html)
            pagecount = self._parse_pagecount(html)
            result['pagecount'] = pagecount if pagecount else 9999
            result['total'] = 999999
        except Exception:
            pass
        return result

    # ════════════ 详情 ════════════

    @cache(ttl=600)
    def _get_detail_html(self, vod_id):
        return self._fetch_html("{0}/pian/{1}.html".format(self.HOST, vod_id))

    def detailContent(self, array):
        try:
            return self._detail_inner(array)
        except Exception as e:
            vod_id = str(array[0]) if array else ""
            return {'list': [{
                "vod_id": vod_id, "vod_name": "解析异常", "vod_pic": "",
                "type_name": "", "vod_year": "", "vod_area": "",
                "vod_remarks": "", "vod_actor": "", "vod_director": "",
                "vod_content": str(e)[:200],
                "vod_play_from": "默认线路",
                "vod_play_url": "播放$" + vod_id + "___1___1",
            }]}

    def _detail_inner(self, array):
        vod_id = str(array[0])
        html = self._get_detail_html(vod_id)
        if not html or len(html) < 200:
            raise Exception("详情页获取失败")

        # 标题
        title = ""
        m = self.RE_H1_TITLE.search(html)
        if m:
            title = html_mod.unescape(self.REM_TAG.sub('', m.group(1))).strip()
        if not title:
            m = self.RE_TITLE_TAG.search(html)
            title = html_mod.unescape(m.group(1)).strip() if m else ""

        # 评分
        m = self.RE_SCORE.search(html)
        score = m.group(1) if m else ""

        # 类型 / 地区 / 年份 / 主演 / 导演
        def _g(pat):
            mm = pat.search(html)
            return html_mod.unescape(mm.group(1)).strip() if mm else ""

        type_name = _g(self.RE_TYPE)
        area      = _g(self.RE_AREA)
        year      = _g(self.RE_YEAR)
        actor     = _g(self.RE_ACTOR).strip(',').strip()
        director  = _g(self.RE_DIRECTOR).strip(',').strip()

        # ★ 备注（更新集数）— 用 pic-text
        remarks = _g(self.RE_REMARK)

        # 简介（去掉书名号前缀）
        content = ""
        m = self.RE_DESC.search(html)
        if m:
            txt = html_mod.unescape(self.REM_TAG.sub('', m.group(1))).strip()
            txt = re.sub(r'^\s*《[^》]*》\s*', '', txt)
            content = txt[:500]

        # 海报
        pic = self._extract_detail_pic(html)

        vod = {
            "vod_id": vod_id, "vod_name": title, "vod_pic": pic,
            "type_name": type_name, "vod_year": year, "vod_area": area,
            "vod_remarks": remarks, "vod_actor": actor,
            "vod_director": director, "vod_content": content,
            "vod_score": score,
        }

        play_from, play_url = self._parse_play_list(html, vod_id)
        vod["vod_play_from"] = play_from
        vod["vod_play_url"]  = play_url

        return {'list': [vod]}

    # ════════════ 搜索 ════════════

    @cache(ttl=300)
    def _get_search_html(self, key, page):
        # 站点表单实际格式：/search/-------------.html?wd=xxx
        wd = quote(key, safe='')
        if page <= 1:
            url = "{0}/search/-------------.html?wd={1}".format(self.HOST, wd)
        else:
            url = "{0}/search/-------------.html?wd={1}&page={2}".format(
                self.HOST, wd, page)
        return self._fetch_html(url)

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        try:
            html = self._get_search_html(key, page)
            return {'list': self._parse_list_html(html)}
        except Exception:
            return {'list': []}

    # ════════════ ★ 播放（核心修复） ════════════

    @cache(ttl=300)
    def _get_play_html(self, vod_id, sid, nid):
        url = "{0}/pianduo/{1}-{2}-{3}.html".format(self.HOST, vod_id, sid, nid)
        return self._fetch_html(url)

    def _is_challenge_page(self, html):
        """检测验证码/弹窗拦截页"""
        if not html or len(html) < 200:
            return True
        lower = html.lower()
        if any(s in lower for s in self.CHALLENGE_SIGNS):
            return True
        # 短页 + captcha 关键字
        if len(html) < 2500 and ('captcha' in lower or '验证码' in html):
            return True
        return False

    def _get_play_referer(self, url):
        """根据播放域名返回合适 Referer"""
        try:
            host = urlparse(url).netloc.lower()
            for key, ref in self.PLAY_REFERERS.items():
                if key in host:
                    return ref
            if host:
                return "https://" + host + "/"
        except Exception:
            pass
        return self.HOST + "/"

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "url": id, "header": ""}
        try:
            parts = id.split("___")
            if len(parts) < 3:
                return result

            vod_id, sid, nid = parts[0], parts[1], parts[2]
            html = self._get_play_html(vod_id, sid, nid)

            # 检测验证码，重试一次
            if self._is_challenge_page(html):
                url = "{0}/pianduo/{1}-{2}-{3}.html".format(
                    self.HOST, vod_id, sid, nid)
                html = self._fetch_html(url)

            # ★ 直接提取 player_aaaa.url → 拿到真实 m3u8，绕过 iframe 弹窗
            player_json = self._extract_player_data(html)
            real_url = ""
            if player_json:
                real_url = (player_json.get('url') or '').replace('\\/', '/')
                encrypt = player_json.get('encrypt', 0)
                if real_url and encrypt == 1:
                    real_url = unquote(real_url)
                elif real_url and encrypt == 2:
                    real_url = self._aes_decrypt(real_url, html)

            # 兜底：从 HTML 中提取未转义的 m3u8
            if not real_url:
                m = (self.RE_MEDIA_M3U8.search(html)
                     or self.RE_MEDIA_MP4.search(html)
                     or self.RE_MEDIA_FLV.search(html))
                if m:
                    real_url = m.group(1).replace('\\/', '/')

            if real_url:
                referer = self._get_play_referer(real_url)
                result = {
                    "parse": 0,
                    "playUrl": "",
                    "url": real_url,
                    "header": json.dumps({
                        "User-Agent": self.UA,
                        "Referer": referer,
                    }, ensure_ascii=False)
                }
            else:
                # 兜底：返回原页面（有些 TVBox 会调解析器）
                result = {
                    "parse": 0,
                    "url": "{0}/pianduo/{1}-{2}-{3}.html".format(
                        self.HOST, vod_id, sid, nid),
                    "header": ""
                }
        except Exception:
            pass
        return result

    # ════════════ 网络请求 ════════════

    def _headers(self):
        return {
            "User-Agent": self.UA,
            "Referer": self.HOST + "/",
            "Accept": ("text/html,application/xhtml+xml,application/xml;"
                       "q=0.9,*/*;q=0.8"),
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Cookie": "js_on=1",
        }

    def _fetch_html(self, url):
        try:
            rsp = self.fetch(url, headers=self._headers(), timeout=8)
            rsp.encoding = rsp.encoding or 'utf-8'
            return rsp.text
        except Exception:
            try:
                rsp = self.fetch(url, headers=self._headers(), timeout=10)
                rsp.encoding = rsp.encoding or 'utf-8'
                return rsp.text
            except Exception:
                return ""

    # ════════════ 海报提取（多路兜底） ════════════

    def _extract_pic_from_chunk(self, chunk):
        if not chunk:
            return ""

        # 1) data-original
        m = self.RE_DATA_ORIG.search(chunk)
        if m and m.group(1).strip() and not m.group(1).startswith("data:"):
            return self._fix_url(m.group(1).strip())

        # 2) data-src
        m = self.RE_DATA_SRC.search(chunk)
        if m and m.group(1).strip() and not m.group(1).startswith("data:"):
            return self._fix_url(m.group(1).strip())

        # 3) style="background-image:url(...)"
        m = self.RE_BG.search(chunk)
        if m and m.group(1).strip():
            u = m.group(1).strip()
            u = u.replace("&quot;", "").replace("'", "").replace('"', "")
            if not u.startswith("data:"):
                return self._fix_url(u)

        # 4) src（跳过占位图）
        for sm in re.finditer(r'\bsrc="([^"]+)"', chunk):
            u = sm.group(1).strip()
            if not u or u.startswith("data:"):
                continue
            low = u.lower()
            if 'svg+xml' in low or self.RE_PLACEHOLDER.search(low):
                continue
            return self._fix_url(u)

        return ""

    # ════════════ 列表解析 ════════════

    def _parse_list_html(self, html):
        videos = []
        seen = set()
        if not html:
            return videos

        for m in self.RE_THUMB.finditer(html):
            start = max(0, m.start() - 60)
            chunk = html[start: start + self._WINDOW]

            # 标题
            tm = self.RE_TITLE_ATTR.search(chunk)
            if tm:
                title = html_mod.unescape(tm.group(1)).strip()
            else:
                tm2 = re.search(r'>([^<>]{2,60})<', chunk)
                title = html_mod.unescape(tm2.group(1)).strip() if tm2 else ""
            if not title:
                continue

            # 海报
            pic = self._extract_pic_from_chunk(chunk)

            # ★ 备注（更新集数/完结）
            rm = self.RE_PIC_TEXT.search(chunk)
            remarks = html_mod.unescape(rm.group(1)).strip() if rm else ""

            # ID
            vid = ""
            lm = self.RE_THUMB_LINK.search(chunk)
            if lm:
                vid = self._extract_vid(lm.group(1))
            if not vid:
                for hm in self.RE_ANY_HREF.finditer(chunk):
                    vid = self._extract_vid(hm.group(1))
                    if vid:
                        break
            if not vid or vid in seen:
                continue
            seen.add(vid)

            videos.append({
                "vod_id": str(vid), "vod_name": title,
                "vod_pic": pic, "vod_remarks": remarks
            })

        # 文本列表项
        for m in self.RE_TEXT_ITEM.finditer(html):
            href = m.group(1)
            title = html_mod.unescape(m.group(2)).strip()
            remarks = html_mod.unescape(m.group(3)).strip() if m.group(3) else ""
            vid = self._extract_vid(href)
            if not vid or vid in seen or not title:
                continue
            seen.add(vid)
            videos.append({
                "vod_id": str(vid), "vod_name": title,
                "vod_pic": "", "vod_remarks": remarks
            })

        return videos

    def _extract_vid(self, href):
        m = self.RE_VID.search(href or "")
        return m.group(1) if m else ""

    def _fix_url(self, url):
        if not url:
            return ""
        url = url.strip().replace("&amp;", "&")
        if url.startswith('http'):
            return url
        if url.startswith('//'):
            return "https:" + url
        if url.startswith('/'):
            return self.HOST + url
        return self.HOST + '/' + url

    def _parse_pagecount(self, html):
        pages = self.RE_PAGECOUNT.findall(html)
        if pages:
            nums = [int(p) for p in pages if int(p) > 0]
            if nums:
                return max(nums)
        return 0

    # ════════════ 详情辅助 ════════════

    def _extract_detail_pic(self, html):
        m = self.RE_V_THUMB.search(html)
        if m:
            chunk = html[max(0, m.start() - 60): m.start() + 400]
            pic = self._extract_pic_from_chunk(chunk)
            if pic:
                return pic
        m = self.RE_OG_IMAGE.search(html)
        if m:
            return self._fix_url(m.group(1))
        return self._extract_pic_from_chunk(html)

    # ════════════ ★ 播放列表解析（核心修复） ════════════

    def _parse_play_list(self, html, vod_id):
        tab_matches = self.RE_PLAY_TAB.findall(html)
        ep_matches  = self.RE_PLAY_EP.findall(html)

        if not tab_matches or not ep_matches:
            return self._parse_play_list_alternative(html, vod_id)

        # 去重
        seen_ep = {}
        for vodid, sid, nid, raw_name in ep_matches:
            key = (vodid, sid, nid)
            ep_name = html_mod.unescape(raw_name).strip()
            if not ep_name:
                ep_name = "第{0}集".format(str(int(nid)).zfill(2))
            seen_ep[key] = (vodid, sid, nid, ep_name)
        ep_list = list(seen_ep.values())

        if tab_matches and ep_list:
            tabs = [(tid, html_mod.unescape(tn).strip() or ("线路" + tid))
                    for tid, tn in tab_matches]
            play_from_list, play_url_list = [], []

            for tab_id, tab_name in tabs:
                # ★ 修复：sid 与 #playlistN 的 N 一一对应
                sid_expected = int(tab_id)
                items = []
                for vodid, sid, nid, ep_name in ep_list:
                    if int(sid) == sid_expected:
                        items.append("{0}${1}___{2}___{3}".format(
                            ep_name, vodid, sid, nid))
                if items:
                    play_from_list.append(tab_name)
                    play_url_list.append("#".join(items))

            if play_from_list:
                return "$$$".join(play_from_list), "$$$".join(play_url_list)

        # 只有剧集、没有标签页
        if ep_list:
            items = []
            for vodid, sid, nid, ep_name in ep_list:
                items.append("{0}${1}___{2}___{3}".format(
                    ep_name, vodid, sid, nid))
            if items:
                return "默认线路", "#".join(items)

        # ★ 兜底：sid=1, nid=1（原 ___0___0 是无效的）
        return "默认线路", "播放$" + vod_id + "___1___1"

    def _parse_play_list_alternative(self, html, vod_id):
        play_from_list, play_url_list = [], []

        for m in self.RE_PLAY_LIST.finditer(html):
            tab_id  = m.group(1)
            content = m.group(2)

            tab_name = "线路" + tab_id
            nm = re.search(r'<h3[^>]*>([^<]*)</h3>', content, re.S)
            if nm:
                tab_name = html_mod.unescape(nm.group(1).strip())

            items = []
            for item in self.RE_PLAY_ITEM.finditer(content):
                vodid, sid, nid, ep_name = item.groups()
                ep_name = html_mod.unescape(ep_name.strip())
                if not ep_name:
                    ep_name = "第{0}集".format(str(int(nid)).zfill(2))
                items.append("{0}${1}___{2}___{3}".format(
                    ep_name, vodid, sid, nid))

            if items:
                play_from_list.append(tab_name)
                play_url_list.append("#".join(items))

        if play_from_list:
            return "$$$".join(play_from_list), "$$$".join(play_url_list)

        # ★ 兜底：sid=1, nid=1
        return "默认线路", "播放$" + vod_id + "___1___1"

    # ════════════ 播放器解析 ════════════

    def _extract_player_data(self, html):
        for pat in (self.RE_PLAYER_AAAA, self.RE_PLAYER_DATA):
            m = pat.search(html)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    try:
                        return json.loads(m.group(1).replace('\\/', '/'))
                    except Exception:
                        pass
        m = self.RE_PLAYER_GEN.search(html)
        if m:
            try:
                return json.loads(m.group(2))
            except Exception:
                pass
        return {}

    def _extract_media_url(self, html):
        m = (self.RE_MEDIA_M3U8.search(html)
             or self.RE_MEDIA_MP4.search(html)
             or self.RE_MEDIA_FLV.search(html))
        return m.group(1) if m else ""

    def _aes_decrypt(self, encrypted, html):
        try:
            from Crypto.Cipher import AES
            import base64
            key_match = re.search(r'key\s*[:=]\s*["\']([A-Za-z0-9]{16})["\']', html)
            key = key_match.group(1) if key_match else "28fd7d0f7dac4156"
            cipher = AES.new(key.encode(), AES.MODE_ECB)
            decrypted = cipher.decrypt(base64.b64decode(encrypted))
            pad = decrypted[-1]
            return decrypted[:-pad].decode('utf-8', errors='ignore')
        except Exception:
            return encrypted

    # ════════════ 通用 ════════════

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def localProxy(self, param):
        return [200, "video/MP2T", "", ""]