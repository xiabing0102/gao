from base.spider import Spider
import requests
import json
import re
import sys
from urllib.parse import quote

class Spider(Spider):
    def getName(self):
        return "小心儿悠悠"

    def init(self, extend=""):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.kuwo.cn/',
        }
        
    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {}
        cateId = [
            {"type_name": "华语男", "type_id": "1"},
            {"type_name": "华语女", "type_id": "2"},
            {"type_name": "华语组合", "type_id": "3"},
            {"type_name": "日韩男", "type_id": "4"},
            {"type_name": "日韩女", "type_id": "5"},
            {"type_name": "日韩组合", "type_id": "6"},
            {"type_name": "欧美男", "type_id": "7"},
            {"type_name": "欧美女", "type_id": "8"},
            {"type_name": "欧美组合", "type_id": "9"},
            {"type_name": "其他", "type_id": "0"}
        ]
        result['class'] = cateId
        return result

    def homeVideoContent(self):
        result = self.categoryContent("1", 1, False, {})
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        url = f"http://wapi.kuwo.cn/api/www/artist/artistInfo?category={tid}&prefix=&pn={pg}&rn=30"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://www.kuwo.cn/'
        }
        
        try:
            r = requests.get(url, headers=headers, timeout=10)
            data = r.json()
            videos = []
            if data.get('data') and data['data'].get('artistList'):
                for item in data['data']['artistList']:
                    video = {
                        "vod_id": str(item.get('id', '')),
                        "vod_name": item.get('name', ''),
                        "vod_pic": item.get('pic300') or item.get('pic') or item.get('pic120', ''),
                        "vod_remarks": f""
                    }
                    videos.append(video)
            
            result['list'] = videos
            result['page'] = pg
            result['pagecount'] = 9999
            result['limit'] = 90
            result['total'] = 999999
            
        except Exception as e:
            result['list'] = []
        
        return result

    def detailContent(self, ids):
        rid = ids[0]
        result = {}
        
        info_url = f"http://wapi.kuwo.cn/api/www/artist/artist?artistid={rid}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://www.kuwo.cn/'
        }
        
        try:
            r = requests.get(info_url, headers=headers, timeout=10)
            info_data = r.json().get('data', {})
            
            artist_name = info_data.get('name', '')
            
            all_songs = self._get_artist_songs(rid)
            
            artist_info = info_data.get('info', '')
            artist_info = re.sub(r'<[^>]+>', '', artist_info)
            artist_info = artist_info.replace('&nbsp;', ' ')
            artist_info = artist_info.replace('\r\n', '\n').replace('\r', '\n')
            artist_info = artist_info.strip()
            
            max_songs = 300
            if len(all_songs) > max_songs:
                all_songs = all_songs[:max_songs]
            
            play_arr = []
            for i, song in enumerate(all_songs):
                name = re.sub(r'[$#]', '', song.get('name', '')).strip()
                song_id = song.get('rid', '')
                album = song.get('album', '')
                
                if album:
                    play_arr.append(f"{name} - {album}${song_id}")
                else:
                    play_arr.append(f"{name}${song_id}")
            
            vod = {
                "vod_id": rid,
                "vod_name": artist_name,
                "vod_pic": info_data.get('pic300') or info_data.get('pic', ''),
                "vod_content": artist_info if artist_info else "暂无歌手简介",
                "vod_remarks": f"歌曲 :   {len(all_songs)}首",
                "vod_actor": artist_name,
                "vod_play_from": "酷我音乐",
                "vod_play_url": "#".join(play_arr)
            }
            
            result['list'] = [vod]
            
        except Exception as e:
            vod = {
                "vod_id": rid,
                "vod_name": "加载失败",
                "vod_content": f"加载歌手信息失败: {str(e)}",
                "vod_remarks": "加载失败",
                "vod_actor": "未知",
                "vod_play_from": "酷我音乐",
                "vod_play_url": ""
            }
            result['list'] = [vod]
        
        return result

    def _get_artist_songs(self, rid):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://www.kuwo.cn/'
        }
        
        songs = []
        max_pages = 10
        
        for page in range(1, max_pages + 1):
            try:
                url = f"http://wapi.kuwo.cn/api/www/artist/artistMusic?artistid={rid}&pn={page}&rn=30"
                response = requests.get(url, headers=headers, timeout=10)
                data = response.json()
                
                if data.get('code') == 200:
                    music_data = data.get('data', {})
                    song_list = music_data.get('list', [])
                    
                    if not song_list:
                        break
                    
                    for song in song_list:
                        song_name = song.get('name', '').strip()
                        if song_name:
                            songs.append({
                                'name': song_name,
                                'rid': song.get('rid', ''),
                                'album': song.get('album', ''),
                                'duration': song.get('duration', '')
                            })
                    
                    if len(songs) >= 300:
                        songs = songs[:300]
                        break
                        
            except Exception:
                continue
        
        return songs

    def playerContent(self, flag, id, vipFlags):
        result = {}
        rid = id
        
        qualities = []
        
        quality_list = [
            ("无损FLAC", 2000, "flac"),
            ("高品质320K", 320, "mp3"),
            ("标准128K", 128, "")
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10)',
            'Referer': 'https://www.kuwo.cn/'
        }
        
        for quality_name, bitrate, format_type in quality_list:
            try:
                api_url = f"https://nmobi.kuwo.cn/mobi.s?f=web&user=0&source=kwplayer_ar_4.4.2.7_B_nuoweida_vh.apk&type=convert_url_with_sign&rid={rid}&bitrate={bitrate}&format={format_type}"
                r = requests.get(api_url, headers=headers, timeout=5)
                data = r.json()
                if data.get('code') == 200 and data.get('data') and data['data'].get('url'):
                    qualities.append((quality_name, data['data']['url']))
            except Exception:
                continue
        
        if not qualities:
            result["parse"] = 0
            result["playUrl"] = ""
            result["url"] = ""
            result["header"] = {}
            return result
        
        urls = []
        for quality_name, quality_url in qualities:
            urls.append(quality_name)
            urls.append(quality_url)
        
        lrc = ""
        pic = ""
        
        try:
            lrc_api = f"https://kuwo.cn/openapi/v1/www/lyric/getlyric?musicId={rid}"
            lr = requests.get(lrc_api, timeout=5)
            lj = lr.json()
            if lj.get('data') and lj['data'].get('lrclist'):
                lrc = "\n".join([f"[{self._format_time(float(item.get('time', 0)))}]{item.get('lineLyric', '')}" 
                               for item in lj['data']['lrclist']])
        except Exception:
            pass
        
        try:
            pic_url = f"http://artistpicserver.kuwo.cn/pic.web?type=rid_pic&pictype=url&size=500&rid={rid}"
            pr = requests.get(pic_url, timeout=5)
            if pr.text.startswith('http'):
                pic = pr.text.strip()
            else:
                pic = pic_url
        except Exception:
            pic = f"http://artistpicserver.kuwo.cn/pic.web?type=rid_pic&pictype=url&size=500&rid={rid}"
        
        result["parse"] = 0
        result["playUrl"] = ""
        result["url"] = urls
        result["header"] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.kuwo.cn/"
        }
        
        if lrc:
            result["lrc"] = lrc
        
        if pic:
            result["pic"] = pic
        
        return result

    def _format_time(self, seconds):
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m:02d}:{s:05.2f}"

    def searchContent(self, key, quick, pg=1):
        result = {}
        wd = quote(key)
        page_num = (int(pg) - 1) * 30
        url = f"https://search.kuwo.cn/r.s?client=kt&pn={page_num}&rn=30&all={wd}&vipver=1&ft=artist&encoding=utf8&rformat=json&mobi=1"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://www.kuwo.cn/'
        }
        
        try:
            r = requests.get(url, headers=headers, timeout=10)
            data = r.json()
            videos = []
            if data.get('abslist'):
                base_path = data.get('BASEPICPATH', 'http://img1.kuwo.cn/star/starheads/')
                for item in data['abslist']:
                    aid = item.get('ARTISTID') or item.get('DC_TARGETID', '')
                    pic = item.get('hts_PICPATH') or (base_path + item['PICPATH'] if item.get('PICPATH') else '')
                    video = {
                        "vod_id": str(aid),
                        "vod_name": item.get('ARTIST', ''),
                        "vod_pic": pic,
                        "vod_remarks": f"歌曲 :  {item.get('SONGNUM', 0)}首"
                    }
                    videos.append(video)
            
            result['list'] = videos
            result['page'] = pg
            result['pagecount'] = 9999
            result['limit'] = 30
            result['total'] = 999999
            
        except Exception as e:
            result['list'] = []
        
        return result

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def localProxy(self, param):
        return None
