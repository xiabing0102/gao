# -*- coding: utf-8 -*-
# 无水印资源网 py 源（苹果 CMS 标准采集 API）
# API: https://api.wsyzy.net/api.php/provide/vod/
import re
import json
import requests
import warnings
from urllib.parse import quote

try:
    warnings.filterwarnings('ignore')
    requests.packages.urllib3.disable_warnings()
except Exception:
    pass

from base.spider import Spider

API = 'https://api.wsyzy.net/api.php/provide/vod/'

# 分类（主分类映射到子分类 id 列表，苹果 CMS API t 只认子分类）
MAIN_CATS = [
    ('电影', '1'), ('电视剧', '2'), ('综艺', '3'), ('动漫', '4'),
    ('短剧', '5'), ('伦理', '6'),
]

# 子分类映射（主分类 → [子分类 id]）
CAT_SUBS = {
    '1': ['6', '7', '8', '9', '10', '11', '12', '20', '39', '62', '70', '71'],
    '2': ['13', '14', '15', '16', '17', '18', '19', '23', '72'],
    '3': ['25', '26', '27', '28', '47'],
    '4': ['29', '30', '31', '44', '45', '63'],
    '5': ['54', '64', '65', '66', '67', '68', '69', '73', '76'],
    '6': ['55', '56', '57', '58', '59', '60', '61'],
}

# 类型筛选（主分类 → 子分类选项）
TYPE_FILTERS = {
    '1': [('', '全部'), ('6', '动作片'), ('7', '喜剧片'), ('8', '爱情片'), ('9', '科幻片'),
          ('10', '恐怖片'), ('11', '剧情片'), ('12', '战争片'), ('20', '纪录片'), ('39', '动画片'),
          ('62', '4K电影'), ('70', '邵氏电影'), ('71', 'Netflix电影')],
    '2': [('', '全部'), ('13', '国产剧'), ('14', '欧美剧'), ('15', '韩剧'), ('16', '日剧'),
          ('17', '港剧'), ('18', '台剧'), ('19', '泰剧'), ('23', '海外剧'), ('72', 'Netflix自制剧')],
    '3': [('', '全部'), ('25', '大陆综艺'), ('26', '日韩综艺'), ('27', '港台综艺'), ('28', '欧美综艺'),
          ('47', '演唱会')],
    '4': [('', '全部'), ('29', '国产动漫'), ('30', '日韩动漫'), ('31', '欧美动漫'),
          ('44', '港台动漫'), ('45', '海外动漫'), ('63', '有声动漫')],
    '5': [('', '全部'), ('54', '爽文短剧'), ('64', '女频恋爱'), ('65', '反转爽剧'), ('66', '古装仙侠'),
          ('67', '年代穿越'), ('68', '脑洞悬疑'), ('69', '现代都市'), ('73', '擦边短剧'), ('76', '漫剧')],
    '6': [('', '全部'), ('55', '伦理'), ('56', '港台三级'), ('57', '韩国伦理'), ('58', '西方伦理'),
          ('59', '日本伦理'), ('60', '两性课堂'), ('61', '写真热舞')],
}


class Spider(Spider):
    def getName(self):
        return '无水印资源'

    def init(self, extend=''):
        self.header = {'User-Agent': 'Mozilla/5.0 (Linux; Android 16; 2407FRK8EC Build/BP2A.250605.031.A3) AppleWebKit/537.36'}
        self.api = API
        # 统一 session（cookie 持久化到文件：验证码输一次后续免验证）
        self.sess = requests.Session()
        self.sess.headers.update(self.header)
        self._cookie_file = self._cookie_path()
        self._load_cookies()
        # 分类先设置
        self.classes = [{'type_id': 'c:' + cid, 'type_name': name}
                        for name, cid in MAIN_CATS]

    def _cookie_path(self):
        """cookie 文件路径（壳缓存目录，可写）"""
        for base in ['/data/data/com.9xiu.box/files/cache',
                     '/data/data/com.9xiu.box/cache',
                     '/sdcard/Android/data/com.9xiu.box/cache',
                     '/tmp']:
            try:
                import os
                os.makedirs(base, exist_ok=True)
                return os.path.join(base, 'wsyzy_cookie.txt')
            except Exception:
                continue
        return '/tmp/wsyzy_cookie.txt'

    def _load_cookies(self):
        """从文件加载 cookie"""
        try:
            with open(self._cookie_file) as f:
                sid = f.read().strip()
            if sid:
                self.sess.cookies.set('PHPSESSID', sid, domain='api.wsyzy.net')
        except Exception:
            pass

    def _save_cookies(self):
        """保存 cookie 到文件"""
        try:
            sid = self.sess.cookies.get('PHPSESSID', domain='api.wsyzy.net')
            if sid:
                with open(self._cookie_file, 'w') as f:
                    f.write(sid)
        except Exception:
            pass

    def _get(self, params):
        try:
            r = self.sess.get(self.api, params=params, timeout=10, verify=False)
            d = json.loads(r.text)
            return d
        except Exception:
            return {}

    # ============ 首页 ============
    def homeContent(self, filter):
        classes = [{'type_id': 'c:' + cid, 'type_name': name}
                   for name, cid in MAIN_CATS]
        filters = {}
        for name, cid in MAIN_CATS:
            subs = TYPE_FILTERS.get(cid, [])
            if subs:
                filters['c:' + cid] = [{
                    'key': 'sub', 'name': '分类',
                    'value': [{'v': '', 'n': '全部'}] +
                             [{'v': sid, 'n': sname} for sid, sname in subs]}]
        # 首页 = 最新
        lst = []
        try:
            d = self._get({'ac': 'list', 'pg': '1'})
            lst = [self._fmt_vod(v) for v in d.get('list', [])]
            lst = self._fill_pics(lst)
        except Exception:
            pass
        return {'class': classes, 'filters': filters, 'list': lst}

    def homeVideoContent(self):
        try:
            d = self._get({'ac': 'list', 'pg': '1'})
            vods = [self._fmt_vod(v) for v in d.get('list', [])]
            return {'list': self._fill_pics(vods)}
        except Exception:
            return {}

    def _fmt_vod(self, v):
        return {
            'vod_id': str(v.get('vod_id', '')),
            'vod_name': v.get('vod_name', ''),
            'vod_pic': v.get('vod_pic', ''),
            'vod_remarks': v.get('vod_remarks', ''),
        }

    # ============ 分类 ============
    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg) if str(pg).isdigit() else 1
            cid = str(tid)
            if cid.startswith('c:'):
                cid = cid[2:]
            # 筛选合并
            sub = ''
            for d in [filter, extend]:
                if isinstance(d, dict) and d.get('sub'):
                    sub = str(d['sub'])
            if sub:
                cid = sub
            # 主分类 → 轮询子分类合并（每子分类取前 N 条）
            if cid in CAT_SUBS:
                vods = []
                for sid in CAT_SUBS[cid]:
                    if len(vods) >= 30:
                        break
                    d = self._get({'ac': 'list', 't': sid, 'pg': str(page)})
                    for v in d.get('list', []):
                        vods.append(self._fmt_vod(v))
                return {'list': self._fill_pics(vods[:30]), 'page': page, 'pagecount': 1,
                        'limit': 30, 'total': 99999}
            # 子分类直接查
            d = self._get({'ac': 'list', 't': cid, 'pg': str(page)})
            vods = [self._fmt_vod(v) for v in d.get('list', [])]
            return {'list': self._fill_pics(vods), 'page': page,
                    'pagecount': int(d.get('pagecount', 1) or 1),
                    'limit': 30, 'total': int(d.get('total', 0) or 0)}
        except Exception:
            return {'list': []}

    def _fill_pics(self, vods):
        """列表无图 → 批量 detail 补图（ac=detail&ids= 带 vod_pic）"""
        if not vods:
            return vods
        try:
            ids = ','.join(v['vod_id'] for v in vods if v.get('vod_id'))
            if not ids:
                return vods
            d = self._get({'ac': 'detail', 'ids': ids})
            pic_map = {str(v.get('vod_id')): v.get('vod_pic', '') for v in d.get('list', [])}
            for v in vods:
                v['vod_pic'] = pic_map.get(str(v.get('vod_id')), v.get('vod_pic', ''))
        except Exception:
            pass
        return vods

    # ============ 详情 ============
    def detailContent(self, ids):
        try:
            if isinstance(ids, list):
                ids = ids[0]
            vid = str(ids)
            if not vid.isdigit():
                # 可能是 URL，取尾部数字
                m = re.search(r'(\d+)', vid)
                vid = m.group(1) if m else '1'
            d = self._get({'ac': 'detail', 'ids': vid})
            if not d.get('list'):
                return {'list': []}
            v = d['list'][0]
            vod = {
                'vod_id': vid,
                'vod_name': v.get('vod_name', ''),
                'vod_pic': v.get('vod_pic', ''),
                'vod_remarks': v.get('vod_remarks', ''),
                'vod_year': v.get('vod_year', ''),
                'vod_area': v.get('vod_area', ''),
                'vod_director': v.get('vod_director', ''),
                'vod_actor': v.get('vod_actor', ''),
                'vod_content': re.sub(r'<[^>]+>', '', str(v.get('vod_content', '')))[:200],
                'vod_play_from': v.get('vod_play_from', ''),
                'vod_play_url': v.get('vod_play_url', ''),
            }
            return {'list': [vod]}
        except Exception:
            return {'list': []}

    # ============ 搜索（suggest 接口，无验证码） ============
    def searchContent(self, key, quick, pg='1'):
        try:
            key = str(key or '').strip()
            if not key:
                return {'list': []}
            # suggest 接口（mid=1&wd=，无验证码）
            r = self.sess.get(
                f"https://api.wsyzy.net/index.php/ajax/suggest?mid=1&wd={quote(key)}",
                timeout=10, verify=False)
            d = json.loads(r.text)
            vods = []
            for it in d.get('list', [])[:30]:
                vods.append({
                    'vod_id': str(it.get('id', '')),
                    'vod_name': it.get('name', ''),
                    'vod_pic': (it.get('pic') or '').replace('\\/', '/'),
                    'vod_remarks': '',
                })
            return {'list': vods}
        except Exception:
            return {'list': []}

    # ============ 播放（直链 m3u8） ============
    def playerContent(self, flag, id, vipFlags):
        try:
            url = str(id or '').strip()
            if url.startswith('http'):
                return {'parse': 0, 'playUrl': '', 'url': url, 'header': self.header}
            return {'parse': 1, 'playUrl': '', 'url': url, 'header': self.header}
        except Exception:
            return {'parse': 1, 'playUrl': '', 'url': id, 'header': self.header}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass
