# -*- coding: utf-8 -*-
# 强国影院 www.qiangguoyw.com — CatVod/TvBox Python 源
# v4: 合并「评论精选」剧情简介到 vod_content + 详情页字段解析 + 动态播放线路

import sys
sys.path.append('..')
from base.spider import Spider
import json
import re
from urllib.parse import quote, unquote


class Spider(Spider):

    HOST = "https://www.qiangguoyw.com"

    CATE = {
        "短剧": "duanju",
        "电影": "dianying",
        "电视": "dianshi",
        "动漫": "dongman",
        "综艺": "zongyi",
        "纪录片": "jilupian",
    }

    SUB_CATE = {
        "duanju": [
            {"n": "全部", "v": ""},
            {"n": "爽文短剧", "v": "shuangwenduanju"},
            {"n": "女频恋爱", "v": "nvpinlianai"},
            {"n": "反转爽剧", "v": "fanzhuanshuangju"},
            {"n": "古装仙侠", "v": "guzhuangxianxia"},
            {"n": "年代穿越", "v": "niandaichuanyue"},
            {"n": "脑洞悬疑", "v": "naodongxuanyi"},
            {"n": "现代都市", "v": "xiandaidushi"},
        ],
        "dianying": [
            {"n": "全部", "v": ""},
            {"n": "动作", "v": "dongzuo"},
            {"n": "喜剧", "v": "xiju"},
            {"n": "爱情", "v": "aiqing"},
            {"n": "科幻", "v": "kehuan"},
            {"n": "恐怖", "v": "kongbu"},
            {"n": "剧情", "v": "juqing"},
            {"n": "战争", "v": "zhanzheng"},
            {"n": "道德", "v": "daode"},
        ],
        "dianshi": [
            {"n": "全部", "v": ""},
            {"n": "国产", "v": "guochan"},
            {"n": "日剧", "v": "riju"},
            {"n": "韩剧", "v": "hanju"},
            {"n": "欧美", "v": "oumei"},
            {"n": "港台", "v": "gangtai"},
            {"n": "泰剧", "v": "taiju"},
        ],
        "dongman": [
            {"n": "全部", "v": ""},
            {"n": "动漫电影", "v": "dongmandianying"},
            {"n": "中国动漫", "v": "zhongguodongman"},
            {"n": "日本动漫", "v": "ribendongman"},
            {"n": "欧美动漫", "v": "oumeidongman"},
        ],
        "zongyi": [
            {"n": "全部", "v": ""},
            {"n": "国产综艺", "v": "guochanzongyi"},
            {"n": "港台综艺", "v": "gangtaizongyi"},
            {"n": "日韩综艺", "v": "rihanzongyi"},
            {"n": "欧美综艺", "v": "oumeizongyi"},
        ],
        "jilupian": [
            {"n": "全部", "v": ""},
        ],
    }

    YEAR_FILTERS = [{"n": "全部", "v": ""}] + \
                   [{"n": str(y), "v": str(y)} for y in range(2026, 2003, -1)]

    UA = ("Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36")

    # ════════════ 预编译正则 ════════════

    # 列表
    RE_VOD_ITEM = re.compile(
        r'<a[^>]*class="[^"]*stui-vodlist__thumb[^"]*"[^>]*'
        r'href="/xq/(\d+)/"[^>]*'
        r'title="([^"]*)"[^>]*'
        r'data-original="([^"]*)"'
        r'[^>]*>.*?'
        r'<span[^>]*class="[^"]*pic-text[^"]*"[^>]*>(.*?)</span>',
        re.S
    )
    RE_H4_TITLE = re.compile(
        r'<h4[^>]*>.*?<a[^>]*href="/xq/(\d+)/"[^>]*title="([^"]*)"',
        re.S
    )

    # 详情页 - 标题 / 评分
    RE_H1 = re.compile(r'<h1[^>]*>(.*?)</h1>', re.S)
    RE_H1_SCORE = re.compile(
        r'<span[^>]*class="[^"]*score[^"]*"[^>]*>.*?</span>', re.S)
    RE_TITLE_TAG = re.compile(r'<title>([^<]*?)</title>')
    RE_SCORE = re.compile(
        r'<span[^>]*class="[^"]*score[^"]*"[^>]*>([\d.]+)</span>')

    # 详情页 - 封面
    RE_OG_IMAGE = re.compile(r'<meta[^>]*og:image[^>]*content="([^"]+)"', re.I)
    RE_OG_IMAGE2 = re.compile(r'<meta[^>]*content="([^"]+)"[^>]*og:image', re.I)
    RE_CONTENT_IMG = re.compile(
        r'<div[^>]*class="[^"]*stui-content__thumb[^"]*".*?'
        r'<img[^>]*data-original="([^"]+)"',
        re.S
    )
    RE_UPLOAD_VOD = re.compile(
        r'(/upload/vod/[^\s"\'<>]+\.(?:jpg|jpeg|png|webp))', re.I)

    # 详情页 - 简介段落
    RE_DESC_PARAGRAPH = re.compile(
        r'<p[^>]*class="[^"]*desc[^"]*"[^>]*>(.*?)</p>', re.S)
    RE_DESC_LABEL = re.compile(r'简介[：:]\s*</span>', re.S)
    RE_DESC_DETAIL_A = re.compile(r'<a\s[^>]*>\s*详情.*?</a>', re.S)

    # ✅ 新增：评论精选区块（id="desc"）里的 <p class="col-pd">
    RE_DESC_COMMENT = re.compile(
        r'id=["\']desc["\'][^>]*>.*?'
        r'<p[^>]*class="[^"]*col-pd[^"]*"[^>]*>(.*?)</p>',
        re.S
    )
    RE_META_DESC = re.compile(
        r'<meta[^>]*name="description"[^>]*content="([^"]*)"', re.I)

    # 播放线路 tab 名称 / 剧集链接
    RE_PLAY_TAB = re.compile(
        r'href="#playlist(\d+)"[^>]*>\s*([^<]*?)\s*</a>', re.S)
    RE_PLAY_EP = re.compile(
        r'href="/bf/(\d+)-(\d+)-(\d+)/"[^>]*>\s*([^<]*?)\s*</a>', re.S)

    RE_MEDIA_M3U8 = re.compile(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', re.I)
    RE_MEDIA_MP4 = re.compile(r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)', re.I)
    RE_MEDIA_FLV = re.compile(r'(https?://[^\s"\'<>]+\.flv[^\s"\'<>]*)', re.I)

    RE_PLAYER_AAAA = re.compile(r'player_aaaa\s*=\s*(\{.*?\})\s*[;<]', re.S)
    RE_PLAYER_DATA = re.compile(r'player_data\s*=\s*(\{.*?\})\s*[;<]', re.S)

    RE_PAGE_NUM = re.compile(r'/shw/\w+--------(\d+)---/')
    RE_PAGE_TOTAL = re.compile(r'(\d+)\s*/\s*(\d+)')

    REM_TAG = re.compile(r'<[^>]+>')
    RE_WS = re.compile(r'\s+')

    # ════════════ 接口方法 ════════════

    def getName(self):
        return "强国影院"

    def init(self, extend=""):
        pass

    # ──────────── 首页 ────────────

    def homeContent(self, filter):
        result = {}
        classes = [{'type_name': n, 'type_id': self.CATE[n]} for n in self.CATE]
        result['class'] = classes
        if filter:
            filters = {}
            for name, cid in self.CATE.items():
                flist = []
                subs = self.SUB_CATE.get(cid, [])
                if len(subs) > 1:
                    flist.append({"key": "sub", "name": "类型", "value": subs})
                flist.append({"key": "year", "name": "年份",
                              "value": self.YEAR_FILTERS})
                filters[cid] = flist
            result['filters'] = filters
        return result

    def homeVideoContent(self):
        result = {'list': []}
        try:
            html = self._fetch(self.HOST + "/shw/duanju-----------/")
            result['list'] = self._parse_list(html)[:30]
        except Exception:
            pass
        return result

    # ──────────── 分类列表 ────────────

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        result = {'list': [], 'page': page, 'pagecount': 1, 'limit': 30, 'total': 0}
        try:
            sub = (extend.get('sub', '') or '') if extend else ''
            slug = sub if sub else tid
            year = (extend.get('year', '') or '') if extend else ''

            if year:
                path = "/shw/{0}-----------{1}/".format(slug, year)
            elif page <= 1:
                path = "/shw/{0}-----------/".format(slug)
            else:
                path = "/shw/{0}--------{1}---/".format(slug, page)

            html = self._fetch(self.HOST + path)
            result['list'] = self._parse_list(html)
            result['pagecount'] = self._parse_pagecount(html) or 9999
            result['total'] = 999999
        except Exception:
            pass
        return result

    # ──────────── 详情 ────────────

    def detailContent(self, array):
        try:
            return self._detail_inner(array)
        except Exception as e:
            vod_id = str(array[0]) if array else ""
            vod = {
                "vod_id": vod_id, "vod_name": "解析异常", "vod_pic": "",
                "type_name": "", "vod_year": "", "vod_area": "",
                "vod_remarks": "", "vod_actor": "", "vod_director": "",
                "vod_content": str(e)[:200],
                "vod_play_from": "默认线路",
                "vod_play_url": "播放$" + vod_id + "___0___0"
            }
            return {'list': [vod]}

    def _detail_inner(self, array):
        vod_id = str(array[0])
        html = self._fetch("{0}/xq/{1}/".format(self.HOST, vod_id))
        if not html or len(html) < 200:
            raise Exception("详情页获取失败")

        # 标题（剥离 h1 内嵌评分 span）
        title = ""
        m = self.RE_H1.search(html)
        if m:
            h1_html = self.RE_H1_SCORE.sub('', m.group(1))
            title = self.REM_TAG.sub('', h1_html).strip()
        if not title:
            m = self.RE_TITLE_TAG.search(html)
            title = m.group(1).strip() if m else ""

        # 评分
        score = ""
        m = self.RE_SCORE.search(html)
        if m:
            score = m.group(1).strip()

        # 类型 / 地区 / 年份 / 主演 / 导演 / 更新
        type_name = self._after_label(html, "类型")
        area = self._after_label(html, "地区")
        year = self._after_label(html, "年份")
        actor = self._after_label(html, "主演")
        director = self._after_label(html, "导演")
        remarks = self._after_label(html, "更新")

        if year:
            m = re.search(r'(\d{4})', year)
            year = m.group(1) if m else year

        # ✅ 简介：合并「顶部 desc」+「评论精选 id=desc」+ meta 兜底
        content = self._extract_desc(html)

        # 封面
        pic = self._extract_pic(html)

        vod = {
            "vod_id": vod_id, "vod_name": title, "vod_pic": pic,
            "type_name": type_name, "vod_year": year, "vod_area": area,
            "vod_remarks": remarks, "vod_actor": actor,
            "vod_director": director, "vod_content": content,
            "vod_score": score,
        }
        vod["vod_play_from"], vod["vod_play_url"] = \
            self._parse_play_list(html, vod_id)
        return {'list': [vod]}

    # ──────────── 搜索 ────────────

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        result = {'list': []}
        try:
            try:
                url = "{0}/index.php/ajax/suggest?mid=1&wd={1}&page={2}".format(
                    self.HOST, quote(key), page)
                text = self._fetch(url)
                data = json.loads(text)
                items = data.get('list', [])
                if items:
                    result['list'] = [{
                        "vod_id": str(it.get('id', '')),
                        "vod_name": it.get('name', ''),
                        "vod_pic": self._norm_pic(it.get('pic', '')),
                        "vod_remarks": it.get('remark', ''),
                    } for it in items]
                    return result
            except Exception:
                pass

            if page <= 1:
                url = "{0}/sch/-------------/?wd={1}".format(
                    self.HOST, quote(key))
            else:
                url = "{0}/sch/-------------/?page={1}&wd={2}".format(
                    self.HOST, page, quote(key))
            html = self._fetch(url)
            result['list'] = self._parse_list(html)
        except Exception:
            pass
        return result

    # ──────────── 播放 ────────────

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 1, "url": "", "header": ""}
        try:
            parts = id.split("___")
            if len(parts) < 3:
                return {"parse": 0, "url": id, "header": ""}
            vod_id, sid, nid = parts[0], parts[1], parts[2]

            play_url = "{0}/bf/{1}-{2}-{3}/".format(self.HOST, vod_id, sid, nid)
            html = self._fetch(play_url)

            player_json = self._extract_player_data(html)
            if player_json and player_json.get('url', ''):
                real_url = player_json['url']
                encrypt = player_json.get('encrypt', 0)
                if encrypt == 1:
                    real_url = unquote(real_url)
                elif encrypt == 2:
                    real_url = self._aes_decrypt(real_url, html)
                result = {"parse": 0, "playUrl": "", "url": real_url,
                          "header": json.dumps(self._play_header())}
                return result

            media_url = self._extract_media_url(html)
            if media_url:
                result = {"parse": 0, "url": media_url,
                          "header": json.dumps(self._play_header())}
                return result

            result = {"parse": 1, "url": play_url, "header": ""}
        except Exception:
            pass
        return result

    # ════════════ 网络 ════════════

    def _headers(self):
        return {
            "User-Agent": self.UA,
            "Referer": self.HOST + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def _play_header(self):
        return {"User-Agent": self.UA, "Referer": self.HOST + "/"}

    def _fetch(self, url):
        rsp = self.fetch(url, headers=self._headers(), timeout=15)
        try:
            rsp.encoding = rsp.apparent_encoding or 'utf-8'
        except Exception:
            pass
        return rsp.text

    # ════════════ 列表解析 ════════════

    def _parse_list(self, html):
        videos = []
        seen = set()

        for m in self.RE_VOD_ITEM.finditer(html):
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)

            videos.append({
                "vod_id": vid,
                "vod_name": m.group(2).strip(),
                "vod_pic": self._norm_pic(m.group(3).strip()),
                "vod_remarks": self.REM_TAG.sub('', m.group(4)).strip()
            })

        if not videos:
            for m in self.RE_H4_TITLE.finditer(html):
                vid = m.group(1)
                if vid in seen:
                    continue
                seen.add(vid)
                videos.append({
                    "vod_id": vid,
                    "vod_name": m.group(2).strip(),
                    "vod_pic": "",
                    "vod_remarks": ""
                })
        return videos

    def _parse_pagecount(self, html):
        pages = self.RE_PAGE_NUM.findall(html)
        if pages:
            nums = [int(p) for p in pages if int(p) > 0]
            if nums:
                return max(nums)
        m = self.RE_PAGE_TOTAL.search(html)
        if m:
            total = int(m.group(2))
            if total > 0:
                return total
        return 0

    # ════════════ 详情字段提取 ════════════

    def _after_label(self, html, label):
        pat = (r'<span[^>]*>\s*' + re.escape(label) +
               r'[：:]\s*</span>(.*?)'
               r'(?=<span\b|</p\s*>|<div\b|<br\s*/?>|$)')
        m = re.search(pat, html, re.S)
        if m:
            v = self.REM_TAG.sub('', m.group(1))
            return v.replace('&nbsp;', ' ').strip()
        return ""

    def _clean_text(self, raw):
        """去标签 + 归一化空白"""
        if not raw:
            return ""
        text = self.REM_TAG.sub('', raw)
        text = text.replace('&nbsp;', ' ')
        text = self.RE_WS.sub(' ', text)
        return text.strip()

    def _extract_desc(self, html):
        """
        ✅ 合并多源简介：
        1) 顶部 <p class="desc"> 摘要
        2) 评论精选区块 id="desc" 里的 <p class="col-pd"> 完整剧情
        3) <meta name="description"> 兜底
        去重规则：互相包含时取长者；否则换行拼接。
        """
        candidates = []

        # 1) 顶部 desc 段落
        m = self.RE_DESC_PARAGRAPH.search(html)
        if m:
            block = m.group(1)
            block = self.RE_DESC_LABEL.sub('', block)
            block = self.RE_DESC_DETAIL_A.sub('', block)
            text = self._clean_text(block)
            if text:
                candidates.append(text)

        # 2) 评论精选（id="desc" → p.col-pd）
        m = self.RE_DESC_COMMENT.search(html)
        if m:
            text = self._clean_text(m.group(1))
            if text:
                candidates.append(text)

        # 3) meta description 兜底
        if not candidates:
            m = self.RE_META_DESC.search(html)
            if m:
                text = m.group(1).strip()
                text = re.sub(r'[，,。.]?\s*首映尽在[^，。.]*[。.]?$',
                              '', text).strip()
                text = text.replace('&nbsp;', ' ')
                if text:
                    candidates.append(text)

        if not candidates:
            return ""

        # 去重：如果候选互相包含，保留长者
        uniq = []
        for t in candidates:
            if not t:
                continue
            replaced = False
            for i, u in enumerate(uniq):
                if t in u:                 # 已有更长，跳过
                    replaced = True
                    break
                if u in t:                 # 当前更长，替换
                    uniq[i] = t
                    replaced = True
                    break
            if not replaced:
                uniq.append(t)

        # 按长度降序：主简介（最长）在前
        uniq.sort(key=len, reverse=True)
        return '\n'.join(uniq)

    def _extract_pic(self, html):
        for pat in (self.RE_OG_IMAGE, self.RE_OG_IMAGE2):
            m = pat.search(html)
            if m:
                return self._norm_pic(m.group(1))
        m = self.RE_CONTENT_IMG.search(html)
        if m:
            return self._norm_pic(m.group(1))
        m = self.RE_UPLOAD_VOD.search(html)
        if m:
            return self._norm_pic(m.group(1))
        return ""

    def _norm_pic(self, pic):
        if not pic:
            return ""
        pic = str(pic).strip()
        if not pic:
            return ""
        if pic.startswith('data:'):
            return pic
        if pic.startswith('//'):
            return 'https:' + pic
        if pic.startswith('http'):
            return pic
        if pic.startswith('/'):
            return self.HOST + pic
        return self.HOST + '/' + pic

    # ════════════ 播放线路（动态识别）════════════

    def _parse_play_list(self, html, vod_id):
        tab_map = {}
        for m in self.RE_PLAY_TAB.finditer(html):
            tab_map[m.group(1)] = m.group(2).strip()

        groups = {}
        order = []
        for m in self.RE_PLAY_EP.finditer(html):
            v_id, sid, nid, ep_name = m.group(1), m.group(2), m.group(3), m.group(4)
            if sid not in groups:
                groups[sid] = []
                order.append(sid)
            groups[sid].append((int(nid), ep_name.strip(), v_id))

        if not groups:
            m = re.search(r'href="(/bf/(\d+)-(\d+)-(\d+)/)"', html)
            if m:
                _, v_id, sid, nid = m.groups()
                name = tab_map.get(sid, "线路" + sid)
                return name, "播放${0}___{1}___{2}".format(v_id, sid, nid)
            return "默认线路", "播放$" + vod_id + "___0___0"

        from_list = []
        url_list = []
        for sid in order:
            eps = sorted(groups[sid], key=lambda x: x[0])
            tab_name = tab_map.get(sid, "线路" + sid)
            items = []
            for nid, ep_name, v_id in eps:
                if not ep_name:
                    ep_name = "第" + str(nid).zfill(2) + "集"
                items.append("{0}${1}___{2}___{3}".format(ep_name, v_id, sid, nid))
            from_list.append(tab_name)
            url_list.append("#".join(items))

        return "$$$".join(from_list), "$$$".join(url_list)

    # ════════════ 播放器数据 ════════════

    def _extract_player_data(self, html):
        for pat in (self.RE_PLAYER_AAAA, self.RE_PLAYER_DATA):
            m = pat.search(html)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    pass
        return {}

    def _extract_media_url(self, html):
        for pat in (self.RE_MEDIA_M3U8, self.RE_MEDIA_MP4, self.RE_MEDIA_FLV):
            m = pat.search(html)
            if m:
                return m.group(1)
        return ""

    def _aes_decrypt(self, encrypted, html):
        try:
            key_match = re.search(
                r'key\s*[:=]\s*["\']([A-Za-z0-9]{16})["\']', html)
            key = key_match.group(1) if key_match else "28fd7d0f7dac4156"
            from Crypto.Cipher import AES
            import base64
            cipher = AES.new(key.encode(), AES.MODE_ECB)
            decrypted = cipher.decrypt(base64.b64decode(encrypted))
            pad = decrypted[-1]
            return decrypted[:-pad].decode('utf-8', errors='ignore')
        except Exception:
            return encrypted

    # ════════════ 占位 ════════════

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def localProxy(self, param):
        return [200, "video/MP2T", "", ""]