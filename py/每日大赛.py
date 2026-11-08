# coding=utf-8
import json, time, ssl, re, base64, random, html as html_parser
from base.spider import Spider
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

class Spider(Spider):
    def getName(self):
        return "每日大赛"

    def init(self, extend=""):
        self.publish_urls = [
            "https://mrdsw13.com",
            "https://mrdsg7.com",
            "https://mrdsg2.com/",
            "https://mrds98.com/"
        ]
        self.ua = "Mozilla/5.0 (Linux; Android 16; 2510DRK44C Build/BP2A.250605.031.A3) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.192 Mobile Safari/537.36"
        self.headers = {
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self.session = requests.Session()
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
        except:
            pass
        self.aes_key = b"f5d965df75336270"
        self.aes_iv = b"97b60394abc2fbe1"
        self._resolve_domain()
        self.classes = [
            {"type_id": "mrds", "type_name": "每日大赛"},
            {"type_id": "aijc", "type_name": "AI剧场"},
            {"type_id": "ztds", "type_name": "主题大赛"},
            {"type_id": "rstt", "type_name": "热搜吃瓜"},
            {"type_id": "xazd", "type_name": "校园学生"},
            {"type_id": "blyp", "type_name": "必撸大赛"},
            {"type_id": "fctg", "type_name": "反差泄密"},
            {"type_id": "mhds", "type_name": "网红黑料"},
            {"type_id": "lqdp", "type_name": "猎奇重口"},
            {"type_id": "jdsj", "type_name": "AV看片"},
            {"type_id": "mxwh", "type_name": "明星大赛"},
            {"type_id": "smdh", "type_name": "动漫之家"},
            {"type_id": "dypd", "type_name": "影视国漫"},
            {"type_id": "mtds", "type_name": "cos写真"},
            {"type_id": "ysds", "type_name": "声控ASMR"},
            {"type_id": "czds", "type_name": "寸止挑战"},
            {"type_id": "hjds", "type_name": "混剪PMV"},
            {"type_id": "tgds", "type_name": "原创投稿"},
            {"type_id": "omjp", "type_name": "欧美精品"},
            {"type_id": "qwcs", "type_name": "全网参赛"},
            {"type_id": "archives", "type_name": "往期内容"},
            {"type_id": "tags", "type_name": "标签云"},
        ]

    def _resolve_domain(self):
        """
        域名自动获取逻辑：
        1. 轮询4个发布站，5秒超时
        2. 若返回JS跳转页，提取href得到真实发布站
        3. 从真实发布站源码提取Base64.decode(...)并解密
        4. 从解密内容提取 words.random() + '后缀'
        5. 随机5位字母前缀 + 后缀 构建真实域名
        """
        suffix = None
        for pub in self.publish_urls:
            try:
                r = self.session.get(pub, headers=self.headers, timeout=5, verify=False)
                if r.status_code != 200:
                    continue
                html = r.text
                real_pub_url = pub

                # 检测JS跳转页（如mrdsg2.com的自动跳转）
                jump_match = re.search(
                    r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>加载中',
                    html, re.I
                )
                if jump_match:
                    real_pub_url = jump_match.group(1)
                    r2 = self.session.get(real_pub_url, headers=self.headers, timeout=5, verify=False)
                    if r2.status_code == 200:
                        html = r2.text
                    else:
                        continue

                m = re.search(r"Base64\.decode\(['\"]([^'\"]+)['\"]\)", html)
                if not m:
                    m = re.search(r"atob\(['\"]([^'\"]+)['\"]\)", html)
                if not m:
                    continue
                encoded = m.group(1)
                try:
                    decoded = base64.b64decode(encoded).decode('utf-8', errors='ignore')
                except:
                    continue
                m2 = re.search(r"words\.random\(\)\s*\+\s*['\"]([^'\"]+)['\"]", decoded)
                if m2:
                    suffix = m2.group(1)
                    break
                m3 = re.search(r'\.[a-z0-9]{5,}\.(?:com|cc|net|org)', decoded)
                if m3:
                    suffix = m3.group(0)
                    break
            except Exception as e:
                print(f"[每日大赛] 发布页 {pub} 解析失败: {e}")
                continue
        if not suffix:
            suffix = ".umghsccl.cc"
        prefix = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=5))
        self.host = f"https://{prefix}{suffix}/"
        self.domains = [self.host]
        if suffix != ".umghsccl.cc":
            print(f"[每日大赛] 域名解析成功: {self.host}")
        else:
            print(f"[每日大赛] 使用保底域名: {self.host}")
    def _decode_page(self, html):
        if not html:
            return ''
        max_rounds = 5
        for _ in range(max_rounds):
            m = re.search(r"Base64\.decode\(['\"]([^'\"]+)['\"]\)", html)
            if not m:
                break
            try:
                decoded = base64.b64decode(m.group(1)).decode('utf-8', 'ignore')
                html = html.replace(m.group(0), f"'{decoded}'")
            except Exception:
                break
        return html

    def _req(self, url):
        try:
            r = self.session.get(url, headers=self.headers, timeout=15, verify=False)
            if r.status_code == 200:
                html = r.text
                html = self._decode_page(html)
                j = re.search(r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>加载中', html, re.I)
                if j:
                    new_url = j.group(1)
                    return self._req(new_url)
                return html
        except Exception as e:
            print(f"[每日大赛] req error: {e}")
        return ""

    def _aes_img(self, data):
        if not data:
            return ""
        if data.startswith("http"):
            return self.getProxyUrl() + "&url=" + self.e64(data) + "&type=img"
        try:
            raw = base64.b64decode(data)
            cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_iv)
            raw = unpad(cipher.decrypt(raw), AES.block_size)
            return "data:image/jpeg;base64," + base64.b64encode(raw).decode('utf-8')
        except:
            return ""

    def _fix_url(self, url):
        if not url:
            return ""
        url = url.replace('\\/', '/').replace('&amp;', '&')
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('/'):
            return self.host.rstrip('/') + url
        if url.startswith('http'):
            return url
        return url

    def _clean_html(self, text):
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()

    def _parse_article_list(self, html):
        result = []
        blocks = re.findall(r'<article\b[\s\S]*?</article>', html, re.I)
        if not blocks:
            blocks = re.findall(r'<div[^>]+class=["\'][^"\']*brick[^"\']*["\'][\s\S]*?</div>', html, re.I)
        for block in blocks:
            if 'sponsored nofollow' in block or 'ad-item' in block:
                continue
            link = self._fix_url(self._extract_one(block, r'<a[^>]+href=["\']([^"\']+)["\']'))
            title = self._extract_one(block, r'itemprop=["\']headline["\'][^>]*>([\s\S]*?)</h\d>')
            if not title:
                title = self._extract_one(block, r'<h\d[^>]*>([\s\S]*?)</h\d>')
            title = self._clean_html(title)
            if not link or not title or title == '加载中...':
                continue
            img_data = self._extract_one(block, r"loadBannerDirect\(['\"]([^'\"]+)['\"]")
            pic = self._aes_img(img_data) if img_data else ""
            if not pic:
                pic = self._extract_one(block, r'(?:data-original|src|content)=["\']([^"\']+\.(?:jpg|jpeg|png|webp|gif)[^"\']*)')
                pic = self._fix_url(pic)
            remarks = self._extract_one(block, r'dateModified[^>]+content=["\']([^"\']+)')
            if not remarks:
                remarks = self._extract_one(block, r'datePublished[^>]+content=["\']([^"\']+)')
            if not remarks:
                remarks = self._extract_one(block, r'<span[^>]+class=["\'][^"\']*time[^"\']*["\'][^>]*>([\s\S]*?)</span>')
            remarks = self._clean_html(remarks)[:20]
            result.append({
                "vod_id": link,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remarks
            })
        return result

    def _parse_archives(self, html):
        result = []
        default_pic = "https://img2.baidu.com/it/u=4291927119,3438962678&fm=253&fmt=auto&app=138&f=JPEG?w=500&h=500"
        blocks = re.findall(r'<div[^>]+class=["\'][^"\']*brick[^"\']*["\'][^>]*>[\s\S]*?</div>', html, re.I)
        for block in blocks:
            link = self._fix_url(self._extract_one(block, r'<a[^>]+href=["\']([^"\']+)["\']'))
            title = self._clean_html(self._extract_one(block, r'<a[^>]*>([\s\S]*?)</a>'))
            title = re.sub(r'^\d{1,2}-\d{1,2}\s*', '', title)
            if not link or not title:
                continue
            remarks = self._clean_html(self._extract_one(block, r'<span[^>]+class=["\'][^"\']*time[^"\']*["\'][^>]*>([\s\S]*?)</span>'))
            result.append({
                "vod_id": link,
                "vod_name": title,
                "vod_pic": default_pic,
                "vod_remarks": remarks
            })
        return result

    def _parse_tags(self, html):
        result = []
        default_pic = "https://img2.baidu.com/it/u=4291927119,3438962678&fm=253&fmt=auto&app=138&f=JPEG?w=500&h=500"
        for link, title in re.findall(r'<a[^>]+class=["\'][^"\']*itags[^"\']*["\'][^>]+href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>', html, re.I):
            title = self._clean_html(title)
            link = self._fix_url(link)
            if not link or not title:
                continue
            result.append({
                "vod_id": f"folder${link}",
                "vod_name": title,
                "vod_pic": default_pic,
                "vod_remarks": "二级目录",
                "vod_tag": "folder"
            })
        return result

    def _extract_one(self, html, pattern):
        m = re.search(pattern, html, re.I | re.S)
        return m.group(1) if m else ""

    def _parse_ext(self, ext):
        if not ext:
            return {}
        if isinstance(ext, dict):
            return ext
        if isinstance(ext, str):
            ext = ext.strip()
            if not ext or ext in ("{}", "null", "undefined"):
                return {}
            try:
                return json.loads(ext)
            except:
                result = {}
                for part in ext.split("&"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        result[k] = v
                return result
        return {}

    def _extract_max_page(self, html):
        pagination = re.search(r'<ul[^>]*class="pagination"[^>]*>(.*?)</ul>', html, re.DOTALL)
        if not pagination:
            pagination = re.search(r'<ul[^>]*class="page-navigator"[^>]*>(.*?)</ul>', html, re.DOTALL)
        if pagination:
            pages = re.findall(r'href="[^"]*?(?:page/|/)(\d+)(?:/|"|>)', pagination.group(1))
            if pages:
                return max(int(p) for p in pages)
        return 1

    # ---------- 接口实现 ----------
    def homeContent(self, filter):
        html = self._req(self.host)
        vods = self._parse_article_list(html)
        return {
            "class": self.classes,
            "list": vods[:20],
            "filters": {}
        }

    def homeVideoContent(self):
        html = self._req(self.host)
        return {"list": self._parse_article_list(html)[:20]}

    def categoryContent(self, cid, pg, filter, ext):
        pg = int(pg) if str(pg).isdigit() else 1
        html = ""
        vods = []
        if isinstance(cid, str) and cid.startswith("folder$"):
            base = cid.split("$", 1)[1].rstrip('/')
            url = base + '/' if pg == 1 else base + f'/{pg}/'
            html = self._req(url)
            vods = self._parse_article_list(html)
        elif cid == "archives":
            url = f"{self.host}archives/page/{pg + 1}/"
            html = self._req(url)
            vods = self._parse_archives(html)
        elif cid == "tags":
            url = f"{self.host}tags/{pg}/"
            html = self._req(url)
            vods = self._parse_tags(html)
        else:
            if pg == 1:
                url = f"{self.host}category/{cid}/"
            else:
                url = f"{self.host}category/{cid}/{pg}/"
            html = self._req(url)
            vods = self._parse_article_list(html)

        pc = self._extract_max_page(html) if html else 1
        limit = len(vods) if vods else 24
        total = pc * limit
        return {
            "list": vods,
            "page": pg,
            "pagecount": pc,
            "limit": limit,
            "total": total
        }

    def detailContent(self, ids):
        url = ids[0]
        if url.startswith("folder$"):
            return {"list": []}
        html = self._req(url)
        if not html:
            return {"list": []}

        # 标题
        title = self._clean_html(self._extract_one(html, r'<h1[^>]*>([\s\S]*?)</h1>'))
        if not title:
            title = self._clean_html(self._extract_one(html, r'itemprop=["\']headline["\'][^>]*>([\s\S]*?)</h\d>'))
        if not title:
            title = "每日大赛"

        # 封面图
        img_data = self._extract_one(html, r"loadBannerDirect\(['\"]([^'\"]+)['\"]")
        pic = self._aes_img(img_data) if img_data else ""

        # 简介
        desc = self._clean_html(self._extract_one(html, r'</blockquote>\s*<p>([\s\S]*?)</p>'))
        if not desc:
            desc = self._clean_html(self._extract_one(html, r'<div[^>]+class=["\'][^"\']*post-content[^"\']*["\'][^>]*>([\s\S]*?)</div>'))

        # ===== 播放地址提取（精确模式） =====
        play_urls = []
        # 模式1：mutex:true 中的 video.url（最精确，优先）
        pattern1 = r'"mutex"\s*:\s*true[\s\S]*?"video"\s*:\s*\{\s*"url"\s*:\s*"([^"]+)"'
        for m in re.finditer(pattern1, html, re.I):
            play_urls.append(self._fix_url(m.group(1).replace('\\/', '/')))

        # 如果模式1没有匹配到，使用备选模式（兼容旧页面）
        if not play_urls:
            # 模式2：video: { url: "..." }
            pattern2 = r'video\s*:\s*\{\s*url\s*:\s*["\']([^"\']+)'
            for m in re.finditer(pattern2, html, re.I):
                play_urls.append(self._fix_url(m.group(1).replace('\\/', '/')))

            # 模式3：直接匹配 .m3u8 或 .mp4
            pattern3 = r'(https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*)'
            for m in re.finditer(pattern3, html, re.I):
                play_urls.append(self._fix_url(m.group(1).replace('\\/', '/')))

            # 额外：var now / playurl
            for pattern in [
                r'var\s+now\s*=\s*["\']([^"\']+)["\']',
                r'var\s+playurl\s*=\s*["\']([^"\']+)["\']'
            ]:
                for m in re.finditer(pattern, html, re.I):
                    play_urls.append(self._fix_url(m.group(1).replace('\\/', '/')))

        # 去重
        seen = set()
        unique = []
        for u in play_urls:
            if u and u not in seen:
                seen.add(u)
                unique.append(u)

        play_from = "自动档" if unique else ""
        play_url_str = "#".join([f"第{i+1}集${u}" for i, u in enumerate(unique)])

        return {
            "list": [{
                "vod_id": url,
                "vod_name": title,
                "vod_pic": pic,
                "vod_content": desc,
                "vod_play_from": play_from,
                "vod_play_url": play_url_str
            }]
        }

    def searchContent(self, key, quick, pg='1'):
        pg = int(pg) if str(pg).isdigit() else 1
        url = f"{self.host}search/{key}/" if pg == 1 else f"{self.host}search/{key}/page/{pg}/"
        html = self._req(url)
        vods = self._parse_article_list(html)
        pc = self._extract_max_page(html) if html else 1
        limit = len(vods) if vods else 24
        total = pc * limit
        return {
            "list": vods,
            "page": pg,
            "pagecount": pc,
            "limit": limit,
            "total": total
        }

    def playerContent(self, flag, id, vipFlags):
        if id.startswith("http") and (".m3u8" in id or ".mp4" in id):
            return {"parse": 0, "url": id, "header": json.dumps(self.headers, ensure_ascii=False)}
        html = self._req(id)
        if html:
            for pattern in [
                r'"mutex"\s*:\s*true[\s\S]*?"video"\s*:\s*\{\s*"url"\s*:\s*"([^"]+)"',
                r'var\s+now\s*=\s*["\']([^"\']+)["\']',
                r'var\s+playurl\s*=\s*["\']([^"\']+)["\']',
                r'(https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*)',
                r'<video[^>]+src=["\']([^"\']+)["\']',
                r'<source[^>]+src=["\']([^"\']+)["\']',
            ]:
                m = re.search(pattern, html, re.I | re.S)
                if m:
                    u = self._fix_url(m.group(1).replace('\\/', '/'))
                    return {"parse": 0, "url": u, "header": json.dumps(self.headers, ensure_ascii=False)}
        return {"parse": 0, "url": id, "header": json.dumps(self.headers, ensure_ascii=False)}

    def localProxy(self, param):
        if param.get("type") == "img":
            try:
                url = self.d64(param.get("url", ""))
                if not url:
                    return [404, "text/plain", "", ""]
                res = requests.get(url, headers=self.headers, timeout=10, verify=False)
                if res.status_code == 200:
                    content = res.content
                    try:
                        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_iv)
                        content = unpad(cipher.decrypt(content), AES.block_size)
                    except:
                        pass
                    return [200, res.headers.get("Content-Type", "image/jpeg"), content, {}]
            except Exception as e:
                print(f"[每日大赛] localProxy img error: {e}")
            return [404, "text/plain", "", ""]
        return [404, "text/plain", "", ""]

    def e64(self, text):
        try:
            return base64.b64encode(text.encode("utf-8")).decode("utf-8")
        except:
            return ""

    def d64(self, encoded_text):
        try:
            return base64.b64decode(encoded_text.encode("utf-8")).decode("utf-8")
        except:
            return ""