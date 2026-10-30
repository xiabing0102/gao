# -*- coding: utf-8 -*-
# 影视大全 iysdq1.com

import sys
import re
import json
from urllib.parse import urljoin, quote

sys.path.append("..")

try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def fetch(self, url, headers=None, **kw):
            import requests as rq
            kw.pop("timeout", None)
            response = rq.get(url, headers=headers, timeout=15, **kw)
            response.encoding = "utf-8"
            return response

HOST = "https://www.iysdq1.com"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)

CATEGORIES = {
    "1": "电影",
    "2": "电视剧",
    "3": "综艺",
    "4": "动漫",
    "5": "短剧",
}

FILTER_OPTIONS = {
    "movie_class": [
        "动作片", "喜剧片", "科幻片", "恐怖片", "爱情片", "剧情片",
        "战争片", "记录片", "动画片", "惊悚", "犯罪", "悬疑",
        "冒险", "奇幻", "家庭", "历史", "传记", "古装",
        "音乐", "同性", "运动", "武侠", "短片", "歌舞",
        "西部", "儿童", "灾难", "戏曲", "真人秀", "青春",
    ],
    "area": [
        "大陆", "香港", "台湾", "美国", "日本", "韩国", "英国",
        "法国", "德国", "意大利", "西班牙", "俄罗斯", "加拿大",
        "印度", "泰国", "其它", "新加坡", "菲律宾", "澳大利亚",
        "土耳其", "瑞典", "巴西", "荷兰", "印度尼西亚", "挪威",
        "智利", "爱尔兰", "伊朗", "蒙古",
    ],
    "lang": [
        "国语", "粤语", "闽南语", "英语", "韩语",
        "日语", "法语", "德语", "其它",
    ],
    "letter": list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["0-9"],
}

CATEGORY_CLASSES = {
    "1": FILTER_OPTIONS["movie_class"],
    "2": [
        "国产剧", "港剧", "台剧", "日剧", "韩剧", "欧美剧",
        "泰剧", "其他",
    ],
    "3": [
        "大陆综艺", "港台综艺", "日韩综艺", "欧美综艺", "真人秀",
        "纪录片", "脱口秀", "音乐", "歌舞", "相声", "喜剧",
        "爱情", "历史", "运动", "冒险", "剧情", "访谈", "旅游",
        "悬疑", "家庭", "短片", "同性", "动作", "儿童", "惊悚",
        "美食",
    ],
    "4": [
        "国产动漫", "日韩动漫", "欧美动漫", "港台动漫", "海外动漫",
        "动画", "喜剧", "剧情", "奇幻", "冒险", "动作", "科幻",
        "爱情", "儿童", "家庭", "短片", "悬疑", "运动", "古装",
        "武侠", "音乐", "犯罪", "惊悚", "战争", "恐怖", "历史",
        "搞笑", "歌舞", "热血",
    ],
    "5": [
        "女频恋爱", "反转爽剧", "古装仙侠", "年代穿越",
        "脑洞悬疑", "现代都市",
    ],
}

FILTERS = {
    tid: [
        {
            "key": "class",
            "name": "类型",
            "value": [
                {"n": "全部", "v": ""},
                *[{"n": v, "v": v} for v in CATEGORY_CLASSES[tid]],
            ],
        },
        {
            "key": "area",
            "name": "地区",
            "value": [
                {"n": "全部", "v": ""},
                *[{"n": v, "v": v} for v in FILTER_OPTIONS["area"]],
            ],
        },
        {
            "key": "year",
            "name": "年份",
            "value": [
                {"n": "全部", "v": ""},
                *[{"n": str(y), "v": str(y)} for y in range(2026, 1999, -1)],
            ],
        },
        {
            "key": "lang",
            "name": "语言",
            "value": [
                {"n": "全部", "v": ""},
                *[{"n": v, "v": v} for v in FILTER_OPTIONS["lang"]],
            ],
        },
        {
            "key": "letter",
            "name": "字母",
            "value": [
                {"n": "全部", "v": ""},
                *[{"n": v, "v": v} for v in FILTER_OPTIONS["letter"]],
            ],
        },
        {
            "key": "by",
            "name": "排序",
            "value": [
                {"n": "默认", "v": ""},
                {"n": "按最新", "v": "time"},
                {"n": "按最热", "v": "hits"},
                {"n": "按评分", "v": "score"},
            ],
        },
    ]
    for tid in CATEGORIES
}


class Spider(Spider):

    def init(self, extend=""):
        global HOST
        if extend and extend.startswith("http"):
            HOST = extend.rstrip("/")

    def homeContent(self, filter=False):
        result = {
            "class": [
                {"type_id": k, "type_name": v}
                for k, v in CATEGORIES.items()
            ],
            "list": [],
        }
        if filter:
            result["filters"] = FILTERS
        return result

    def homeVideoContent(self):
        try:
            response = self.fetch(HOST, headers={"User-Agent": UA}, timeout=15)
            html = response.text if hasattr(response, "text") else str(response)
            return {"list": self._items(html)}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg=1, filter=False, extend=""):
        try:
            page = max(int(str(pg)), 1)
        except Exception:
            page = 1

        category_id = str(tid)
        if category_id not in CATEGORIES:
            category_id = "1"

        try:
            url = self._category_url(category_id, page, extend)
            response = self.fetch(url, headers={"User-Agent": UA}, timeout=15)
            html = response.text if hasattr(response, "text") else str(response)
            items = self._items(html)
            return {
                "page": page,
                "pagecount": self._pagecount(html, page),
                "limit": 40,
                "total": len(items),
                "list": items,
            }
        except Exception:
            return {
                "page": page,
                "pagecount": 1,
                "limit": 40,
                "total": 0,
                "list": [],
            }

    def detailContent(self, ids):
        if isinstance(ids, list):
            video_id = ids[0] if ids else ""
        else:
            video_id = str(ids) if ids else ""

        match = re.search(r"(\d+)", str(video_id))
        video_id = match.group(1) if match else ""

        if not video_id:
            return {"list": []}

        try:
            response = self.fetch(
                f"{HOST}/voddetail/{video_id}.html",
                headers={"User-Agent": UA},
                timeout=15,
            )
            html = response.text if hasattr(response, "text") else str(response)
        except Exception:
            return {"list": []}

        detail = {
            "vod_id": video_id,
            "vod_name": "",
            "vod_pic": "",
            "vod_year": "",
            "vod_area": "",
            "vod_class": "",
            "vod_director": "",
            "vod_actor": "",
            "vod_content": "",
            "vod_remarks": "",
            "vod_play_from": "",
            "vod_play_url": "",
        }

        # 标题
        title_match = re.search(r'class="this-desc-title">([^<]+)<', html)
        if not title_match:
            title_match = re.search(r"<title>(.*?)</title>", html)
            if title_match:
                detail["vod_name"] = (
                    title_match.group(1)
                    .split("-")[0]
                    .replace("免费在线观看", "")
                    .replace("高清完整版", "")
                    .strip()
                )
        if title_match and not detail["vod_name"]:
            detail["vod_name"] = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()

        # 封面
        picture_match = re.search(
            r"background-image:\s*url\(['\"]?(https?://[^'\")]+)", html
        )
        if not picture_match:
            picture_match = re.search(
                r'data-src="(https?://[^"]+\.(?:jpg|jpeg|png|webp))"',
                html,
                re.IGNORECASE,
            )
        if picture_match:
            detail["vod_pic"] = picture_match.group(1)

        # 简介
        desc_match = re.search(
            r'<meta name="description" content="([^"]*)"', html, re.IGNORECASE
        )
        if not desc_match:
            desc_match = re.search(
                r'class="[^"]*this-desc[^"]*"[^>]*>([\s\S]*?)</div>',
                html,
                re.IGNORECASE,
            )
        if desc_match:
            detail["vod_content"] = re.sub(
                r"\s+", " ", re.sub(r"<[^>]+>", "", desc_match.group(1))
            ).strip()[:500]

        # 年份/地区/状态
        info_match = re.search(
            r'class="this-desc-info"[^>]*>([\s\S]*?)</div>', html, re.IGNORECASE
        )
        if info_match:
            info = info_match.group(1)
            year_match = re.search(r"(\d{4})", info)
            if year_match:
                detail["vod_year"] = year_match.group(1)
            remark_match = re.search(r"更新[至到]?([^<]+)", info)
            if remark_match:
                detail["vod_remarks"] = remark_match.group(1).strip()

        # 类型
        class_match = re.search(
            r'class="[^"]*this-desc-tags[^"]*"[^>]*>([\s\S]*?)</div>',
            html,
            re.IGNORECASE,
        )
        if class_match:
            detail["vod_class"] = re.sub(
                r"\s+", " ", re.sub(r"<[^>]+>", "", class_match.group(1))
            ).strip().rstrip("，").strip()

        # 导演/演员
        director_match = re.search(
            r"导演:</strong>([\s\S]*?)</div>", html, re.IGNORECASE
        )
        if director_match:
            detail["vod_director"] = ",".join(
                re.findall(r">([^<>]{1,30})</a>", director_match.group(1))
            )
        actor_match = re.search(
            r"演员:</strong>([\s\S]*?)</div>", html, re.IGNORECASE
        )
        if actor_match:
            detail["vod_actor"] = ",".join(
                re.findall(r">([^<>]{1,30})</a>", actor_match.group(1))
            )

        # 播放线路
        try:
            play_from = []
            play_urls = []

            # 线路名
            tab_match = re.search(
                r'<div class="anthology-tab[^>]*>(.*?)</div>\s*</div>', html, re.S
            )
            tabs = re.findall(
                r"&nbsp;([\u4e00-\u9fffA-Za-z]+线)",
                tab_match.group(1) if tab_match else "",
            )

            # 每个线路的剧集盒
            boxes = re.findall(
                r'<div class=["\']?anthology-list-box[^>]*>(.*?)</div>\s*</div>',
                html,
                re.S,
            )

            for tab_name, box in zip(tabs, boxes):
                links = re.findall(
                    r'href="(/vodplay/\d+-\d+-\d+\.html)"[^>]*>([\s\S]*?)</a>',
                    box,
                )
                if not links:
                    continue
                episodes = []
                for href, name in links:
                    ep_name = re.sub(r"<[^>]+>", "", name).strip()
                    episodes.append(f"{ep_name}${urljoin(HOST, href)}")
                if episodes:
                    play_from.append(tab_name)
                    play_urls.append("#".join(episodes))

            # 兜底：直接抓 vodplay 链接
            if not play_from:
                links = re.findall(
                    r'href="(/vodplay/\d+-(\d+)-(\d+)\.html)"[^>]*>([^<]+)</a>',
                    html,
                )
                routes = {}
                for href, route, episode, name in links:
                    routes.setdefault(route, []).append(
                        f"{name.strip()}${urljoin(HOST, href)}"
                    )
                for route in sorted(
                    routes, key=lambda v: int(v) if v.isdigit() else 999
                ):
                    idx = len(play_from)
                    route_name = tabs[idx] if idx < len(tabs) else f"线路{route}"
                    play_from.append(route_name)
                    play_urls.append("#".join(routes[route]))

            if play_from:
                detail["vod_play_from"] = "$$$".join(play_from)
                detail["vod_play_url"] = "$$$".join(play_urls)
        except Exception:
            pass

        return {"list": [detail]}

    def searchContent(self, key, quick=False, pg="1"):
        try:
            page = max(int(str(pg)), 1)
        except Exception:
            page = 1

        try:
            url = f"{HOST}/vodsearch/-------------.html?wd={quote(str(key))}"
            response = self.fetch(url, headers={"User-Agent": UA}, timeout=15)
            html = response.text if hasattr(response, "text") else str(response)
            return {"list": self._items(html), "page": page}
        except Exception:
            return {"list": [], "page": page}

    def playerContent(self, flag, id, vipFlags=None):
        url = str(id) if id else str(flag)

        # 直接是 m3u8/mp4
        if (
            url.startswith("http")
            and "/vodplay/" not in url
            and (".m3u8" in url or ".mp4" in url)
        ):
            return {"url": url}

        if url.startswith("http"):
            full_url = url
        else:
            if not url.startswith("/"):
                url = "/" + url
            full_url = urljoin(HOST, url)

        try:
            response = self.fetch(full_url, headers={"User-Agent": UA}, timeout=15)
            html = response.text if hasattr(response, "text") else str(response)
        except Exception:
            return {"url": ""}

        # player_aaaa JSON
        player_match = re.search(
            r"var player_aaaa=(.*?)</script>", html, re.S
        )
        if player_match:
            try:
                player_data = json.loads(
                    player_match.group(1).strip().rstrip(";")
                )
                play_url = player_data.get("url", "")
                if play_url:
                    return {"url": play_url}
            except Exception:
                pass

        # 兜底：直接抓 m3u8 / mp4
        m3u8_match = re.search(
            r'(https?://[^\s"\']+\.m3u8)', html, re.IGNORECASE
        )
        if m3u8_match:
            return {"url": m3u8_match.group(1)}

        mp4_match = re.search(
            r'(https?://[^\s"\']+\.mp4)', html, re.IGNORECASE
        )
        if mp4_match:
            return {"url": mp4_match.group(1)}

        return {"url": ""}

    def localProxy(self, param):
        pass

    # ---------- 内部工具 ----------

    def _category_url(self, cat, pn, extend):
        if isinstance(extend, str):
            try:
                extend = json.loads(extend)
            except Exception:
                extend = {}
        extend = extend if isinstance(extend, dict) else {}

        area = quote(str(extend.get("area", "")).strip(), safe="")
        sort_type = quote(str(extend.get("by", "")).strip(), safe="")
        genre = quote(str(extend.get("class", "")).strip(), safe="")
        language = quote(str(extend.get("lang", "")).strip(), safe="")
        letter = quote(str(extend.get("letter", "")).strip(), safe="")
        year = quote(str(extend.get("year", "")).strip(), safe="")

        # 无筛选：/vodtype/1-2.html
        if not any((area, sort_type, genre, language, letter, year)):
            return f"{HOST}/vodtype/{cat}-{pn}.html"

        # 有筛选：/vodshow/1-{area}-{by}-{class}-{lang}-{letter}---{page}---{year}.html
        page = "" if pn <= 1 else str(pn)
        return (
            f"{HOST}/vodshow/{cat}-{area}-{sort_type}-{genre}-"
            f"{language}-{letter}---{page}---{year}.html"
        )

    def _pagecount(self, html, current_page=1):
        pages = re.findall(r'href="/vodtype/\d+-(\d+)\.html"', html)
        pages += re.findall(
            r'href="/vodshow/[^"]*?-(\d+)---(?:\d{4})?\.html"', html
        )
        max_page = current_page
        for p in pages:
            try:
                max_page = max(max_page, int(p))
            except Exception:
                pass
        if re.search(
            r'title="下一页"|class="[^"]*next[^"]*"', html, re.IGNORECASE
        ):
            max_page = max(max_page, current_page + 1)
        return max_page

    def _items(self, html):
        items = []
        seen = set()

        # 匹配 /voddetail/{id}.html
        pattern = r'href="/voddetail/(\d+)\.html"[^>]*title="([^"]*)"'
        for m in re.finditer(pattern, html):
            vid = m.group(1)
            if vid in seen:
                continue
            name = m.group(2).strip()
            if not name or len(name) > 100:
                continue

            after = html[m.end():m.end() + 1200]

            cover = re.search(
                r'(?:data-original|data-src|original|src)="'
                r'(https?://[^"]+\.(?:jpg|jpeg|png|webp))"',
                after,
                re.IGNORECASE,
            )
            if not cover:
                cover = re.search(r'src="(https?://[^"]+)"', after, re.IGNORECASE)

            remark = re.search(
                r'class="(?:public-list-prb|pic-text|module-item-note|'
                r'remarks|status)[^"]*"[^>]*>([^<]+)<',
                after,
                re.IGNORECASE,
            )
            if not remark:
                remark = re.search(
                    r'<div[^>]*class="[^"]*(?:note|text|remark)[^"]*"'
                    r'[^>]*>([^<]+)<',
                    after,
                    re.IGNORECASE,
                )

            seen.add(vid)
            items.append({
                "vod_id": vid,
                "vod_name": name[:50],
                "vod_pic": cover.group(1) if cover else "",
                "vod_remarks": remark.group(1).strip() if remark else "",
            })
        return items