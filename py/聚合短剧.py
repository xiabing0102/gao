# -*- coding: utf-8 -*-
# 短剧聚合 Spider - 七猫/星芽/西饭/围观/好看/短剧大全
import re, json, base64, hashlib, time, uuid, requests
from urllib.parse import quote, unquote, urlparse, parse_qs, urlencode, urlunparse
from base.spider import Spider

HEMA_TAGS = {
    "情节主题": ["逆袭","打脸虐渣","豪门恩怨","重生","闪婚","先婚后爱","破镜重圆","追妻火葬场","复仇","马甲","强者回归","传承觉醒","双向救赎","白月光","灵魂互换","暴富","捞偏门","反派主角","扮猪吃虎","赘婿逆袭","隐瞒身份","千金归来","离婚后","带球跑","替嫁","契约婚姻","日久生情","扮丑","退婚","女扮男装","异能觉醒","系统加持","金手指","开挂","翻身"],
    "角色设定": ["总裁","大女主","大男主","小人物","真假千金","赘婿","战神","神医","萌宝","团宠","大叔","业界精英","特种兵","兵王","龙王","阎王","军嫂","宝妈","婆婆","岳母","姐姐","弟弟","青梅竹马","姐弟恋","年下恋","寡妇女主","离婚女","农村女","打工妹","都市白领"],
    "题材背景": ["都市","古装","民国","校园","职场","乡村","年代","架空","宫廷","荒岛","悬疑","谍战","喜剧","玄幻","仙侠","科幻","末世","丧尸","武侠","神话","穿越","现代言情","古代言情","宫斗","权谋","商战","医患","刑侦","军事","灵异","志怪","综艺","娱乐圈"],
    "风格调性": ["甜宠","虐恋","爽剧","脑洞","沙雕","治愈","暗黑","温情","搞笑","励志","热血","温情治愈","爆笑"]
}
ALL_HEMA_TAGS = [t for v in HEMA_TAGS.values() for t in v]
PLOT_TAGS = ["系统","贬值","修仙","末世","末日","马甲","穿越"]


def _merge(base, extra, priority=None):
    seen, result = set(), []
    head = [x for x in base if x.get('v', '') == '']
    rest = [x for x in base if x.get('v', '') != '']

    def push(item):
        n = item.get('n', '')
        if n and n not in seen:
            seen.add(n); result.append(item)

    for x in head: push(x)
    for t in (priority or []): push({'n': t, 'v': t})
    for x in rest: push(x)
    for t in extra: push({'n': t, 'v': t})
    return result


BASE_TAGS = _merge([{'n': '全部', 'v': ''}], ALL_HEMA_TAGS)
PLATFORM_TAGS = _merge([{'n': '全部', 'v': ''}], ALL_HEMA_TAGS, ["闪婚"] + PLOT_TAGS)
XIFAN_TAGS = _merge([{'n': '全部', 'v': ''}], ALL_HEMA_TAGS, ["闪婚","贬值","修仙","马甲","末世","末日"])
QM_PRIORITY = ["闪婚","系统","贬值","修仙","马甲","末日","末世"]


class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.keys = 'd3dGiJc651gSQ8w1'
        self.cmap = {
            '+':'P','/':'X','0':'M','1':'U','2':'l','3':'E','4':'r','5':'Y','6':'W','7':'b','8':'d','9':'J',
            'A':'9','B':'s','C':'a','D':'I','E':'0','F':'o','G':'y','H':'_','I':'H','J':'G','K':'i','L':'t',
            'M':'g','N':'N','O':'A','P':'8','Q':'F','R':'k','S':'3','T':'h','U':'f','V':'R','W':'q','X':'C',
            'Y':'4','Z':'p','a':'m','b':'B','c':'O','d':'u','e':'c','f':'6','g':'K','h':'x','i':'5','j':'T',
            'k':'-','l':'2','m':'z','n':'S','o':'Z','p':'1','q':'V','r':'v','s':'j','t':'Q','u':'7','v':'D',
            'w':'w','x':'n','y':'L','z':'e'}
        self.hd = {'User-Agent': 'okhttp/3.12.11', 'content-type': 'application/json; charset=utf-8'}
        self.plat = {
            '星芽': {'host': 'https://app.whjzjx.cn', 'url1': '/cloud/v2/theater/home_page?theater_class_id', 'url2': '/v2/theater_parent/detail', 'search': '/v3/search', 'rank': '/cloud/v1/first_level_ranking/detail', 'login': 'https://u.shytkjgs.com/user/v1/account/login'},
            '西饭': {'host': 'https://xifan-api-cn.youlishipin.com', 'url1': '/xifan/drama/portalPage', 'url2': '/xifan/drama/getDuanjuInfo', 'search': '/xifan/search/getSearchList',
                'common': {'version': '2001001', 'androidVersionCode': '28', 'appId': 'drama', 'teenMode': 'false', 'userBaseMode': 'false'},
                'session': 'eyJpbmZvIjp7InVpZCI6IiIsInJ0IjoiMTc0MDY1ODI5NCIsInVuIjoiT1BHXzFlZGQ5OTZhNjQ3ZTQ1MjU4Nzc1MTE2YzFkNzViN2QwIiwiZnQiOiIxNzQwNjU4Mjk0In19',
                'feedssession': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1dHlwIjowLCJidWlkIjoxNjMzOTY4MTI2MTQ4NjQxNTM2LCJhdWQiOiJkcmFtYSIsInZlciI6MiwicmF0IjoxNzQwNjU4Mjk0LCJ1bm0iOiJPUEdfMWVkZDk5NmE2NDdlNDUyNTg3NzUxMTZjMWQ3NWI3ZDAiLCJpZCI6IjNiMzViZmYzYWE0OTgxNDQxNDBlZjI5N2JkMDY5NGNhIiwiZXhwIjoxNzQxMjYzMDk0LCJkYyI6Imd6cXkifQ.JS3QY6ER0P2cQSxAE_OGKSMIWNAMsYUZ3mJTnEpf-Rc',
                'headers': {'User-Agent': 'Mozilla/5.0 (Linux; Android 8.0; DUK-AL20 Build/HUAWEIDUK-AL20; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/57.0.2987.132 MQQBrowser/6.2 TBS/044353 Mobile Safari/537.36 MicroMessenger/6.7.3.1360(0x26070333) NetType/WIFI Language/zh_CN Process/tools', 'Accept': 'application/json, text/plain, */*', 'Accept-Encoding': 'gzip, deflate', 'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8', 'Connection': 'keep-alive'}},
            '七猫': {'host': 'https://api-store.qmplaylet.com', 'url1': '/api/v1/playlet/index', 'url2': 'https://api-read.qmplaylet.com/player/api/v1/playlet/info', 'search': '/api/v1/playlet/search'},
            '围观': {'host': 'https://api.drama.9ddm.com', 'url2': '/drama/home/shortVideoDetail', 'search': '/drama/home/search'},
            '好看': {'host': 'https://sv.baidu.com'},
            '大全': {'host': 'https://lssy.net'}
        }
        self.plist = [{'name': '🐱七猫短剧', 'id': '七猫'}, {'name': '🍃星芽短剧', 'id': '星芽'}, {'name': '🚞围观短剧', 'id': '围观'},
                      {'name': '💞好看短剧', 'id': '好看'}, {'name': '🍀西饭短剧', 'id': '西饭'}, {'name': '💮短剧大全', 'id': '大全'}]
        self.rdef = {'星芽': {'area': '1', 'class2': '0', 'rank': '1'}, '西饭': {'area': '都市'}, '七猫': {'area': '0'},
                     '围观': {'area': ''}, '好看': {'tag_id': '0'}, '大全': {'area': '1'}}

        self.gw = {'version_code':'1600','version_name':'1.6.0','device_name':'PJA110','device_type':'phone','is_first_day':'false','is_first_24h':'false','app_launch_way':'icon','default_homepage':'drama_library','device_owning_firm':'OnePlus','font_scale':'default','os_type':'1','clientInfo':'9BBBC7EC6D9045E6BD3B6E6B95A71D9Dd66169e46a7d8de8d766bce0d0e0df57'}

        self.hk_base = ("https://sv.baidu.com/appui/api?cmd=video/commonlist&log=vhk&tn=1043677m&ctn=1043677m&blur=1&mac=&imei=AL5fB&cuid=B8B02D397EF5A5D8675FF92CDEDB833B%7C0&iid=A50-GZSWENRQHEZWMLJUHFSTALJUMYZDCLLBHEYWGLLCGZTDGNZQGBRGCOJQGE-OUABVLNI&c3_aid=A00-GGDKZORUQAP5GY6JC5BBPXTPVNC74IIA-V5QNYZSV&os=android&osbranch=a0&ua=900_1600_240&ut=V1938T_9_28_vivo&uh=vivo,qcom,V1938T&apiv=7.93.0.18&appv=793001&version=7.93.0.18&life=1773081846&clife=1773081846&nlife=1773081808&hid=empty&imsi=0&user_live_rec_source=yy,baijiahao,bjh_client,pc_client,bd_client&app_cpu_abi=64&device_prefer_abi=64&is_fold_screen=0&is_tablet=0&player_params=%7B%22ps%22:-1%7D&androidId=ec1280db12795506&zid=UW60kbyg6UiIf3uhVai1IDx_sCpGqcu19NSBuVuST5hB1Ho3bCpDReYbYo3zw3ZVdgFFLm7bHyMC7Kis_fOMAnA&network=1&sids=265_2-999990_2-999991_2-999989_2-999992_2-999988_2-999993_2-999999_72-123_2&young_mode=0&oaid=&honor_oaid=&nu=1&score=0.4330356&network5g=1&mpv=1&before_agree_sids=user_growth_15&fvt=1773081342&cp_isbg=0&is_playlet=1")
        self.hk_ua = ("Mozilla/5.0 (Linux; Android 9; V1938T Build/PQ3A.190705.08061357; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Safari/537.36 haokan/7.93.0.18 (Baidu; P1 9)/oviv_82_9_T8391V/1043677m/B8B02D397EF5A5D8675FF92CDEDB833B%7C0/1/7.93.0.18/793001/1/immersiveMode/modeV4PlusWhite/isFirstInstall/bbqMode/bbqModeV2/blackStyle/isPlaylet")
        self.hk_hd = {'User-Agent': self.hk_ua}

        self._hk_cls, self._hk_cls_ts = None, 0
        self._qm_filter, self._qm_ts = None, 0
        self._xf_map, self._xf_map_ts = None, 0

        self.dq_hd = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8', 'Accept-Language': 'zh-CN,zh;q=0.9', 'Referer': 'https://lssy.net/', 'Connection': 'keep-alive'}
        self.dq_cat = {"1":"","2":"重生","3":"穿越","4":"都市","5":"甜宠","6":"虐恋","7":"战神","8":"逆袭","9":"古装","10":"家庭","11":"悬疑","12":"剧情"}

        self.fopts = {
            '七猫': [],
            '星芽': [
                {'key':'area','name':'剧场','value':[{'n':'剧场','v':'1'},{'n':'热播短剧','v':'2'},{'n':'会员专享','v':'8'},{'n':'星选好剧','v':'7'},{'n':'新剧','v':'3'},{'n':'阳光剧场','v':'5'},{'n':'排行榜','v':'9'}]},
                {'key':'class2','name':'类型','value':[{'n':'全部','v':'0'},{'n':'都市','v':'4'},{'n':'逆袭','v':'7'},{'n':'古装','v':'5'},{'n':'亲情','v':'41'},{'n':'现代言情','v':'15'},{'n':'重生','v':'6'},{'n':'虐恋','v':'8'},{'n':'玄幻','v':'35'},{'n':'穿越','v':'17'},{'n':'脑洞','v':'32'},{'n':'甜宠','v':'33'},{'n':'古代言情','v':'37'},{'n':'战神','v':'24'},{'n':'历史','v':'40'},{'n':'赘婿','v':'26'},{'n':'萌宝','v':'9'},{'n':'神医','v':'25'}]},
                {'key':'rank','name':'榜单','value':[{'n':'实时热榜','v':'1'},{'n':'热搜榜','v':'2'},{'n':'新剧榜','v':'3'},{'n':'剧单榜','v':'4'},{'n':'口碑榜','v':'5'}]},
                {'key':'tag','name':'标签','value':PLATFORM_TAGS}],
            '西饭': [{'key':'tag','name':'标签','value':XIFAN_TAGS}],
            '围观': [
                {'key':'audience','name':'受众','value':[{'n':'全部','v':''},{'n':'男频','v':'男频'},{'n':'女频','v':'女频'}]},
                {'key':'order','name':'排序','value':[{'n':'全部','v':''},{'n':'最热','v':'hot'},{'n':'最新','v':'new'}]},
                {'key':'tag','name':'标签','value':PLATFORM_TAGS}],
            '好看': [],
            '大全': [
                {'key':'area','name':'分类','value':[{'n':'短剧大全','v':'1'},{'n':'重生','v':'2'},{'n':'穿越','v':'3'},{'n':'都市','v':'4'},{'n':'甜宠','v':'5'},{'n':'虐恋','v':'6'},{'n':'战神','v':'7'},{'n':'逆袭','v':'8'},{'n':'古装','v':'9'},{'n':'家庭','v':'10'},{'n':'悬疑','v':'11'},{'n':'剧情','v':'12'}]},
                {'key':'tag','name':'标签','value':PLATFORM_TAGS}]
        }
        self.qm_hd = {'value': None, 'ts': 0}
        self.xy_hd = dict(self.hd)

    def init(self, extend=""): self.extend = extend; return self
    def getName(self): return "短剧聚合"

    # ---- 工具 ----
    def _tag(self, e): return (e.get('tag') or '').strip() if e and isinstance(e.get('tag'), str) else ''
    def _cn(self, n):
        return re.sub(r'<[^>]+>', '', n).replace('\u200b', '').replace('\xa0', ' ').strip() if isinstance(n, str) else n
    def _md5(self, t): return hashlib.md5(t.encode()).hexdigest().lower()

    def _req(self, url, method='GET', hd=None, data=None, to=5000):
        try:
            h = {**self.hd, **(hd or {})}
            r = (requests.post if method.upper() == 'POST' else requests.get)(url, headers=h, timeout=to/1000, verify=False, **({'json': data} if method.upper() == 'POST' else {}))
            return r.json()
        except Exception: return None

    # ---- 七猫签名 ----
    def _qm_sign(self):
        now = int(time.time() * 1000)
        if self.qm_hd['value'] and now - self.qm_hd['ts'] < 300000: return self.qm_hd['value']
        d = {"static_score":"0.8","uuid":"00000000-7fc7-08dc-0000-000000000000","device-id":"20250220125449b9b8cac84c2dd3d035c9052a2572f7dd0122edde3cc42a70","sourceuid":"aa7de295aad621a6","refresh-type":"0","model":"22021211RC","client-id":"aa7de295aad621a6","brand":"Redmi","sys-ver":"12","phone-level":"H","wlb-uid":"aa7de295aad621a6","session-id":str(now)}
        b64 = base64.b64encode(json.dumps(d, separators=(',', ':')).encode()).decode()
        qm = ''.join(self.cmap.get(c, c) for c in b64)
        sign = self._md5(f"AUTHORIZATION=app-version=10001application-id=com.duoduo.readchannel=unknownis-white=net-env=5platform=androidqm-params={qm}reg={self.keys}")
        self.qm_hd['value'] = {'qmParams': qm, 'sign': sign}; self.qm_hd['ts'] = now
        return self.qm_hd['value']

    def _qm_hdr(self):
        q = self._qm_sign()
        return {'net-env':'5','reg':'','channel':'unknown','is-white':'','platform':'android','application-id':'com.duoduo.read','authorization':'','app-version':'10001','user-agent':'webviewversion/0','qm-params':q['qmParams'],'sign':q['sign']}

    def _xy_auth(self):
        if self.xy_hd.get('authorization'): return self.xy_hd
        try:
            r = requests.post(self.plat['星芽']['login'], headers={'User-Agent':'okhttp/4.10.0','platform':'1','Content-Type':'application/json'}, json={'device':'24250683a3bdb3f118dff25ba4b1cba1a'}, timeout=10, verify=False).json()
            tk = r.get('data', {}).get('token') or r.get('token')
            if tk: self.xy_hd = {**self.hd, 'authorization': tk}
        except Exception: pass
        return self.xy_hd

    # ---- 七猫动态筛选 ----
    def _qm_filter_data(self):
        now = time.time()
        if self._qm_filter is not None and now - self._qm_ts < 1800: return self._qm_filter
        sign = self._md5(f"operation=1playlet_privacy=1tag_id=0{self.keys}")
        url = f"{self.plat['七猫']['host']}{self.plat['七猫']['url1']}?tag_id=0&playlet_privacy=1&operation=1&sign={sign}"
        try: data = requests.get(url=url, headers=self._qm_hdr(), timeout=10, verify=False).json()
        except Exception: return None
        if 'data' not in data or 'tag_categories' not in data['data']: return None
        cats = data['data']['tag_categories']
        tags, order = {}, []
        for i in range(min(5, len(cats))):
            for v in cats[i].get('tags', []):
                n, t = v.get('tag_name', ''), str(v.get('tag_id', ''))
                if n and t and "推荐" not in n and n not in tags:
                    tags[n] = t; order.append(n)
        vals = [{"v":"","n":"全部"}]; seen_tid = {""}; seen_n = set()
        for p in QM_PRIORITY:
            pt = tags.get(p, '')
            if pt and pt not in seen_tid:
                seen_tid.add(pt); seen_n.add(p); vals.append({"v":pt,"n":p})
        for n in order:
            if n in seen_n or tags[n] in seen_tid: continue
            seen_tid.add(tags[n]); vals.append({"v":tags[n],"n":n})
        self._qm_filter = [{"key":"tag","name":"分类标签","value":vals}] if len(vals) > 1 else []
        self._qm_ts = now
        return self._qm_filter

    # ---- 首页 ----
    def homeContent(self, filter):
        cls = [{'type_name': p['name'], 'type_id': p['id']} for p in self.plist]
        fts = {p['id']: self.fopts.get(p['id'], []) for p in self.plist}
        try:
            g = self._qm_filter_data()
            if g is not None: fts['七猫'] = g
        except Exception: pass
        try:
            hk = self._hk_classes()
            if hk: fts['好看'] = [{'key':'tag_id','name':'分类','value':[{'n':c['type_name'],'v':c['type_id']} for c in hk]}, {'key':'tag','name':'标签','value':PLATFORM_TAGS}]
        except Exception: pass
        return {'class': cls, 'filters': fts}

    def homeVideoContent(self): return self.categoryContent('七猫', '1', False, {})

    # ---- 分类 ----
    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if pg else 1; extend = extend or {}
        try:
            if tid == '七猫': return self._qm_cat(pg, extend)
            if tid == '星芽': return self._xy_cat(pg, extend)
            if tid == '西饭': return self._xf_cat(pg, extend)
            if tid == '围观': return self._gw_cat(pg, extend)
            if tid == '好看': return self._hk_cat(pg, extend)
            if tid == '大全': return self._dq_cat(pg, extend)
        except Exception: pass
        return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}

    def _qm_cat(self, pg, e):
        p = self.plat['七猫']; tv = str(e.get('tag', '') or '').strip() or '0'
        if pg == 1:
            sign = self._md5(f"operation=1playlet_privacy=1tag_id={tv}{self.keys}")
            url = f"{p['host']}{p['url1']}?tag_id={tv}&playlet_privacy=1&operation=1&sign={sign}"
        else:
            sign = self._md5(f"next_id={pg}operation=1playlet_privacy=1tag_id={tv}{self.keys}")
            url = f"{p['host']}{p['url1']}?tag_id={tv}&next_id={pg}&playlet_privacy=1&operation=1&sign={sign}"
        try: data = requests.get(url=url, headers=self._qm_hdr(), timeout=10, verify=False).json()
        except Exception: return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 90, 'total': 0}
        if 'data' not in data or 'list' not in data['data']: return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 90, 'total': 0}
        vs = [{'vod_id': f"七猫@{quote(str(v['playlet_id']))}", 'vod_name': v.get('title', ''), 'vod_pic': v.get('image_link', ''),
               'vod_remarks': v.get('hot_value', '') or f"{v.get('total_episode_num', '')}集"}
              for v in data['data']['list'] if v.get('title') and v.get('playlet_id')]
        return {'list': vs, 'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 999999}

    def _xy_search(self, key):
        try:
            r = self._req(self.plat['星芽']['host'] + self.plat['星芽']['search'], 'POST', self._xy_auth(), {'text': key}, 10000) or {}
            d = r.get('data', {})
            return d.get('theater', {}).get('search_data', []) or d.get('search_data', []) or d.get('list', [])
        except Exception: return []

    def _xy_vod(self, i):
        if not i.get('id'): return None
        return {'vod_id': f"星芽@{self.plat['星芽']['host']}{self.plat['星芽']['url2']}?theater_parent_id={i['id']}",
                'vod_name': i.get('title', ''), 'vod_pic': i.get('cover_url', ''), 'vod_remarks': f"{i.get('total', '')}集"}

    def _xy_cat(self, pg, e):
        p = self.plat['星芽']; area = e.get('area') or self.rdef['星芽']['area']; tag = self._tag(e)
        if tag:
            vs = [v for i in self._xy_search(tag) if (v := self._xy_vod(i))]
            return {'list': vs, 'page': pg, 'pagecount': 1, 'limit': len(vs), 'total': len(vs)}
        hd = self._xy_auth()
        if area == '9':
            if pg > 1: return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
            r = self._req(f"{p['host']}{p['rank']}?id={e.get('rank') or e.get('class2') or self.rdef['星芽']['rank']}", hd=hd, to=10000) or {}
            vs = [v for it in r.get('data', {}).get('list', []) if (i := (it.get('theater') or it)) and (v := self._xy_vod(i))]
            return {'list': vs, 'page': pg, 'pagecount': 1, 'limit': len(vs), 'total': len(vs)}
        c2 = e.get('class2') or self.rdef['星芽']['class2']
        r = self._req(f"{p['host']}{p['url1']}={area}&type=1&class2_ids={c2}&page_num={pg}&page_size=24", hd=hd, to=10000)
        d = r.get('data', {}) if r else {}
        vs = [v for it in d.get('list', []) if (i := (it.get('theater') or it)) and (v := self._xy_vod(i))]
        tot = int(d.get('total') or 0) or ((pg - 1) * 24 + len(vs))
        pc = pg if (d.get('is_end') or not vs) else max(pg + 1, (tot + 23) // 24)
        return {'list': vs, 'page': pg, 'pagecount': pc, 'limit': 24, 'total': tot}

    def _xf_p(self, extra=None):
        p = self.plat['西饭']; d = dict(p.get('common', {})); d['requestId'] = f"{int(time.time() * 1000)}aa498144140ef297"
        if extra: d.update(extra)
        d['session'] = p.get('session', ''); d['feedssession'] = p.get('feedssession', '')
        return d

    def _xf_get(self, url, params):
        try: return requests.get(url, params=params, headers=self.plat['西饭'].get('headers', {}), timeout=10, verify=False).json()
        except Exception: return None

    def _xf_parse(self, res, area=''):
        vs = []
        if not res: return vs
        for el in res.get('result', {}).get('elements', []):
            for it in el.get('contents', []):
                if it.get('categoryItemVo'): continue
                dj = it.get('duanjuVo') or {}
                if not dj.get('duanjuId'): continue
                if area:
                    cats = dj.get('categories', [])
                    if cats and area not in cats: continue
                tot = dj.get('total', 0)
                ep = f"全{tot}集" if dj.get('updateStatus') == 'over' else (f"更新至{tot}集" if tot else "")
                c = (dj.get('categories') or [''])[0]
                rm = ' · '.join([x for x in (c, ep) if x])
                vs.append({'vod_id': f"西饭@{dj['duanjuId']}#{dj['source']}", 'vod_name': self._cn(dj.get('title', '')),
                           'vod_pic': dj.get('coverImageUrl', ''), 'vod_remarks': rm or (f"{tot}集" if tot else "")})
        return vs

    def _xf_page(self, res, pg, got):
        tot = None
        if res and isinstance(res, dict):
            r = res.get('result', {})
            for k in ('total', 'totalCount', 'count', 'pageCount', 'page_total'):
                v = r.get(k)
                if isinstance(v, (int, float)) and v > 0: tot = int(v); break
        if tot: pc = max(1, (tot + 29) // 30)
        elif got == 0: pc = max(1, pg - 1)
        else: pc = 9999
        return tot, pc

    def _xf_map(self):
        now = time.time()
        if self._xf_map is not None and now - self._xf_map_ts < 3600: return self._xf_map
        m = {}
        try:
            d = self._xf_get(f"{self.plat['西饭']['host']}{self.plat['西饭']['url1']}", self._xf_p({'reqType': 'duanjuCategory', 'density': '1.5'}))
            if d:
                for el in d.get('result', {}).get('elements', []):
                    for it in el.get('contents', []):
                        vo = it.get('categoryItemVo') or {}
                        pn, pi = vo.get('oppoCategory'), str(vo.get('categoryId', ''))
                        if pn and pi: m[pn] = (pn, pi)
                        for s in vo.get('subCategories', []) or []:
                            sn, si = s.get('oppoCategory'), str(s.get('categoryId', ''))
                            if sn and si: m[sn] = (sn, si)
        except Exception: pass
        self._xf_map, self._xf_map_ts = m, now
        return m

    def _xf_cat(self, pg, e):
        p = self.plat['西饭']; tag = self._tag(e); area = e.get('area') or self.rdef['西饭']['area']
        if tag:
            mp = self._xf_map().get(tag)
            if mp:
                cn, ci = mp
                res = self._xf_get(f"{p['host']}{p['url1']}", self._xf_p({'reqType':'aggregationPage','offset':str((pg-1)*30),'categoryId':ci,'categoryNames':cn,'categoryVersion':'1','density':'1.5','pageID':'page_theater'}))
            else:
                res = self._xf_get(f"{p['host']}{p['search']}", self._xf_p({'keyword': tag, 'pageIndex': str(pg)}))
            vs = self._xf_parse(res); tot, pc = self._xf_page(res, pg, len(vs))
            return {'list': vs, 'page': pg, 'pagecount': pc, 'limit': 30, 'total': tot if tot else (pg - 1) * 30 + len(vs)}
        res = self._xf_get(f"{p['host']}{p['url1']}", self._xf_p({'reqType':'aggregationPage','offset':str((pg-1)*30),'categoryId':'68','categoryNames':area,'categoryVersion':'1','density':'1.5','pageID':'page_theater'}))
        vs = self._xf_parse(res, area=area); tot, pc = self._xf_page(res, pg, len(vs))
        return {'list': vs, 'page': pg, 'pagecount': pc, 'limit': 30, 'total': tot if tot else (pg - 1) * 30 + len(vs)}

    def _gw_search(self, key, pg=1, size=30, aud='', order=''):
        d = {"audience": aud, "page": pg, "pageSize": size, "searchWord": key or "", "subject": ""}
        if order: d["order"] = order
        try:
            return requests.post(self.plat['围观']['host'] + self.plat['围观']['search'], headers={'Content-Type': 'application/json;charset=utf-8'}, data=json.dumps(d), timeout=10, params=self.gw, verify=False).json()
        except Exception: return {}

    def _gw_vod(self, i):
        vc, ec = i.get("viewCount", 0), i.get("episodeCount", 0)
        parts = []
        if vc: parts.append(f"{vc/10000:.1f}万播放" if vc >= 10000 else f"{vc}播放")
        if ec: parts.append(f"{ec}集")
        return {"vod_id": f"围观@{i['oneId']}", "vod_name": i["title"], "vod_pic": i["vertPoster"],
                "vod_year": i.get("upperLeftCornerLabel", "") or str(i.get("publishDate", "")),
                "vod_remarks": " · ".join(parts) if parts else ""}

    def _gw_cat(self, pg, e):
        d = self._gw_search(self._tag(e), pg, aud=e.get('audience', ''), order=e.get('order', ''))
        vs = [self._gw_vod(i) for i in d.get("data", [])]
        return {'list': vs, 'page': pg, 'pagecount': 9999 if vs else 1, 'limit': 30, 'total': 999999}

    def _hk_cuid(self): return uuid.uuid4().hex.upper()[:32] + "%7C0"
    def _hk_ua(self): return re.sub(r'(/1043677m/)([\w%]+)(/\d+/\d+\.\d+\.\d+/\d+/)', lambda m: m.group(1) + self._hk_cuid() + m.group(3), self.hk_ua)

    def _hk_classes(self):
        now = time.time()
        if self._hk_cls and now - self._hk_cls_ts < 600: return self._hk_cls
        cls = []
        try:
            r = requests.post(f"{self.plat['好看']['host']}/haokan/ui-feed/playletShelfFeed", headers=self.hk_hd, json={"data": json.dumps({"from": "feed"})}, timeout=10, verify=False).json()
            for v in r.get('data', {}).get('playlet_tags', []):
                tid, n = str(v.get('tag_id', '')).strip(), str(v.get('name', '')).strip()
                if tid and n: cls.append({"type_id": tid, "type_name": n})
        except Exception: pass
        if not cls: cls = [{"type_id": "0", "type_name": "推荐"}, {"type_id": "2", "type_name": "新剧"}]
        self._hk_cls, self._hk_cls_ts = cls, now
        return cls

    def _hk_search(self, key):
        try:
            return requests.post(f"{self.plat['好看']['host']}/haokan/ui-interact/playlet/search/sugs", headers=self.hk_hd, data={"search_word": key}, timeout=10, verify=False).json().get('data', [])
        except Exception: return []

    def _hk_cat(self, pg, e):
        tag = self._tag(e)
        tid = str(e.get('tag_id', '') or '') or str(e.get('area', '') or '') if e else ''
        if tag:
            vs = [{"vod_id": f"好看@{v['id']}", "vod_name": v.get('title', ''), "vod_pic": v.get('cover_url', ''), "vod_remarks": "好看短剧"} for v in self._hk_search(tag)]
            return {'list': vs, 'page': pg, 'pagecount': 9999 if vs else 1, 'limit': 9, 'total': 999999}
        if not tid:
            c = self._hk_classes()
            if c: tid = c[0]['type_id']
        if not tid: return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 9, 'total': 0}
        vs = []
        try:
            r = requests.post(f"{self.plat['好看']['host']}/haokan/ui-feed/playletTagsFeed", headers=self.hk_hd, data={"tag_id": tid, "pn": pg, "rn": 9}, timeout=10, verify=False).json()
            for v in r.get('data', {}).get('list', []):
                vs.append({"vod_id": f"好看@{v['playlet_id']}", "vod_name": v['playlet_title'], "vod_pic": v.get('playlet_poster', ''), "vod_year": str(v.get('hot_value', '')), "vod_remarks": v.get('episodes_num_text', '')})
        except Exception: pass
        return {'list': vs, 'page': pg, 'pagecount': 9999 if vs else 1, 'limit': 9, 'total': 999999}

    def _dq_fix(self, u):
        if not u: return ''
        u = u.strip()
        if u.startswith('http'): return u
        if u.startswith('//'): return 'https:' + u
        if u.startswith('/'): return self.plat['大全']['host'] + u
        return self.plat['大全']['host'] + '/' + u

    def _dq_fetch(self, url, retry=1, to=8):
        hd = {**self.dq_hd, 'Referer': url if 'detail.php' in url else self.plat['大全']['host'] + '/'}
        for i in range(retry + 1):
            try:
                r = requests.get(url, headers=hd, timeout=to, verify=False)
                if r and r.status_code == 200: return r
            except Exception: pass
            if i < retry: time.sleep(0.2)
        return None

    def _dq_list(self, html):
        vs, seen = [], set()
        for b in re.findall(r'<div class="card">(.*?)</div>\s*</div>', html, re.DOTALL):
            m = re.search(r'detail\.php\?vid=(\d+)', b)
            if not m: continue
            vid = m.group(1)
            if vid in seen: continue
            seen.add(vid)
            tm = re.search(r'<div class="title">(.*?)</div>', b, re.DOTALL)
            title = re.sub(r'<[^>]+>', '', tm.group(1)).strip() if tm else ''
            pm = re.search(r'data-original="([^"]+)"', b) or re.search(r'src="([^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', b)
            pic = self._dq_fix(pm.group(1)) if pm else ''
            em = re.search(r'(\d+)\s*集', b)
            rm = f"{em.group(1)}集" if em else ''
            if title: vs.append({"vod_id": f"大全@{vid}", "vod_name": title, "vod_pic": pic, "vod_remarks": rm})
        return vs

    def _dq_cat(self, pg, e):
        p = self.plat['大全']; tag = self._tag(e); cid = str(e.get('area', '1') or '1') if e else '1'
        kw = tag or self.dq_cat.get(cid, "")
        if kw: url = f"{p['host']}/?keyword={quote(kw)}&p={pg}"
        else: url = p['host'] + "/" if pg <= 1 else f"{p['host']}/?p={pg}"
        r = self._dq_fetch(url)
        if not r: return {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}
        vs = self._dq_list(r.text)
        pages = re.findall(r'\?p=(\d+)', r.text)
        pc = max(1, max(map(int, pages))) if pages else 1
        tm = re.search(r'共找到\s*([\d,]+)\s*部', r.text)
        tot = int(tm.group(1).replace(',', '')) if tm else 20 * pc
        return {"list": vs, "page": pg, "pagecount": pc, "limit": 20, "total": tot}

    # ---- 详情 ----
    def detailContent(self, ids):
        out = []
        for id in (ids if isinstance(ids, list) else [ids]):
            if not id: continue
            parts = id.split('@', 1)
            if len(parts) < 2: continue
            pid, did = parts
            if pid not in self.plat:
                out.append({'vod_id': id, 'vod_name': '平台不支持', 'vod_play_url': ''}); continue
            v = {'vod_id': id, 'vod_name': '未知', 'vod_pic': '', 'vod_remarks': '', 'vod_content': '', 'vod_play_from': '', 'vod_play_url': ''}
            try:
                v = {'七猫': self._qm_dt, '星芽': self._xy_dt, '西饭': self._xf_dt, '围观': self._gw_dt, '好看': self._hk_dt, '大全': self._dq_dt}[pid](did, v)
            except Exception: v['vod_name'] = '加载失败'
            out.append(v)
        return {'list': out}

    def _qm_dt(self, did, v):
        p = self.plat['七猫']; dd = unquote(did)
        sign = self._md5(f"playlet_id={dd}{self.keys}")
        try: r = requests.get(f"{p['url2']}?playlet_id={dd}&sign={sign}", headers=self._qm_hdr(), timeout=10, verify=False).json()
        except Exception: r = None
        if not r or not r.get('data'): return v
        d = r['data']; parts = []
        for i, ep in enumerate(d.get('play_list', []) or [], 1):
            u = ep.get('video_url') or ep.get('url') or ''
            if u: parts.append(f"{ep.get('sort') or ep.get('sort_name') or f'第{i}集'}${u}")
        v.update({'vod_name': d.get('title', ''), 'vod_pic': d.get('image_link', ''), 'vod_remarks': f"{d.get('total_episode_num', '')}集", 'vod_content': d.get('intro', ''), 'vod_play_from': '七猫专线', 'vod_play_url': '#'.join(parts)})
        return v

    def _xy_dt(self, did, v):
        r = self._req(did, hd=self._xy_auth(), to=10000)
        if not r or not r.get('data'): return v
        d = r['data']
        v.update({'vod_name': d.get('title', ''), 'vod_pic': d.get('cover_url', ''), 'vod_remarks': str(d.get('desc_tags', '')), 'vod_play_from': '星芽短剧',
                  'vod_play_url': '#'.join([f"{i['num']}${i['son_video_url']}" for i in d.get('theaters', [])])})
        return v

    def _xf_dt(self, did, v):
        p = self.plat['西饭']; dj, src = did.split('#', 1) if '#' in did else (did, '')
        r = self._xf_get(f"{p['host']}{p['url2']}", self._xf_p({'duanjuId': dj, 'source': src, 'openFrom': 'homescreen', 'type': '', 'pageID': 'page_inner_flow', 'density': '1.5'}))
        if not r or not r.get('result'): return v
        d = r['result']
        v.update({'vod_name': self._cn(d.get('title', '')), 'vod_pic': d.get('coverImageUrl', ''),
                  'vod_remarks': f"全{d.get('total', 0)}集" if d.get('updateStatus') == 'over' else f"更新至{d.get('total', 0)}集",
                  'vod_play_from': '西饭短剧',
                  'vod_play_url': '#'.join([f"{ep['index']}${ep['playUrl']}" for ep in d.get('episodeList', []) if ep.get('index') and ep.get('playUrl')])})
        return v

    def _gw_dt(self, vid, v):
        p = self.plat['围观']; params = {"oneId": vid, "page": 1, "pageSize": 1000, **self.gw}
        try:
            data = requests.get(p['host'] + p['url2'], headers={'Content-Type': 'application/json;charset=utf-8'}, timeout=10, params=params, verify=False).json()
        except Exception: return v
        vd = data.get("data", [])
        if not vd: return v
        first = vd[0]; actors, tags, desc, ec, vc = [], [], "", 0, 0
        try:
            for it in self._gw_search(first["title"], 1, 1).get("data", []):
                if it.get("oneId") == vid:
                    desc, actors, tags = it.get("description", ""), it.get("actors", []), it.get("shortPlayTag", [])
                    ec, vc = it.get("episodeCount", len(vd)), it.get("viewCount", 0); break
        except Exception: pass
        ec, vc = ec or len(vd), vc or first.get("collectionCount", 0)
        try:
            ai = data.get("actorItems", [])
            if ai and isinstance(ai, list):
                blocks = []
                for a in ai:
                    n = a.get("name", "")
                    if not n: continue
                    ls = [f"{n} 饰演 {a.get('rolePlayingName', '')}"]
                    if a.get("briefIntroduction"): ls.append(a["briefIntroduction"])
                    blocks.append("\n".join(ls))
                if blocks: desc += "\n\n演员信息：\n" + "\n\n".join(blocks)
        except Exception: pass
        rp = []
        if vc: rp.append(f"{vc/10000:.1f}万" if vc >= 10000 else f"▶️{vc}")
        if ec: rp.append(f"共{ec}集")
        urls = []
        for ep in vd:
            qi = {}
            for it in ep.get('videoClarityList', []) or []:
                n, u = it.get('name', ''), it.get('url', '')
                if not n or not u: continue
                qi['super' if '1080' in n else 'high' if '720' in n else 'normal' if '480' in n else n] = u
            urls.append(f"第{ep.get('playOrder', 1)}集${json.dumps(qi, ensure_ascii=False)}")
        v.update({"vod_name": first["title"], "vod_pic": first["vertPoster"], "vod_year": str(first.get("publishDate", "")),
                  "vod_remarks": " · ".join(rp) if rp else "", "vod_content": desc, "vod_play_from": "围观短剧",
                  "vod_play_url": "#".join(urls), "vod_actor": " · ".join(actors) if actors else "",
                  "type_name": " · ".join(tags) if tags else ""})
        return v

    def _hk_dt(self, sid, v):
        eps = self._hk_all_eps(sid, 10)
        if not eps:
            v.update({"vod_name": f"好看短剧 {sid}", "vod_play_from": "好看短剧", "vod_play_url": ""}); return v
        f = eps[0].get('content', {}); title = f.get('title', '')
        st = re.sub(r'\s*第\s*\d+\s*集\s*$', '', title).strip() or title if title else f"好看短剧 {sid}"
        parts, idx = [], 0
        for e in eps:
            u = self._hk_extract(e.get('content', {}).get('clarityUrl', []))
            if not u: continue
            idx += 1; parts.append(f"第{idx:02d}集${u}")
        v.update({"vod_name": st, "vod_pic": f.get('cover_url', '') or f.get('poster', '') or f.get('cover', ''),
                  "vod_remarks": f"{len(parts)}集", "vod_play_from": "好看短剧", "vod_play_url": "#".join(parts)})
        return v

    def _hk_all_eps(self, sid, rn=10):
        out, seen, cur, n = [], set(), "", 0
        while n < 200:
            n += 1
            batch, more, last = self._hk_batch(sid, cur, rn)
            if not batch: break
            added = 0
            for e in batch:
                ev = e.get('content', {}).get('vid')
                if ev and ev not in seen:
                    out.append(e); seen.add(ev); added += 1
            if last: cur = last
            else: break
            if not more and added == 0: break
            if len(batch) < rn and not more: break
        return out

    def _hk_batch(self, sid, svid, rn):
        parsed = urlparse(self.hk_base)
        q = {k: v[0] for k, v in parse_qs(parsed.query, keep_blank_values=True).items()}
        q['cuid'] = self._hk_cuid(); q['androidId'] = uuid.uuid4().hex[:16]; q['zid'] = uuid.uuid4().hex
        url = urlunparse(parsed._replace(query=urlencode(q, doseq=True)))
        ip = {"source_from":"kanju_shelf_playlet","enable_enter_playlet":"0","seek_time":"0","hotspot":"0","page_value":"playlet","auto_show_hot_point_panel":"0","type":"playlet","commonlist_id":str(int(time.time()*1000)),"scene":"","vid":svid,"enable_atlas":"0","mark_pn":"","uk":"","ctime":"0","from":"playlet_talos","id":sid,"rn":str(rn),"pn":"1","direction":"3"}
        try:
            r = requests.post(url, data={"video/commonlist": "&".join([f"{k}={v}" for k, v in ip.items()])},
                              headers={"Host": urlparse(url).netloc, "User-Agent": self._hk_ua(), "Content-Type": "application/x-www-form-urlencoded"}, timeout=15, verify=False)
            r.raise_for_status()
            d = r.json().get('video/commonlist', {}).get('data', {})
            batch = d.get('list') or d.get('results') or []
            last = ""
            for e in batch:
                vid = e.get('content', {}).get('vid')
                if vid: last = vid
            return batch, d.get('has_more', 0) == 1, last
        except Exception: return [], False, ""

    def _hk_extract(self, urls):
        if not urls: return ''
        return urls[min(2, len(urls) - 1)].get('url', '')

    def _dq_dt(self, vid, v):
        p = self.plat['大全']; r = self._dq_fetch(f"{p['host']}/detail.php?vid={vid}")
        if not r: return v
        h = r.text
        name = ''
        tm = re.search(r'<title>(.*?)</title>', h)
        if tm: name = tm.group(1).split('-')[0].split('_')[0].strip()
        if not name or name == '短剧大全':
            nm = re.search(r'<div class="video-title">(.*?)</div>', h, re.DOTALL)
            if nm: name = re.sub(r'<[^>]+>', '', nm.group(1)).strip()
        pic = ''
        pm = re.search(r'<video[^>]*poster="([^"]+)"', h) or re.search(r'data-original="([^"]+)"', h)
        if pm: pic = self._dq_fix(pm.group(1))
        desc = ''
        dm = re.search(r'<meta name="description" content="([^"]+)"', h)
        if dm: desc = re.sub(r'短剧大全-短剧网提供.*?在线观看[。，]?', '', dm.group(1).strip()).strip()
        year = ''
        ym = re.search(r'(\d{4})[年/-]', h)
        if ym: year = ym.group(1)
        urls = []
        eps = re.findall(r'<div[^>]*class="episode[^"]*"[^>]*data-src="([^"]+)"[^>]*>(.*?)</div>', h, re.DOTALL)
        if eps:
            for i, (src, raw) in enumerate(eps, 1):
                en = re.sub(r'<[^>]+>', '', raw).strip() or f"第{i}集"
                urls.append(f"{en}${src if src.startswith('http') else self._dq_fix(src)}")
        else:
            for i, u in enumerate(list(dict.fromkeys(re.findall(r"https?://[^\s\"'<>]+\.m3u8[^\s\"'<>]*", h))), 1):
                urls.append(f"第{i}集${u}")
        pf, pu = ("直链播放", '#'.join(urls)) if urls else ("默认线路", f"播放${p['host']}/detail.php?vid={vid}")
        v.update({"vod_name": name or f"短剧 {vid}", "vod_pic": pic, "vod_content": desc, "vod_year": year, "vod_play_from": pf, "vod_play_url": pu})
        return v

    # ---- 播放 ----
    def playerContent(self, flag, id, vipFlags):
        if '七猫' in flag: return {'parse': 0, 'url': id}
        if '西饭' in flag: return {"parse": 0, "playUrl": '', "url": id, "header": self.plat['西饭'].get('headers', self.hd)}
        if '好看' in flag: return {"parse": 0, "playUrl": '', "url": id, "header": self.hk_hd}
        if '围观' in flag:
            try: qd = json.loads(id); qd = qd if isinstance(qd, dict) else {}
            except Exception: qd = {}
            nm = {'super': '超清', 'high': '高清', 'normal': '流畅'}; urls = []
            for k in ('super', 'high', 'normal'):
                if qd.get(k): urls += [nm[k], qd[k]]
            if not urls:
                for k, u in qd.items():
                    if u and isinstance(u, str): urls += [k, u]; break
            hdr = {'Content-Type': 'application/json;charset=utf-8'}
            return {'parse': 0, 'playUrl': '', 'url': urls or id, 'header': hdr}
        if '大全' in flag or '直链' in flag or '默认线路' in flag: return self._dq_play(id)
        return {'parse': 0, 'url': id}

    def _dq_play(self, id):
        p = self.plat['大全']; u = id if id.startswith('http') else self._dq_fix(id)
        if '.m3u8' in u:
            return {"parse": 0, "url": u, "header": {'User-Agent': self.dq_hd['User-Agent'], 'Referer': p['host'] + '/'}}
        r = self._dq_fetch(u)
        if r:
            m = re.search(r"https?://[^\s\"'<>]+\.m3u8[^\s\"'<>]*", r.text)
            if m: return {"parse": 0, "url": m.group(0), "header": {'User-Agent': self.dq_hd['User-Agent'], 'Referer': u}}
        return {"parse": 1, "url": u, "header": self.dq_hd}

    # ---- 搜索 ----
    def searchContent(self, key, quick, pg="1"):
        pg = int(pg) if pg else 1
        if not key: return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
        vs, seen = [], set()

        def push(it):
            if not it: return
            vid, n = str(it.get('vod_id', '')).strip(), str(it.get('vod_name', '')).strip()
            if not vid or not n or vid in seen: return
            it['vod_id'], it['vod_name'] = vid, n; seen.add(vid); vs.append(it)

        # 七猫
        try:
            sign = self._md5(f"extend=page={pg}read_preference=0track_id=ec1280db127955061754851657967wd={key}{self.keys}")
            url = f"{self.plat['七猫']['host']}/api/v1/playlet/search?extend=&page={pg}&wd={quote(key)}&read_preference=0&track_id=ec1280db127955061754851657967&sign={sign}"
            r = self._req(url, hd={**self._qm_hdr(), **self.hd}, to=6000)
            if r:
                for i in r.get('data', {}).get('list', []):
                    vid, n = i.get('id', ''), ' '.join(self._cn(i.get('title', '')).split())
                    if vid and n: push({'vod_id': f"七猫@{quote(str(vid))}", 'vod_name': n, 'vod_pic': i.get('image_link', ''), 'vod_remarks': f"七猫短剧｜{i.get('total_num', '')}集"})
        except Exception: pass

        # 星芽
        try:
            for i in self._xy_search(key):
                v = self._xy_vod(i)
                if v: v['vod_remarks'] = f"星芽短剧｜{v.get('vod_remarks', '')}"; push(v)
        except Exception: pass

        # 西饭
        try:
            r = self._xf_get(f"{self.plat['西饭']['host']}{self.plat['西饭']['search']}", self._xf_p({'keyword': key, 'pageIndex': str(pg)}))
            if r:
                for v in self._xf_parse(r): v['vod_remarks'] = f"西饭短剧｜{v.get('vod_remarks', '')}"; push(v)
        except Exception: pass

        # 围观
        try:
            for i in self._gw_search(key, pg).get("data", []):
                v = self._gw_vod(i); v['vod_remarks'] = f"围观短剧｜{v.get('vod_remarks', '')}"; push(v)
        except Exception: pass

        # 好看
        try:
            for v in self._hk_search(key): push({"vod_id": f"好看@{v['id']}", "vod_name": v.get('title', ''), "vod_pic": v.get('cover_url', ''), "vod_remarks": "好看短剧"})
        except Exception: pass

        # 大全
        try:
            r = self._dq_fetch(f"{self.plat['大全']['host']}/?keyword={quote(key)}&p={pg}")
            if r and r.text:
                for it in self._dq_list(r.text): it['vod_remarks'] = f"短剧大全｜{it.get('vod_remarks', '')}"; push(it)
        except Exception: pass

        return {'list': vs, 'page': pg, 'pagecount': 1, 'limit': len(vs), 'total': len(vs)}