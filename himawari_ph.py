#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""気象庁 気象衛星センター（MSC）のひまわり画像「東南アジア2（se2）」から
   フィリピン周辺を切り出す。10分ごと、約5km/px、海岸線と5度の格子入り。
   se2 は 105〜140E / 0〜30N の正距円筒（20px/度）、701x601px。"""
import io, re, datetime, requests, concurrent.futures as _cf
from PIL import Image, ImageDraw

MSC   = "https://www.data.jma.go.jp/mscweb/data/himawari/"
PAGE  = MSC + "sat_img.php?area=se2"
IMG   = MSC + "img/se2/se2_%s_%s.jpg"
HDR   = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/140.0 Safari/537.36",
         "Referer": PAGE}
W0, N0, PPD = 105.0, 30.0, 20.0            # 左上の経度・緯度、1度あたりのpx
CROP  = (113.0, 22.0, 131.0, 3.0)          # 西, 北, 東, 南
SCALE = 2
NAMES = {"hrp": "Heavy rainfall potential", "snd": "Sandwich", "b13": "IR B13"}
MONTH = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July",
                                      "August", "September", "October", "November", "December"], 1)}

_TIMES = None


def _times():
    """[(ファイル名の時刻HHMM, 表示時刻datetime), ...] 新しい順"""
    global _TIMES
    if _TIMES is not None:
        return _TIMES
    out = []
    try:
        t = requests.get(PAGE, headers=HDR, timeout=30).text
        for v, hh, mm, d, mon, y in re.findall(
                r'<option[^>]*value="(\d{4})"[^>]*>\s*(\d{2}):(\d{2}) UTC (\d{1,2}) (\w+) (\d{4})', t):
            if mon in MONTH:
                out.append((v, datetime.datetime(int(y), MONTH[mon], int(d), int(hh), int(mm))))
    except Exception as ex:
        print("    ひまわり時刻一覧エラー:", str(ex)[:80])
    _TIMES = out
    return out


def _crop(im):
    w, n, e, s = CROP
    box = (int(round((w - W0) * PPD)), int(round((N0 - n) * PPD)),
           int(round((e - W0) * PPD)), int(round((N0 - s) * PPD)))
    im = im.convert("RGB").crop(box)
    return im.resize((im.size[0] * SCALE, im.size[1] * SCALE), Image.LANCZOS)


def _caption(im, band, dt):
    dr = ImageDraw.Draw(im)
    h = im.size[1]
    dr.rectangle([4, h - 20, 420, h - 2], fill=(0, 0, 0))
    dr.text((8, h - 16), "Himawari-9 %s  %s  (JMA)" % (NAMES.get(band, band), dt.strftime("%d %H%MZ")),
            fill=(255, 255, 160))


def collect_series(s, save):
    """radar_collect から呼ぶ。[{file, ts}] を新しい順で返す"""
    key  = s.get("key")
    band = str(s.get("code") or "hrp")
    step = max(10, int(s.get("step", 10)) // 10 * 10)
    n    = int(s.get("frames", 12))
    specs = _times()[::step // 10][:n]

    def one(spec):
        v, dt = spec
        try:
            r = requests.get(IMG % (band, v), headers=HDR, timeout=30)
            if r.status_code != 200 or len(r.content) < 2000:
                return None
            im = _crop(Image.open(io.BytesIO(r.content)))
            _caption(im, band, dt)
            ts = dt.strftime("%Y%m%d%H%M00")
            fn = save(im, "%s_%s.jpg" % (key, ts))
            return {"file": fn, "ts": ts} if fn else None
        except Exception:
            return None

    with _cf.ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(one, specs))
    frames = [r for r in res if r]
    print("  %-12s %d/%d 枚" % (key, len(frames), len(specs)))
    return frames
