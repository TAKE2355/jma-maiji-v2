#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JAXA GSMaP_NOW（衛星推定の降水強度）をフィリピン域の地図に重ねる。
   RainViewer は PAGASA のレーダーに依存しており、配信が止まるとマニラ周辺が空白になるため、
   レーダーとは独立した衛星推定を使う。0.1度格子・30分ごと・観測から約1時間遅れで公開。"""
import io, re, datetime, requests
from PIL import Image, ImageDraw

import metair_all_mail_v2 as M   # 地図（Esri）とタイル範囲の計算を共用

GSM_SITE   = "https://sharaku.eorc.jaxa.jp"
GSM_LATEST = GSM_SITE + "/GSMaP_NOW/js/gsmap_set_latest.js"
GSM_TILE   = (GSM_SITE + "/cgi-bin/trmm/GSMaP_NOW/tilemap/tile_rain.py"
              "?prod=rain&year=%d&month=%d&day=%d&hour=%d&min=%d&z=%d&x=%d&y=%d")
GSM_HDR    = {"User-Agent": M.RV_HDR["User-Agent"],
              "Referer": GSM_SITE + "/GSMaP_NOW/index.htm"}

_GSM_FRAMES = None


def _latest():
    """公開済みの最新時刻（UTC）。失敗したら現在時刻から逆算する"""
    try:
        r = requests.get(GSM_LATEST, headers=GSM_HDR, timeout=20)
        t = r.text
        g = lambda k: int(re.search(r"var\s+%s\s*=\s*0*(\d+)" % k, t).group(1))
        return datetime.datetime(g("ltYer"), g("ltMon"), g("ltDay"), g("ltHour"), g("ltMin"))
    except Exception as ex:
        print("    GSMaP最新時刻エラー:", str(ex)[:80])
        now = datetime.datetime.utcnow() - datetime.timedelta(minutes=70)
        return now.replace(minute=(now.minute // 30) * 30, second=0, microsecond=0)


def gsm_frames(step=30, n=12):
    """[(時刻14桁UTC, datetime), ...] を新しい順で返す"""
    global _GSM_FRAMES
    if _GSM_FRAMES is None:
        t0 = _latest()
        _GSM_FRAMES = [t0 - datetime.timedelta(minutes=30 * i) for i in range(48)]
    step = max(30, int(step) // 30 * 30)
    k = step // 30
    sel = _GSM_FRAMES[::k][:n]
    return [(dt.strftime("%Y%m%d%H%M00"), dt) for dt in sel]


def _tile(dt, z, x, y):
    """降水タイル（透過PNG）。降水なしの空タイルは None"""
    ty = (2 ** z) - 1 - y            # TMS（y軸反転）
    u = GSM_TILE % (dt.year, dt.month, dt.day, dt.hour, dt.minute, z, x, ty)
    try:
        r = requests.get(u, headers=GSM_HDR, timeout=20)
        # 未公開の時刻は 70バイト程度のダミーが返る（降水なしの正規タイルは数百バイト）
        if r.status_code == 200 and r.content[:4] == b"\x89PNG" and len(r.content) > 120:
            im = Image.open(io.BytesIO(r.content)).convert("RGBA")
            if im.size != (256, 256):
                im = im.resize((256, 256), Image.NEAREST)
            return im, len(r.content)
    except Exception:
        pass
    return None, 0


def _caption(cv, ts_label):
    dr = ImageDraw.Draw(cv)
    h = cv.size[1]
    dr.rectangle([4, h - 20, 420, h - 2], fill=(255, 255, 255, 220))
    dr.text((8, h - 16), "JAXA GSMaP_NOW  satellite rain estimate  %s  / (C) Esri" % ts_label,
            fill=(60, 60, 60, 255))


def get_gsm_image(dt, region="MNL"):
    """降水タイルを地図に重ねて1枚にする。時刻のデータが未公開なら None"""
    try:
        cv = M._rv_basemap(region)
        z, x0, x1, y0, y1 = M._rv_geom(region)
        got = 0
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                tl, size = _tile(dt, z, x, y)
                if tl is None:
                    continue
                got += 1
                cv.paste(tl, ((x - x0) * 256, (y - y0) * 256), tl)
        if got == 0:
            return None
        _caption(cv, dt.strftime("%H%MZ"))
        return cv.convert("RGB")
    except Exception as ex:
        print("    GSMaP画像エラー[%s]: %s" % (region, str(ex)[:90]))
        return None


def collect_series(s, save):
    """radar_collect から呼ぶ。save(im, name) で保存し [{file, ts}] を新しい順で返す"""
    import concurrent.futures as _cf
    key  = s.get("key")
    view = str(s.get("code") or "MNL")
    specs = gsm_frames(int(s.get("step", 30)), int(s.get("frames", 12)))
    M._rv_basemap(view)              # 地図はスレッド間で共有するため先に作る

    def one(spec):
        ts, dt = spec
        im = get_gsm_image(dt, view)
        fn = save(im, "%s_%s.jpg" % (key, ts)) if im is not None else None
        return {"file": fn, "ts": ts} if fn else None

    with _cf.ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(one, specs))
    frames = [r for r in res if r]
    print("  %-12s %d/%d 枚" % (key, len(frames), len(specs)))
    return frames
