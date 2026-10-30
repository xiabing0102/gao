# coding=utf-8
# !/usr/bin/python
import sys
sys.path.append('..')
from base.spider import Spider
import json
import time
import urllib.parse
import re


class Spider(Spider):

    def getName(self):
        return "厂长资源"

    def init(self, extend=""):
        self.host = "https://www.4kcz.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': self.host + '/'
        }
        self.mobile_ua = (
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) '
            'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 '
            'Mobile/15E148 Safari/604.1'
        )
        self._waf_passed = False
        self._waf_cookies = {}
        self.log(f"厂长资源爬虫初始化完成，主站: {self.host}")

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    # ==================================================================
    # WAF 盾自动验证
    # ==================================================================
    def _is_waf_challenge(self, text):
        if not text:
            return False
        low = text.lower()
        markers = [
            'safeline', 'slg-box', 'slg-bg', 'challenge.js',
            'protected by', '雷池', 'challenge/v2'
        ]
        return any(m in low for m in markers)

    def _extract_cookies_from_response(self, rsp):
        try:
            raw_cookies = []
            if hasattr(rsp, 'headers'):
                if hasattr(rsp.headers, 'get_all'):
                    raw_cookies = rsp.headers.get_all('Set-Cookie') or []
                elif hasattr(rsp.headers, 'get'):
                    c = rsp.headers.get('Set-Cookie')
                    if c:
                        raw_cookies = [c]
            for c in raw_cookies:
                pair = c.split(';')[0]
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    self._waf_cookies[k.strip()] = v.strip()
        except Exception as e:
            self.log(f"提取 cookie 失败: {e}")

    def _apply_waf_cookies(self, headers):
        if self._waf_cookies:
            ck = '; '.join([f"{k}={v}" for k, v in self._waf_cookies.items()])
            headers['Cookie'] = ck

    def _fetch_with_waf(self, url, extra_headers=None, referer=None, retry=3):
        """
        带 WAF 盾自动验证：优先复用已通过的 UA / cookie，
        只有被拦时才切换 UA 重试（避免每次都打回移动端 UA 造成额外延迟）。
        """
        headers = self.headers.copy()
        if referer:
            headers['Referer'] = referer
        if extra_headers:
            headers.update(extra_headers)
        self._apply_waf_cookies(headers)

        # 已通过且缓存的 UA 直接使用
        rsp = None
        try:
            rsp = self.fetch(url, headers=headers)
            self._extract_cookies_from_response(rsp)
            text = rsp.text or ''
        except Exception as e:
            self.log(f"请求失败: {e}")
            text = ''

        if text and not self._is_waf_challenge(text):
            self._waf_passed = True
            return rsp

        self.log("⚠️ 检测到雷池 WAF 盾，开始自动验证...")

        # 策略 1：移动端 UA（重试）
        for attempt in range(retry):
            try:
                mobile_headers = headers.copy()
                mobile_headers['User-Agent'] = self.mobile_ua
                mobile_headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                self._apply_waf_cookies(mobile_headers)
                if referer:
                    mobile_headers['Referer'] = referer

                self.log(f"WAF 策略1-移动端UA 第 {attempt+1} 次尝试")
                time.sleep(1.0 + attempt * 0.5)
                rsp = self.fetch(url, headers=mobile_headers)
                self._extract_cookies_from_response(rsp)
                text = rsp.text or ''
                if not self._is_waf_challenge(text):
                    self.log(f"✅ WAF 通过（移动端 UA，第 {attempt+1} 次）")
                    self._waf_passed = True
                    self.headers['User-Agent'] = self.mobile_ua
                    return rsp
            except Exception as e:
                self.log(f"移动端 UA 尝试失败: {e}")

        # 策略 2：连续重试
        for attempt in range(retry + 2):
            try:
                self.log(f"WAF 策略2-连续重试 第 {attempt+1} 次")
                time.sleep(2.0)
                retry_headers = headers.copy()
                self._apply_waf_cookies(retry_headers)
                if referer:
                    retry_headers['Referer'] = referer
                rsp = self.fetch(url, headers=retry_headers)
                self._extract_cookies_from_response(rsp)
                text = rsp.text or ''
                if not self._is_waf_challenge(text):
                    self.log(f"✅ WAF 通过（连续重试，第 {attempt+1} 次）")
                    self._waf_passed = True
                    return rsp
            except Exception as e:
                self.log(f"连续重试失败: {e}")

        # 策略 3：带 cookie 重放（不清 cookie，保留上一次过盾成果）
        try:
            self.log("WAF 策略3-带 cookie 重放")
            time.sleep(3.0)
            replay_headers = headers.copy()
            self._apply_waf_cookies(replay_headers)
            if referer:
                replay_headers['Referer'] = referer
            rsp = self.fetch(url, headers=replay_headers)
            self._extract_cookies_from_response(rsp)
            return rsp
        except Exception as e:
            self.log(f"最终重放失败: {e}")

        self.log("❌ WAF 验证失败")
        return rsp

    # ==================================================================
    # 首页 / 分类
    # ==================================================================
    def homeContent(self, filter):
        result = {'class': self._classes(), 'filters': self._get_filters()}
        try:
            rsp = self._fetch_with_waf(self.host + "/")
            doc = self.html(rsp.text)
            result['list'] = self._get_videos(doc, limit=80)
        except Exception as e:
            self.log(f"首页获取出错: {str(e)}")
            result['list'] = []
        return result

    def homeVideoContent(self):
        return {'class': self._classes(), 'filters': self._get_filters()}

    def _classes(self):
        return [
            {'type_id': 'movie_bt',          'type_name': '分类筛选'},
            {'type_id': 'zuixindianying',    'type_name': '最新电影'},
            {'type_id': 'dbtop250',          'type_name': '豆瓣Top250'},
            {'type_id': 'dongmanjuchangban', 'type_name': '剧场版'},
            {'type_id': 'gcj',               'type_name': '国产剧'},
            {'type_id': 'meijutt',           'type_name': '美剧'},
            {'type_id': 'hanjutv',           'type_name': '韩剧'},
            {'type_id': 'fanju',             'type_name': '番剧'},
        ]

    def categoryContent(self, tid, pg, filter, extend):
        try:
            # 合并 filter 和 extend
            ext = {}
            if filter and isinstance(filter, dict):
                ext.update(filter)
            if extend and isinstance(extend, dict):
                ext.update(extend)

            url = self._build_url(tid, pg, ext)
            self.log(f"分类URL: {url}")

            rsp = self._fetch_with_waf(url, referer=self.host + '/')
            if self._is_waf_challenge(rsp.text or ''):
                return {'list': [], 'page': int(pg), 'pagecount': 0, 'limit': 100, 'total': 0}

            doc = self.html(rsp.text)
            videos = self._get_videos(doc, limit=100)

            pagecount = 999
            last = doc.xpath('//div[contains(@class,"pagenavi_txt")]//a/@href')
            for href in last:
                m = re.search(r'/page/(\d+)', href)
                if m:
                    pagecount = max(pagecount, int(m.group(1)))

            return {
                'list': videos,
                'page': int(pg),
                'pagecount': pagecount,
                'limit': 100,
                'total': pagecount * 100
            }
        except Exception as e:
            self.log(f"分类内容获取出错: {str(e)}")
            return {'list': [], 'page': int(pg), 'pagecount': 1, 'limit': 100, 'total': 0}

    # ==================================================================
    # 搜索
    # ==================================================================
    def searchContent(self, key, quick, pg="1"):
        try:
            encoded_key = urllib.parse.quote(key)
            if pg and str(pg) != "1":
                search_url = f"{self.host}/nimasile?q={encoded_key}&f=_all&p={pg}"
            else:
                search_url = f"{self.host}/nimasile?q={encoded_key}"

            self.log(f"搜索URL: {search_url}")
            rsp = self._fetch_with_waf(search_url, referer=self.host + '/')

            try:
                html_text = rsp.text if rsp.text else ''
            except Exception:
                html_text = ''

            if self._is_waf_challenge(html_text):
                self.log("⚠️ 搜索仍被 WAF 拦截")
                return {'list': []}

            doc = self.html(html_text)

            # 多级兜底定位搜索结果
            elements = doc.xpath('//div[contains(@class,"search_list")]//li')
            if not elements:
                elements = doc.xpath('//div[contains(@class,"bt_img")]//li')
            if not elements:
                elements = doc.xpath('//li[.//a[contains(@href,"/movie/")]]')

            self.log(f"找到 {len(elements)} 个搜索结果元素")

            videos, seen_ids = [], set()
            for elem in elements:
                video = self._extract_video(elem)
                if not video:
                    continue
                if video['vod_id'] in seen_ids:
                    continue
                if self._is_relevant_search_result(video['vod_name'], key):
                    videos.append(video)
                    seen_ids.add(video['vod_id'])

            # 分页
            pagecount = 1
            pager_links = doc.xpath('//div[contains(@class,"pagenavi_txt")]//a/@href')
            for href in pager_links:
                m = re.search(r'[?&]p=(\d+)', href)
                if m:
                    pagecount = max(pagecount, int(m.group(1)))

            self.log(f"最终搜索结果: {len(videos)} 个视频")
            return {
                'list': videos,
                'page': int(pg),
                'pagecount': pagecount,
                'limit': 20,
                'total': pagecount * 20
            }
        except Exception as e:
            self.log(f"搜索出错: {str(e)}")
            return {'list': []}

    # ==================================================================
    # 详情
    # ==================================================================
    def detailContent(self, ids):
        try:
            vid = str(ids[0])
            detail_url = f"{self.host}/movie/{vid}.html"
            rsp = self._fetch_with_waf(detail_url, referer=self.host + '/')
            doc = self.html(rsp.text)

            video_info = self._get_detail(doc, vid)
            return {'list': [video_info]} if video_info else {'list': []}
        except Exception as e:
            self.log(f"详情获取出错: {str(e)}")
            return {'list': []}

    def _get_detail(self, doc, vid):
        try:
            title = self._get_text(doc, [
                '//div[contains(@class,"moviedteail_tt")]/h1/text()',
                '//h1/text()',
                '//h1/a/text()'
            ])
            pic = self._get_text(doc, [
                '//div[contains(@class,"dyimg")]//img/@data-original',
                '//div[contains(@class,"dyimg")]//img/@src',
            ])
            if pic and pic.startswith('/'):
                pic = self.host + pic

            desc = self._get_text(doc, [
                '//div[contains(@class,"yp_context")]/text()',
                '//div[contains(@class,"yp_context")]//p/text()',
            ])
            year = self._get_text(doc, ['//ul[contains(@class,"moviedteail_list")]//a[contains(@href,"/year/")]/text()'])
            area = self._get_text(doc, ['//ul[contains(@class,"moviedteail_list")]//a[contains(@href,"/movie_bt_cat/")]/text()'])
            type_name = self._get_text(doc, ['//ul[contains(@class,"moviedteail_list")]//a[contains(@href,"/movie_bt_tags/")]/text()'])

            director = self._get_text(doc, ['//li[contains(text(),"导演")]/span/text()'])
            actor = self._get_text(doc, ['//li[contains(text(),"主演")]/span/text()'])
            if not actor or actor.lower() == 'false':
                actor_arr = doc.xpath('//p[contains(@class,"inzhuy")]/text()')
                if actor_arr:
                    actor = re.sub(r'^\s*主演[:：]\s*', '', actor_arr[0].strip())

            # 备注（更新状态）—— 从 moviedteail_list 或顶部信息取
            remarks = self._get_text(doc, [
                '//div[contains(@class,"moviedteail_tt")]//span/text()',
                '//li[contains(text(),"状态")]/span/text()',
                '//li[contains(text(),"集数")]/span/text()',
            ])

            # 播放列表 —— 支持多种容器 class
            play_from, play_urls = [], []
            episodes = []
            episode_links = doc.xpath('//div[contains(@class,"paly_list_btn")]//a')
            if not episode_links:
                episode_links = doc.xpath('//ul[contains(@class,"content_playlist")]//a')
            if not episode_links:
                episode_links = doc.xpath('//div[contains(@class,"playlist")]//a')

            for ep_link in episode_links:
                ep_title_arr = ep_link.xpath('.//text()')
                ep_href_arr = ep_link.xpath('./@href')
                if not ep_title_arr or not ep_href_arr:
                    continue
                ep_title = ''.join([t for t in ep_title_arr if t]).strip()
                ep_href = ep_href_arr[0]
                play_id = self.regStr(r'/v_play/([^/]+?)\.html', ep_href)
                if not play_id:
                    # 兼容 /v_play/xxx-1-1.html
                    m = re.search(r'/v_play/([^"\'#?]+?)(?:\.html)?$', ep_href)
                    if m:
                        play_id = m.group(1)
                if play_id:
                    episodes.append(f"{ep_title}${play_id}")

            if episodes:
                play_from.append("厂长资源")
                play_urls.append('#'.join(episodes))

            return {
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'type_name': type_name,
                'vod_year': year,
                'vod_area': area,
                'vod_remarks': remarks,
                'vod_actor': actor,
                'vod_director': director,
                'vod_content': desc,
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_urls)
            }
        except Exception as e:
            self.log(f"获取详情出错: {str(e)}")
            return None

    # ==================================================================
    # 播放
    # ==================================================================
    def playerContent(self, flag, id, vipFlags):
        try:
            self.log(f"获取播放链接: flag={flag}, id={id}")
            start_time = time.time()

            # 修正：id 可能已经带 .html，也可能不带
            clean_id = id[:-5] if id.endswith('.html') else id
            play_url = f"{self.host}/v_play/{clean_id}.html"

            rsp = self._fetch_with_waf(play_url, referer=self.host + '/')

            try:
                html = rsp.text if rsp.encoding else rsp.content.decode('utf-8', errors='ignore')
            except Exception:
                try:
                    html = rsp.content.decode('gbk', errors='ignore')
                except Exception:
                    html = rsp.content.decode('latin-1', errors='ignore')

            real_url = self._extract_real_video_url(html, play_url)

            end_time = time.time()
            self.log(f"播放链接获取完成，耗时{end_time - start_time:.2f}秒, url={real_url}")

            if real_url and any(ext in real_url.lower() for ext in ['.m3u8', '.mp4', '.flv', '.avi']):
                return {'parse': 0, 'playUrl': '', 'url': real_url}
            elif real_url and real_url.startswith('http'):
                return {'parse': 1, 'playUrl': '', 'url': real_url}
            else:
                return {'parse': 1, 'playUrl': '', 'url': play_url}
        except Exception as e:
            self.log(f"播放链接获取出错: {str(e)}")
            return {'parse': 1, 'playUrl': '', 'url': f"{self.host}/v_play/{id}.html"}

    def _extract_real_video_url(self, html, play_page_url):
        try:
            # 1. player_aaaa JSON 变量
            url = self._parse_player_aaaa(html)
            if url:
                return url

            # 2. iframe 中的 player
            iframe_pattern = r'<iframe[^>]+src=["\']([^"\']+)["\']'
            iframe_matches = re.findall(iframe_pattern, html, re.IGNORECASE)
            for iframe_src in iframe_matches:
                try:
                    iframe_url = self._resolve_url(iframe_src, play_page_url)

                    iframe_headers = self.headers.copy()
                    iframe_headers['Referer'] = play_page_url

                    self.log(f"获取iframe内容: {iframe_url}")
                    iframe_rsp = self.fetch(iframe_url, headers=iframe_headers)
                    iframe_html = iframe_rsp.text

                    u = self._parse_player_aaaa(iframe_html)
                    if u:
                        return u

                    v = self._find_video_file(iframe_html)
                    if v:
                        return v

                    if 'url=' in iframe_url:
                        m = re.search(r'url=([^&\s]+)', iframe_url)
                        if m:
                            decoded = self._try_decode_url(urllib.parse.unquote(m.group(1)))
                            if decoded:
                                return decoded
                except Exception as e:
                    self.log(f"获取iframe内容失败: {str(e)}")
                    continue

            # 3. 直接搜索视频文件
            v = self._find_video_file(html)
            if v:
                return v

            self.log("未找到任何有效的视频播放链接")
            return ''
        except Exception as e:
            self.log(f"提取真实视频链接出错: {str(e)}")
            return ''

    def _resolve_url(self, src, base_page):
        """统一解析相对/绝对 URL"""
        if src.startswith('//'):
            return 'https:' + src
        if src.startswith('http'):
            return src
        if src.startswith('/'):
            return self.host + src
        # 相对于页面路径
        base = base_page.rsplit('/', 1)[0]
        return f"{base}/{src.lstrip('./')}"

    def _parse_player_aaaa(self, html):
        for marker in ['player_aaaa', 'var player_aaaa', 'player_aaaa:']:
            idx = html.find(marker)
            if idx == -1:
                continue
            brace_idx = html.find('{', idx)
            if brace_idx == -1 or brace_idx - idx > 30:
                continue
            json_str = self._extract_json_object(html, brace_idx)
            if not json_str:
                continue
            try:
                data = json.loads(json_str)
                url = data.get('url', '')
                if url:
                    decoded = self._try_decode_url(url)
                    if decoded:
                        self.log(f"✅ player_aaaa 中提取到: {decoded}")
                        return decoded
            except Exception as e:
                self.log(f"解析 player_aaaa 失败: {e}")
        return ''

    def _extract_json_object(self, text, start_idx):
        while start_idx < len(text) and text[start_idx] in ' \t\n\r':
            start_idx += 1
        if start_idx >= len(text) or text[start_idx] != '{':
            return None
        depth = 0
        start = start_idx
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        return None

    def _try_decode_url(self, url):
        if not url:
            return ''
        for _ in range(3):
            if url.startswith('http'):
                return url
            new_url = urllib.parse.unquote(url)
            if new_url == url:
                break
            url = new_url
        return url if url.startswith('http') else ''

    def _find_video_file(self, html):
        patterns = [
            r'https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*',
            r'https?://[^\s"\'<>\\]+\.mp4[^\s"\'<>\\]*',
            r'https?://[^\s"\'<>\\]+\.flv[^\s"\'<>\\]*',
        ]
        skip_words = ['blank.gif', 'logo', 'thumb', 'poster', 'preview']
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if not any(s in match.lower() for s in skip_words):
                    self.log(f"找到视频文件链接: {match}")
                    return match
        return ''

    # ==================================================================
    # 列表解析
    # ==================================================================
    def _get_videos(self, doc, limit=None):
        try:
            videos, seen_ids = [], set()
            elements = doc.xpath('//div[contains(@class,"bt_img")]//li')
            if not elements:
                elements = doc.xpath('//ul[contains(@class,"bt_img")]//li')

            self.log(f"找到 {len(elements)} 个列表项")
            if not elements:
                self.log("⚠️ 未找到任何列表项")
                return []

            for elem in elements:
                video = self._extract_video(elem)
                if video and video['vod_id'] not in seen_ids:
                    videos.append(video)
                    seen_ids.add(video['vod_id'])

            self.log(f"最终解析出 {len(videos)} 个视频")
            return videos[:limit] if limit else videos
        except Exception as e:
            self.log(f"获取视频列表出错: {str(e)}")
            return []

    def _extract_video(self, element):
        """
        兼容：
        - 首页/分类页：<a href="https://www.4kcz.com/movie/xxx.html"><img data-original=...></a>
        - 搜索结果：  <a href="/movie/xxx.html"><img src=...></a>
        """
        try:
            # 优先找 h3.dytit 里的 <a>，避免误取广告/轮播图链接
            hrefs = element.xpath('.//h3[contains(@class,"dytit")]//a/@href')
            if not hrefs:
                hrefs = element.xpath('.//a[contains(@href,"/movie/")]/@href')
            if not hrefs:
                return None

            link = hrefs[0].strip()
            if link.startswith('//'):
                link = 'https:' + link
            elif link.startswith('/'):
                link = self.host + link
            elif not link.startswith('http'):
                link = self.host + '/' + link

            vod_id = ''
            # 支持带查询参数的 /movie/xxx.html?xxx
            m = re.search(r'/movie/(\d+)\.html', link)
            if m:
                vod_id = m.group(1)
            if not vod_id:
                return None

            # 标题
            title = ''
            title_selectors = [
                './/h3[contains(@class,"dytit")]//a/text()',
                './/h3/a/text()',
                './/h3/text()',
                './/img/@alt',
            ]
            for sel in title_selectors:
                arr = element.xpath(sel)
                for t in arr:
                    if t and t.strip() and len(t.strip()) > 1:
                        title = t.strip()
                        break
                if title:
                    break
            if not title:
                return None

            # 封面
            pic = ''
            for attr in ['data-original', 'data-src', 'src']:
                arr = element.xpath(f'.//img/@{attr}')
                for p in arr:
                    if not p:
                        continue
                    if 'blank.gif' in p or p.startswith('data:image/') or 'base64' in p:
                        continue
                    if p.startswith('//'):
                        pic = 'https:' + p
                    elif p.startswith('/'):
                        pic = self.host + p
                    else:
                        pic = p
                    break
                if pic:
                    break

            # 备注：hdinfo + jidi + rating
            remarks_parts = []
            for sp in element.xpath('.//div[contains(@class,"hdinfo")]//span/text()'):
                if sp and sp.strip():
                    remarks_parts.append(sp.strip())
            for sp in element.xpath('.//div[contains(@class,"jidi")]//span/text()'):
                if sp and sp.strip():
                    remarks_parts.append(sp.strip())
            rating_arr = element.xpath('.//div[contains(@class,"rating")]/text()')
            for r in rating_arr:
                r = (r or '').strip()
                if r:
                    remarks_parts.append(r)
                    break

            seen_r, remarks_list = set(), []
            for r in remarks_parts:
                if r not in seen_r:
                    seen_r.add(r)
                    remarks_list.append(r)
            remarks = ' '.join(remarks_list)

            # 主演
            actor = ''
            actor_arr = element.xpath('.//p[contains(@class,"inzhuy")]/text()')
            if actor_arr:
                actor = re.sub(r'^\s*主演[:：]\s*', '', actor_arr[0].strip())
                if actor.lower() == 'false':
                    actor = ''

            return {
                'vod_id': vod_id,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': remarks,
                'vod_year': '',
                'vod_actor': actor,
            }
        except Exception as e:
            self.log(f"提取视频信息出错: {str(e)}")
            return None

    # ==================================================================
    # URL 构建（支持多筛选组合）
    # ==================================================================
    def _build_url(self, tid, pg, extend):
        try:
            self.log(f"构建URL: tid={tid}, pg={pg}, extend={extend}")

            category_map = {
                'movie_bt':          '/movie_bt',
                'zuixindianying':    '/zuixindianying',
                'dbtop250':          '/dbtop250',
                'dongmanjuchangban': '/dongmanjuchangban',
                'gcj':               '/gcj',
                'meijutt':           '/meijutt',
                'hanjutv':           '/hanjutv',
                'fanju':             '/fanju',
                'riju':              '/riju',
                'haiwaijuqita':      '/haiwaijuqita',
                'dyy':               '/movie_bt_series/dyy',
                'guochanju':         '/gcj',
                'mj':                '/meijutt',
                'hj':                '/hanjutv',
                'rj':                '/riju',
                'hwj':               '/haiwaijuqita',
                'fjj':               '/fanju',
            }

            # 1) 优先使用 caturl 作为基础路径
            base_path = None
            if extend:
                caturl = (extend.get('caturl') or '').strip()
                if caturl:
                    base_path = caturl if caturl.startswith('/') else ('/' + caturl)

            if not base_path:
                base_path = category_map.get(tid, '/movie_bt')

            url = f"{self.host}{base_path.rstrip('/')}"

            # 2) 依次拼接其它筛选（areal / yearl / tagl），支持组合
            if extend:
                for key in ('areal', 'yearl', 'tagl'):
                    v = (extend.get(key) or '').strip()
                    if not v:
                        continue
                    seg = v.lstrip('/')
                    url = f"{url}/{seg}"

            # 3) 分页
            if pg and str(pg) != '1':
                url = f"{url}/page/{pg}"

            self.log(f"构建的URL: {url}")
            return url
        except Exception as e:
            self.log(f"构建URL出错: {str(e)}")
            return f"{self.host}/movie_bt"

    # ==================================================================
    # 筛选配置
    # ==================================================================
    def _get_filters(self):
        cat_filter = {
            'key': 'caturl', 'name': '分类',
            'value': [
                {'n': '全部',         'v': ''},
                {'n': '分类筛选',     'v': '/movie_bt'},
                {'n': '最新电影',     'v': '/zuixindianying'},
                {'n': '豆瓣Top250',   'v': '/dbtop250'},
                {'n': '剧场版',       'v': '/dongmanjuchangban'},
                {'n': '国产剧',       'v': '/gcj'},
                {'n': '美剧',         'v': '/meijutt'},
                {'n': '韩剧',         'v': '/hanjutv'},
                {'n': '番剧',         'v': '/fanju'},
                {'n': '日剧',         'v': '/riju'},
                {'n': '海外剧',       'v': '/haiwaijuqita'},
                {'n': '电影',         'v': '/movie_bt_series/dyy'},
                {'n': '电视剧',       'v': '/movie_bt_series/dianshiju'},
                {'n': '动画',         'v': '/movie_bt_series/dohua'},
                {'n': '华语电影',     'v': '/movie_bt_series/huayudianying'},
                {'n': '欧美电影',     'v': '/movie_bt_series/meiguodianying'},
                {'n': '日本电影',     'v': '/movie_bt_series/ribendianying'},
                {'n': '韩国电影',     'v': '/movie_bt_series/hanguodianying'},
                {'n': '印度电影',     'v': '/movie_bt_series/yindudianying'},
                {'n': '俄罗斯电影',   'v': '/movie_bt_series/eluosidianying'},
                {'n': '加拿大电影',   'v': '/movie_bt_series/jianadadianying'},
                {'n': '站长推荐',     'v': '/movie_bt_series/zhanchangtuijian'},
                {'n': '会员专区',     'v': '/movie_bt_series/huiyuanzhuanqu'},
            ]
        }
        area_filter = {
            'key': 'areal', 'name': '地区',
            'value': [
                {'n': '全部',     'v': ''},
                {'n': '中国大陆', 'v': '/movie_bt_cat/zh'},
                {'n': '中国香港', 'v': '/movie_bt_cat/hk'},
                {'n': '中国台湾', 'v': '/movie_bt_cat/tw'},
                {'n': '美国',     'v': '/movie_bt_cat/meiguo'},
                {'n': '韩国',     'v': '/movie_bt_cat/hggggg'},
                {'n': '日本',     'v': '/movie_bt_cat/riben'},
                {'n': '英国',     'v': '/movie_bt_cat/yinguo'},
                {'n': '法国',     'v': '/movie_bt_cat/fg'},
                {'n': '德国',     'v': '/movie_bt_cat/dg'},
                {'n': '印度',     'v': '/movie_bt_cat/yidu'},
                {'n': '泰国',     'v': '/movie_bt_cat/taiguo'},
                {'n': '澳大利亚', 'v': '/movie_bt_cat/adly'},
                {'n': '其他',     'v': '/movie_bt_cat/qt'},
            ]
        }
        year_filter = {
            'key': 'yearl', 'name': '年份',
            'value': [
                {'n': '全部',         'v': ''},
                {'n': '2026',         'v': '/year/2026'},
                {'n': '2025',         'v': '/year/2025'},
                {'n': '2024',         'v': '/year/2024'},
                {'n': '2023',         'v': '/year/2023'},
                {'n': '2022',         'v': '/year/2022'},
                {'n': '2021',         'v': '/year/2021'},
                {'n': '2020',         'v': '/year/2020'},
                {'n': '2019',         'v': '/year/2019'},
                {'n': '2018',         'v': '/year/2018'},
                {'n': '2017',         'v': '/year/2017'},
                {'n': '2016',         'v': '/year/2016'},
                {'n': '2015',         'v': '/year/2015'},
                {'n': '2011~2010年代', 'v': '/year/20012010nd'},
                {'n': '1900~2000年代', 'v': '/year/19002000nd'},
            ]
        }
        tag_filter = {
            'key': 'tagl', 'name': '类型',
            'value': [
                {'n': '全部',     'v': ''},
                {'n': '动作',     'v': '/movie_bt_tags/dozuo'},
                {'n': '喜剧',     'v': '/movie_bt_tags/xiju'},
                {'n': '爱情',     'v': '/movie_bt_tags/aiqing'},
                {'n': '科幻',     'v': '/movie_bt_tags/kh'},
                {'n': '恐怖',     'v': '/movie_bt_tags/kubu'},
                {'n': '剧情',     'v': '/movie_bt_tags/juqing'},
                {'n': '悬疑',     'v': '/movie_bt_tags/xuanyi'},
                {'n': '惊悚',     'v': '/movie_bt_tags/kingsong'},
                {'n': '战争',     'v': '/movie_bt_tags/zhanzheng'},
                {'n': '犯罪',     'v': '/movie_bt_tags/fanzui'},
                {'n': '动画',     'v': '/movie_bt_tags/dhh'},
                {'n': '奇幻',     'v': '/movie_bt_tags/qihuan'},
                {'n': '冒险',     'v': '/movie_bt_tags/maoxian'},
                {'n': '历史',     'v': '/movie_bt_tags/lishi'},
                {'n': '家庭',     'v': '/movie_bt_tags/jiating'},
                {'n': '武侠',     'v': '/movie_bt_tags/wuxia'},
                {'n': '古装',     'v': '/movie_bt_tags/guzhuang'},
                {'n': '灾难',     'v': '/movie_bt_tags/zainan'},
                {'n': '纪录片',   'v': '/movie_bt_tags/jlpp'},
                {'n': '运动',     'v': '/movie_bt_tags/yd'},
                {'n': '音乐',     'v': '/movie_bt_tags/yy'},
                {'n': '西部',     'v': '/movie_bt_tags/xb'},
                {'n': '儿童',     'v': '/movie_bt_tags/etet'},
                {'n': '同性',     'v': '/movie_bt_tags/tongxing'},
                {'n': '歌舞',     'v': '/movie_bt_tags/gw'},
                {'n': '短片',     'v': '/movie_bt_tags/dp'},
                {'n': '传记',     'v': '/movie_bt_tags/chuanji'},
                {'n': '真人秀',   'v': '/movie_bt_tags/zrx'},
                {'n': '鬼怪',     'v': '/movie_bt_tags/%e9%ac%bc%e6%80%aa'},
            ]
        }

        full = [cat_filter, area_filter, year_filter, tag_filter]
        filters = {}
        for cid in ['movie_bt', 'zuixindianying', 'dbtop250', 'dongmanjuchangban',
                    'gcj', 'meijutt', 'hanjutv', 'fanju',
                    'riju', 'haiwaijuqita', 'dyy', 'guochanju', 'mj', 'hj', 'rj', 'hwj', 'fjj']:
            filters[cid] = full
        return filters

    # ==================================================================
    # 搜索相关性
    # ==================================================================
    def _is_relevant_search_result(self, title, search_key):
        if not title or not search_key:
            return False
        title_lower = title.lower()
        search_key_lower = search_key.lower()
        if search_key_lower in title_lower:
            return True
        search_chars = set(search_key_lower.replace(' ', ''))
        title_chars = set(title_lower.replace(' ', ''))
        if len(search_chars) > 0:
            match_ratio = len(search_chars & title_chars) / len(search_chars)
            if match_ratio >= 0.8:
                return True
        if len(search_key_lower) <= 2:
            return search_key_lower in title_lower
        return False

    # ==================================================================
    # 通用工具
    # ==================================================================
    def _get_text(self, doc, selectors):
        for selector in selectors:
            try:
                texts = doc.xpath(selector)
            except Exception:
                continue
            for text in texts:
                if text and str(text).strip():
                    return str(text).strip()
        return ''