import re, requests, json
from urllib.parse import quote, urljoin
from base.spider import Spider

HOST = 'https://www.cliclidm.com'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
JX = 'https://jx.wujinkk.com/'
CATEGORIES = {'cndm': '中国动漫', 'manju': '漫剧', 'jpdm': '日本动漫', 'ysdm': '有声动漫', 'omdm': '欧美动漫', 'dmdy': '动漫电影'}

class Spider(Spider):
    def init(self, extend=""):
        self.s = requests.Session()
        self.s.headers.update({'User-Agent': UA, 'Referer': HOST + '/'})

    def _get(self, url):
        r = self.s.get(url, timeout=15)
        r.encoding = 'utf-8'
        return r.text

    def _items(self, html):
        out = []
        for m in re.finditer(r'<a class="link" href="(/dm/[^"]+)" title="([^"]+)".*?data-original="([^"]+)"', html, re.S):
            out.append({'vod_id': m.group(1).rstrip('/').split('/')[-1], 'vod_name': m.group(2), 'vod_pic': m.group(3), 'vod_remarks': ''})
        return out

    def homeContent(self, filter=False):
        cats = [{'type_id': k, 'type_name': v} for k, v in CATEGORIES.items()]
        html = self._get(HOST + '/')
        lst = []
        for v in self._items(html):
            if v['vod_id'] not in [x['vod_id'] for x in lst]:
                lst.append(v)
        return {'class': cats, 'list': lst}

    def homeVideoContent(self):
        return {'list': self._items(self._get(HOST + '/dmtype/jpdm/'))}

    def categoryContent(self, tid, pg, filter=False, extend=""):
        url = HOST + '/dmtype/' + str(tid) + ('-' + str(pg) + '/' if int(pg) > 1 else '/')
        html = self._get(url)
        return {'list': self._items(html), 'page': int(pg), 'pagecount': self._pagecount(html, int(pg)), 'limit': 20, 'total': 99999}

    def _pagecount(self, html, cur=1):
        nums = [int(x) for x in re.findall(r'/dmtype/[^/]+?-(\d+)/', html)]
        return max(nums) if nums else max(cur, 1)

    def detailContent(self, ids):
        vid = str(ids[0]).rstrip('/').split('/')[-1]
        html = self._get(HOST + '/dm/' + vid + '/')
        name = re.search(r'<h1>(.*?)</h1>', html, re.S)
        pic = re.search(r'data-original="([^"]+)"', html)
        tags = re.findall(r'<span>([^<]+)</span>', html)
        meta = dict(re.findall(r'<span class="label">([^<]+)：</span><span>([^<]+)</span>', html))
        desc = re.search(r'<p class="movie-description">(.*?)</p>', html, re.S)
        cast = {}
        for cm in re.finditer(r'<div class="movie-cast"><h3>([^<]+)</h3><ul>(.*?)</ul>', html, re.S):
            cast[cm.group(1)] = ','.join(re.findall(r'>([^<]+)</a>', cm.group(2)))
        pfs, segs = [], []
        ph = self._get(HOST + '/dongman/' + vid + '-1-1/')
        fm = re.search(r'"from":"([^"]+)"', ph)
        pfs.append(fm.group(1) if fm else 'wjm3u8')
        eps = []
        for em in re.finditer(r'href="(/dongman/' + re.escape(vid) + r'-\d+-(\d+)/)"[^>]*title="([^"]+)"', ph):
            eps.append((int(em.group(2)), em.group(3), em.group(1)))
        eps.sort(key=lambda x: x[0])
        seen = set()
        segs.append('#'.join([(e[1] + '$' + e[2]) for e in eps if not (e[1] in seen or seen.add(e[1]))]))
        return {'list': [{'vod_id': vid, 'vod_name': name.group(1) if name else vid, 'vod_pic': pic.group(1) if pic else '', 'vod_remarks': ','.join(tags) if tags else '', 'vod_year': meta.get('年份', ''), 'vod_area': meta.get('地区', ''), 'vod_director': cast.get('导演', ''), 'vod_actor': cast.get('主演', ''), 'vod_content': re.sub(r'<[^>]+>', '', desc.group(1)) if desc else '', 'vod_play_from': '$$$'.join(pfs), 'vod_play_url': '$$$'.join(segs)}]}

    def searchContent(self, key, quick=False, pg='1'):
        html = self._get(HOST + '/vodsearch/-------------/?wd=' + quote(key))
        return {'list': self._items(html), 'page': 1, 'pagecount': 1, 'limit': 20, 'total': 99999}

    def playerContent(self, flag, id, vipFlags=None):
        url = urljoin(HOST, id) if id.startswith('/') else HOST + '/dongman/' + str(id).split('/')[-1].split('-')[0] + '-1-1/'
        try:
            html = self._get(url)
            m = re.search(r'player_aaaa=(\{.*?\})', html, re.S)
            if m:
                d = json.loads(m.group(1))
                u = d.get('url', '')
                if u and re.search(r'\.(m3u8|mp4|mkv|flv)(\?|$)', u, re.I):
                    return {'parse': 0, 'url': u, 'header': {'User-Agent': UA, 'Referer': JX}}
        except:
            pass
        return {'parse': 1, 'url': url}

    def localProxy(self, param):
        return [200, 'text/plain', '']