# -*- coding: utf-8 -*-
# 专属全网聚合 Python版
# 适配常见 TVBox ok影视 鱼壳影视 羊壳PeekPro

import json
from urllib.parse import urlparse, quote

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from base.spider import Spider


class Spider(Spider):
    sources = {
        's1': {'name': '🎬电影天堂', 'api': 'http://caiji.dyttzyapi.com/api.php/provide/vod/from/dyttm3u8/at/json'},
        's2': {'name': '💧无水印', 'api': 'https://api.wsyzy.net/api.php/provide/vod'},
        's3': {'name': '🧸量子', 'api': 'https://cj.lziapi.com/api.php/provide/vod'},
        's4': {'name': '📺1080资源', 'api': 'https://api.1080zyku.com/inc/api_mac10.php'},
        's5': {'name': '🔥155资源', 'api': 'https://155api.com/api.php/provide/vod'},
        's6': {'name': '📺天涯', 'api': 'https://tyyszy.com/api.php/provide/vod/'},
        's7': {'name': '📺暴风', 'api': 'https://bfzyapi.com/api.php/provide/vod/'},
        's8': {'name': '⚡索尼闪电', 'api': 'https://xsd.sdzyapi.com/api.php/provide/vod/'},
        's9': {'name': '📺索尼', 'api': 'https://suoniapi.com/api.php/provide/vod/'},
        's10': {'name': '📺红牛', 'api': 'https://www.hongniuzy2.com/api.php/provide/vod/'},
        's11': {'name': '📺茅台', 'api': 'https://caiji.maotaizy.cc/api.php/provide/vod/'},
        's12': {'name': '🐯虎牙', 'api': 'https://www.huyaapi.com/api.php/provide/vod/'},
        's13': {'name': '📺豆瓣', 'api': 'https://caiji.dbzy.tv/api.php/provide/vod/'},
        's14': {'name': '📺豆瓣2', 'api': 'https://dbzy.tv/api.php/provide/vod/'},
        's15': {'name': '📺豪华', 'api': 'https://hhzyapi.com/api.php/provide/vod/'},
        's16': {'name': '📺如意影视', 'api': 'https://cj.rycjapi.com/api.php/provide/vod/'},
        's17': {'name': '📺U酷', 'api': 'https://api.ukuapi.com/api.php/provide/vod'},
        's18': {'name': '📺ikun', 'api': 'https://ikunzyapi.com/api.php/provide/vod'},
        's19': {'name': '📺无尽', 'api': 'https://api.wujinapi.cc/api.php/provide/vod'},
        's20': {'name': '🌕光速', 'api': 'https://api.guangsuapi.com/api.php/provide/vod'},
        's21': {'name': '📺卧龙', 'api': 'https://collect.wolongzyw.com/api.php/provide/vod'},
        's22': {'name': '📺新浪', 'api': 'https://api.xinlangapi.com/xinlangapi.php/provide/vod'},
        's23': {'name': '📺旺旺', 'api': 'https://api.wwzy.tv/api.php/provide/vod'},
        's24': {'name': '📺最大', 'api': 'https://api.zuidapi.com/api.php/provide/vod'},
        's25': {'name': '🌸樱花', 'api': 'https://m3u8.apiyhzy.com/api.php/provide/vod'},
        's26': {'name': '🐮牛牛', 'api': 'https://api.niuniuzy.me/api.php/provide/vod'},
        's27': {'name': '☁️百度云', 'api': 'https://api.apibdzy.com/api.php/provide/vod'},
        's28': {'name': '🏎速播', 'api': 'https://subocaiji.com/api.php/provide/vod'},
        's29': {'name': '🦅金鹰', 'api': 'https://jinyingzy.com/api.php/provide/vod'},
        's30': {'name': '⚡闪电', 'api': 'https://sdzyapi.com/api.php/provide/vod'},
        's31': {'name': '👑非凡', 'api': 'https://cj.ffzyapi.com/api.php/provide/vod'},
        's32': {'name': '🍃飘零', 'api': 'https://p2100.net/api.php/provide/vod'},
        's33': {'name': '🐾魔爪', 'api': 'https://mozhuazy.com/api.php/provide/vod'},
        's34': {'name': '📺魔都', 'api': 'https://www.mdzyapi.com/api.php/provide/vod'},
        's35': {'name': '📺西瓜资源', 'api': 'https://caiji.xgzyapi.com/api.php/provide/vod/'},
        's36': {'name': '📺98资源', 'api': 'https://98zy.vip/api.php/provide/vod/'},
        's37': {'name': '🦊火狐影视', 'api': 'https://hhzyapi.com/api.php/provide/vod/'},
        's38': {'name': '📺大众资源', 'api': 'https://cdn.dzzyapi.com/api.php/provide/vod/'},
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    # ==================== 海报相关配置 ====================
    # 图片代理前缀：留空 "" 表示不使用代理（默认）
    # 若大量源海报 403/防盗链，可填公共代理或自建代理，例如：
    #   "https://images.weserv.nl/?url="
    # 注意：使用代理时传入的 url 不能带协议头（下面代码已自动处理）
    IMG_PROXY = ""

    # 是否强制 http -> https（Android 9+ 默认禁止明文图片，建议 True）
    # 若某些图床只支持 http，转 https 后会 404，可改为 False
    FORCE_HTTPS = True

    # 海报为空时的兜底图（留空则使用空字符串）
    DEFAULT_PIC = ""
    # =====================================================

    def getName(self):
        return "影视+专属全网聚合"

    def init(self, extend=""):
        pass

    def fetch(self, url, timeout=8):
        try:
            r = requests.get(
                url,
                headers=self.headers,
                timeout=timeout,
                verify=False
            )
            return r.text
        except Exception:
            return ""

    # ---------------------------------------------------------------
    # 海报地址修复：相对路径 / 协议缺失 / http 明文 / 转义符 / 中文空格
    # ---------------------------------------------------------------
    def fix_pic(self, pic, api=""):
        if not pic:
            return self.DEFAULT_PIC

        pic = str(pic).strip()

        # 1. 去掉 json 转义产生的反斜杠、换行、制表符
        pic = (pic.replace("\\", "")
                  .replace("\n", "")
                  .replace("\r", "")
                  .replace("\t", "")
                  .replace(" ", "")
                  .strip())

        # 2. 无效值过滤
        if not pic or pic.lower() in ("null", "none", "undefined", "false", "0"):
            return self.DEFAULT_PIC

        # 3. 某些源返回 "url1,url2,url3"，取第一个
        if "," in pic and ("http" in pic or pic.startswith("//")):
            pic = pic.split(",")[0].strip()

        # 4. 补全协议
        if pic.startswith("//"):
            # 协议相对：//img.xxx.com/a.jpg
            pic = "http:" + pic

        elif pic.startswith("/"):
            # 根路径相对：/upload/vod/a.jpg -> 拼上接口域名
            try:
                p = urlparse(api)
                if p.netloc:
                    pic = f"{p.scheme or 'http'}://{p.netloc}{pic}"
            except Exception:
                pass

        elif not pic.lower().startswith(("http://", "https://", "data:", "file:")):
            # 既没协议也不是路径：img.xxx.com/a.jpg
            pic = "http://" + pic

        # 5. http -> https（规避 TVBox Android9+ 明文图片拦截）
        if self.FORCE_HTTPS and pic.startswith("http://"):
            pic = "https://" + pic[7:]

        # 6. 中文 / 空格 等 URL 编码（保留已有 %xx 不二次编码）
        try:
            pic = quote(pic, safe=":/?&=#%[]@!$'()*+,;~")
        except Exception:
            pass

        # 7. 走图片代理（解决防盗链 403）
        if self.IMG_PROXY:
            try:
                # 代理通常不接受协议头，去掉 http(s)://
                no_scheme = pic.split("://", 1)[-1]
                pic = self.IMG_PROXY + quote(no_scheme, safe="")
            except Exception:
                pass

        return pic

    def clean_item(self, item, source_key, source_name, is_detail=False):
        item = dict(item)

        if not is_detail:
            item["vod_id"] = f"{source_key}@@{item.get('vod_id', '')}"

        # ---------- 海报修复（核心） ----------
        api = self.sources.get(source_key, {}).get("api", "")
        raw_pic = (
            item.get("vod_pic")
            or item.get("vod_pic_thumb")
            or item.get("vod_pic_slide")
            or item.get("pic")
            or ""
        )
        item["vod_pic"] = self.fix_pic(raw_pic, api)
        # 部分版本还会读 vod_pic_thumb，一并同步，避免空白
        item["vod_pic_thumb"] = item["vod_pic"]
        # --------------------------------------

        remarks = item.get("vod_remarks", "")
        item["vod_remarks"] = f"{source_name} | {remarks}"

        if item.get("vod_play_from"):
            froms = item["vod_play_from"].split("$$$")
            froms = [f"{source_name}-{x}" for x in froms]
            item["vod_play_from"] = "$$$".join(froms)

        item.pop("vod_down_from", None)
        item.pop("vod_down_url", None)

        return item

    def homeContent(self, filter):
        classes = []
        filters = {}

        def load_class(key, source):
            url = f"{source['api']}?ac=list"
            html = self.fetch(url, 4)

            try:
                data = json.loads(html)
            except Exception:
                data = {}

            vals = [{"n": "全部(最新)", "v": ""}]

            for c in data.get("class", []):
                vals.append({
                    "n": c.get("type_name", ""),
                    "v": c.get("type_id", "")
                })

            return key, vals

        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = []

            for key, source in self.sources.items():
                classes.append({
                    "type_id": key,
                    "type_name": source["name"]
                })

                futures.append(executor.submit(load_class, key, source))

            for future in as_completed(futures):
                try:
                    key, vals = future.result()

                    filters[key] = [{
                        "key": "cateId",
                        "name": "分类",
                        "value": vals
                    }]
                except Exception:
                    pass

        return {
            "class": classes,
            "filters": filters,
            "list": []
        }

    def categoryContent(self, tid, pg, filter, extend):
        if tid not in self.sources:
            return {"list": []}

        source = self.sources[tid]

        cate_id = ""
        if isinstance(extend, dict):
            cate_id = extend.get("cateId", "")

        url = f"{source['api']}?ac=detail&pg={pg}"

        if cate_id:
            url += f"&t={cate_id}"

        html = self.fetch(url)

        try:
            data = json.loads(html)
        except Exception:
            data = {}

        result = []

        for item in data.get("list", []):
            result.append(
                self.clean_item(
                    item,
                    tid,
                    source["name"],
                    False
                )
            )

        return {
            "list": result,
            "page": data.get("page", pg),
            "pagecount": data.get("pagecount", 1),
            "limit": data.get("limit", 20),
            "total": data.get("total", len(result))
        }

    def detailContent(self, ids):
        if isinstance(ids, list):
            ids = ids[0]

        if "@@" not in ids:
            return {"list": []}

        source_key, real_id = ids.split("@@", 1)

        if source_key not in self.sources:
            return {"list": []}

        source = self.sources[source_key]

        url = f"{source['api']}?ac=detail&ids={real_id}"

        html = self.fetch(url)

        try:
            data = json.loads(html)
        except Exception:
            data = {}

        result = []

        for item in data.get("list", []):
            cleaned = self.clean_item(
                item,
                source_key,
                source["name"],
                True
            )

            cleaned["vod_id"] = ids

            result.append(cleaned)

        return {"list": result}

    def search_one(self, source_key, source, keyword, pg):
        url = f"{source['api']}?ac=detail&wd={keyword}&pg={pg}"

        html = self.fetch(url, 6)

        try:
            data = json.loads(html)
        except Exception:
            data = {}

        result = []

        for item in data.get("list", []):
            result.append(
                self.clean_item(
                    item,
                    source_key,
                    source["name"],
                    False
                )
            )

        return {
            "list": result,
            "pagecount": data.get("pagecount", 1)
        }

    def searchContent(self, key, quick=False, pg=1):
        result = []
        max_page = 1

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []

            for source_key, source in self.sources.items():
                futures.append(
                    executor.submit(
                        self.search_one,
                        source_key,
                        source,
                        key,
                        pg
                    )
                )

            for future in as_completed(futures):
                try:
                    data = future.result()

                    result.extend(data["list"])

                    if data["pagecount"] > max_page:
                        max_page = data["pagecount"]

                except Exception:
                    pass

        return {
            "list": result,
            "page": pg,
            "pagecount": max_page,
            "limit": 40,
            "total": 9999
        }

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "playUrl": "",
            "url": id,
            "header": self.headers
        }

    def localProxy(self, param):
        return [200, "text/plain", "ok"]


if __name__ == "__main__":
    Spider().run()