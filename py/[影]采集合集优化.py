# -*- coding: utf-8 -*-
# @Author  : AI Assistant
# @Desc    : 终极完美版 (智能网络更新 + 本地绝对兜底)

import json
import os
import time
import hashlib
import threading
import requests
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor, as_completed
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "CjJson_Final_Best"

    def init(self, extend):
        # =======================================================
        # 【配置区】 唯一的本地兜底路径
        # =======================================================
        self.DEFAULT_PATH = "/storage/emulated/0/lz/cj.json"
        
        # 缓存目录
        self.CACHE_DIR = "/storage/emulated/0/lz/cache/"
        
        # [防呆] 自动创建文件夹，防止保存文件时报错
        try:
            if not os.path.exists(os.path.dirname(self.DEFAULT_PATH)):
                os.makedirs(os.path.dirname(self.DEFAULT_PATH))
            if not os.path.exists(self.CACHE_DIR):
                os.makedirs(self.CACHE_DIR)
        except: pass

        # [基础] 网络组件
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=1)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.session.headers.update({"User-Agent": "Mozilla/5.0", "Connection": "keep-alive"})

        # [基础] 启动垃圾回收
        threading.Thread(target=self._silent_gc, daemon=True).start()

        # =======================================================
        # 【核心逻辑】 1.解析 -> 2.下载(可选) -> 3.定轨 -> 4.读取
        # =======================================================
        
        target = ""
        self.mode = "0" # 0=全部, 1=过滤福利, 2=仅福利

        # 1. 解析 Ext 参数
        if extend:
            if "|" in extend:
                parts = extend.split("|")
                target = parts[0].strip()
                if len(parts) > 1: self.mode = parts[1].strip()
            elif extend in ["0", "1", "2"]:
                self.mode = extend
            else:
                target = extend.strip()

        # 2. 逻辑分流
        final_file = self.DEFAULT_PATH # 默认读取目标

        if target:
            # 【分支A】用户指定了本地绝对路径 (以 / 开头)
            if target.startswith("/"):
                final_file = target  # 直接读它，不进行下载覆盖
            
            # 【分支B】用户指定了网络地址 (HTTP)
            elif target.lower().startswith("http"):
                try:
                    # 尝试下载
                    res = self.session.get(target, timeout=5, verify=False)
                    if res.status_code == 200:
                        # 只有当下载的数据是合法的JSON时，才保存
                        new_data = res.json()
                        
                        # 【关键】下载成功 -> 覆盖保存到默认兜底路径
                        with open(self.DEFAULT_PATH, "w", encoding="utf-8") as f:
                            json.dump(new_data, f, ensure_ascii=False, indent=4)
                except:
                    # 网络失败，不做任何操作，代码会自动向下执行
                    pass
                
                # 网络模式下，读取目标永远是默认兜底路径
                final_file = self.DEFAULT_PATH

        # 3. 最终读取 (无论前面经历了什么，都在这里汇合)
        data = {}
        try:
            if os.path.exists(final_file):
                with open(final_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
        except: pass

        # 4. 载入站点
        self.sites = self._filter_sites(data.get("api_site", []), self.mode)


    # =======================================================
    # 【标准功能区】 (无需修改，保持最高性能)
    # =======================================================

    def _filter_sites(self, sites, mode):
        if mode == "0": return sites
        adult_kws = {"AV", "色", "福利", "成人", "18+", "偷拍", "自拍", "淫", "激情", "GAY", "SEX"}
        def is_adult(name):
            return any(k in name.upper() for k in adult_kws) if name else False
        if mode == "1": return [s for s in sites if not is_adult(s.get("name", ""))]
        elif mode == "2": return [s for s in sites if is_adult(s.get("name", ""))]
        return sites

    def _silent_gc(self):
        try:
            time.sleep(10)
            if os.path.exists(self.CACHE_DIR):
                now = time.time()
                for f in os.listdir(self.CACHE_DIR):
                    if not f.endswith(".json"): continue
                    p = os.path.join(self.CACHE_DIR, f)
                    try:
                        if now - os.path.getmtime(p) > 604800: os.remove(p)
                    except: pass
        except: pass

    def _get_disk_cache(self, key, ttl=86400):
        try:
            md5 = hashlib.md5(key.encode('utf-8')).hexdigest()
            path = os.path.join(self.CACHE_DIR, f"{md5}.json")
            if os.path.exists(path):
                if time.time() - os.path.getmtime(path) < ttl:
                    with open(path, "r", encoding="utf-8") as f: return json.load(f)
                else: os.remove(path)
        except: pass
        return None

    def _set_disk_cache(self, key, data):
        try:
            if not data or not data.get("list"): return 
            md5 = hashlib.md5(key.encode('utf-8')).hexdigest()
            path = os.path.join(self.CACHE_DIR, f"{md5}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except: pass

    def _fetch(self, url, params=None):
        try:
            sep = "&" if "?" in url else "?"
            qs = "&".join([f'{k}={v}' for k, v in params.items()]) if params else ""
            full = f"{url}{sep}{qs}" if qs else url
            to = 1.5 if params and "wd" in params else 3.0
            res = self.session.get(full, timeout=to, verify=False)
            if res.status_code == 200:
                try: return res.json()
                except: return json.loads(res.text.strip().lstrip('﻿'))
        except: pass
        return {}

    def homeContent(self, filter):
        classes, filters = [], {}
        base_ft = [{"key": "cateId", "name": "分类", "value": [{"n": "全部", "v": ""}, {"n": "动作", "v": "动作"}, {"n": "喜剧", "v": "喜剧"}, {"n": "剧情", "v": "剧情"}, {"n": "科幻", "v": "科幻"}, {"n": "恐怖", "v": "恐怖"}, {"n": "国产", "v": "国产"}, {"n": "动漫", "v": "动漫"}, {"n": "综艺", "v": "综艺"}]}]
        for i, s in enumerate(self.sites):
            tid = str(i)
            clean_name = s.get("name", f"源{i}").replace("TV-", "").replace("AV-", "")
            classes.append({"type_id": tid, "type_name": clean_name})
            filters[tid] = base_ft
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, ext):
        try:
            idx = int(tid)
            if idx >= len(self.sites): return {"list": []}
            site = self.sites[idx]
        except: return {"list": []}

        key = f"C_{hashlib.md5(site.get('api','').encode()).hexdigest()}_{pg}_{json.dumps(ext)}"
        c = self._get_disk_cache(key, ttl=86400)
        if c: return c

        try:
            kw = ext.get("cateId", "") if ext else ""
            paichu_str = str(site.get("paichu", ""))
            paichu = set(paichu_str.split(",")) if paichu_str else set()

            res = self._fetch(site["api"], {"ac": "detail", "pg": pg})
            lst = []
            if res and "list" in res:
                for i in res["list"]:
                    if str(i.get("type_id")) in paichu: continue
                    if kw and kw not in i.get("type_name", ""): continue
                    i["vod_id"] = f"{idx}@@{i['vod_id']}"
                    lst.append(i)
            
            ret = {"page": int(res.get("page", 1)) if res else 1, "pagecount": int(res.get("pagecount", 1)) if res else 1, "limit": 20, "total": int(res.get("total", 0)) if res else 0, "list": lst}
            self._set_disk_cache(key, ret)
            return ret
        except: return {"list": []}

    def detailContent(self, array):
        if not array: return {"list": []}
        vid_full = str(array[0])
        if "@@" not in vid_full: return {"list": []}
        try:
            idx, vid = vid_full.split("@@")
            site = self.sites[int(idx)]
            res = self._fetch(site["api"], {"ac": "detail", "ids": vid})
            if res and "list" in res:
                item = res["list"][0]
                item["vod_id"] = vid_full
                return {"list": [item]}
        except: pass
        return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        if not key: return {"list": []}
        c_key = f"S_{self.mode}_{key}"
        c = self._get_disk_cache(c_key, ttl=3600)
        if c: return c

        targets = [(i, s) for i, s in enumerate(self.sites) if s.get("api")]
        workers = min(len(targets), 32)
        if not workers: return {"list": []}

        def _task(t):
            i, s = t
            try:
                paichu_str = str(s.get("paichu", ""))
                paichu = set(paichu_str.split(",")) if paichu_str else set()
                res = self._fetch(s["api"], {"ac": "detail", "wd": key})
                l = []
                if res and "list" in res:
                    for item in res["list"]:
                        if str(item.get("type_id")) in paichu: continue
                        s_name = s.get("name","").replace("TV-", "").replace("AV-", "")
                        item["vod_name"] = f"[{s_name}] {item['vod_name']}"
                        item["vod_id"] = f"{i}@@{item['vod_id']}"
                        l.append(item)
                return i, l
            except: return i, []

        tmp = {}
        with ThreadPoolExecutor(workers) as exe:
            for fut in as_completed([exe.submit(_task, t) for t in targets]):
                try:
                    i, l = fut.result()
                    if l: tmp[i] = l
                except: pass
        
        final = []
        for i in sorted(tmp.keys()): final.extend(tmp[i])
        
        ret = {"list": final}
        self._set_disk_cache(c_key, ret)
        return ret

    def playerContent(self, flag, id, vipFlags):
        parse = 0 if (".m3u8" in id or ".mp4" in id) else 1
        return {"url": id, "header": {"User-Agent": "Mozilla/5.0"}, "parse": parse, "jx": 0}

    def localProxy(self, params):
        return [200, "video/MP2T", "", ""]