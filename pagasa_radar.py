#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PAGASA（フィリピン気象庁）のレーダーモザイクを panahon.gov.ph から取得して地図に重ねる。
   エコーが1コマも無いとき（配信停止中など）は JAXA GSMaP_NOW（gsmap.py）に切り替える。

   panahon.gov.ph の仕様（2026年11月時点）
   - 時系列: /api/v1/radar/timeline?token=..&sublayer=mosaic-reflectivity
       data.timeline[].observed_at_unix / data.bounds [lon0,lat0,lon1,lat1]
       data.scale {max, sqrt, mode} / data.colormap [[[値], [r,g,b,a]], ...]
       data.tile_version / data.image_sizes / data.no_data
   - 画像:   /api/v1/radar-data-image?token=..&sublayer=..&t=<unix>&mode=..&size=2048&v=..
       Webメルカトル（EPSG:3857）で長辺 size px。赤チャンネル=値（0〜1 × max、sqrt なら二乗）、
       アルファ=有効域。色はサイト側で colormap を当てて付けているので、ここでも同じ処理をする。"""
import io, math, datetime, concurrent.futures as _cf
from PIL import Image, ImageChops, ImageDraw

import metair_all_mail_v2 as M     # panahon のセッション、地図（Esri）とタイル範囲を共用

SUBLAYERS   = ("mosaic-reflectivity", "hybrid-reflectivity")
DEF_BOUNDS  = (115.4154914129329, 3.8016540706290445, 129.51727937415484, 22.458510294136033)
# colormap が取れなかった時の代替（凡例 5〜65 dBZ と同系統の配色）
DEF_CMAP    = [(5, (160, 160, 160, 0)), (10, (150, 150, 150, 180)), (15, (100, 180, 230, 255)),
               (20, (40, 120, 230, 255)), (25, (30, 200, 60, 255)), (30, (20, 150, 40, 255)),
               (35, (250, 240, 40, 255)), (40, (250, 180, 30, 255)), (45, (250, 110, 20, 255)),
               (50, (230, 30, 30, 255)), (55, (190, 0, 40, 255)), (60, (220, 0, 220, 255)),
               (65, (140, 40, 200, 255))]
R_EARTH = 6378137.0

_META = None          # 時系列のメタ情報（1回だけ取る）
_SRC  = {}            # t(unix) -> 着色済みRGBA（MNL と PH で共有）


def _mx(lon):
    return R_EARTH * math.radians(lon)


def _my(lat):
    return R_EARTH * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def _meta():
    """時系列・範囲・配色を取得。取れなければ None"""
    global _META
    if _META is not None:
        return _META or None
    _META = {}
    sess = M._panahon_session()
    tok = getattr(sess, "nimbus_token", None)
    if not tok:
        print("    PAGASA: トークンが取得できません")
        return None
    for sub in SUBLAYERS:
        try:
            r = sess.get(M.PANAHON_BASE + "/api/v1/radar/timeline",
                         params={"token": tok, "sublayer": sub},
                         headers={"X-Requested-With": "XMLHttpRequest"}, timeout=40)
            if "json" not in (r.headers.get("Content-Type") or ""):
                print("    PAGASA 時系列 応答異常:", r.status_code, sub)
                continue
            d = (r.json() or {}).get("data") or {}
            tl = d.get("timeline") or []
            if d.get("no_data") or not tl:
                print("    PAGASA: 配信なし（%s）" % sub)
                continue
            b = d.get("bounds")
            sizes = [int(x) for x in (d.get("image_sizes") or []) if str(x).isdigit()]
            _META = {"sub": sub, "tok": tok, "times": [int(e["observed_at_unix"]) for e in tl
                                                        if e.get("observed_at_unix")],
                     "bounds": tuple(float(x) for x in b) if isinstance(b, list) and len(b) == 4
                               else DEF_BOUNDS,
                     "scale": d.get("scale") or {}, "cmap": d.get("colormap") or [],
                     "ver": d.get("tile_version") or 1,
                     "size": 2048 if (not sizes or 2048 in sizes) else max(sizes)}
            print("    PAGASA: %s %d コマ" % (sub, len(_META["times"])))
            return _META
        except Exception as ex:
            print("    PAGASA 時系列エラー:", str(ex)[:90])
    return None


def _stops(meta):
    """[(値, (r,g,b,a)), ...] を値の昇順で"""
    out = []
    for e in meta.get("cmap") or []:
        try:
            v, c = e[0], e[1]
            v = float(v[0] if isinstance(v, (list, tuple)) else v)
            c = tuple(int(x) for x in c[:3]) + (int(c[3]) if len(c) > 3 else 255,)
            out.append((v, c))
        except Exception:
            continue
    out.sort(key=lambda x: x[0])
    if not out:
        return DEF_CMAP
    if out[0][0] > 0:                 # サイトと同じく 0 に透明の始点を置く
        out.insert(0, (0.0, out[0][1][:3] + (0,)))
    return out


def _lut(meta):
    """赤チャンネル(0-255) → RGBA の対応表"""
    sc = meta.get("scale") or {}
    mx = float(sc.get("max") or 0) or None
    sq = bool(sc.get("sqrt"))
    st = _stops(meta)
    lut = []
    for i in range(256):
        f = i / 255.0
        v = (f * f if sq else f) * mx if mx else f
        if v <= st[0][0]:
            c = st[0][1] if v == st[0][0] else st[0][1][:3] + (0,)
        elif v >= st[-1][0]:
            c = st[-1][1]
        else:
            for (v0, c0), (v1, c1) in zip(st, st[1:]):
                if v0 <= v <= v1:
                    k = (v - v0) / (v1 - v0) if v1 > v0 else 0
                    c = tuple(int(round(a + (b - a) * k)) for a, b in zip(c0, c1))
                    break
        lut.append(c)
    return lut


def _source(t):
    """時刻 t の画像を取得・着色。エコーが無ければ (None, False)"""
    if t in _SRC:
        return _SRC[t]
    meta = _meta()
    res = (None, False)
    try:
        sc = meta.get("scale") or {}
        r = M._panahon_session().get(
            M.PANAHON_BASE + "/api/v1/radar-data-image",
            params={"token": meta["tok"], "sublayer": meta["sub"], "t": t,
                    "mode": sc.get("mode") or "dbz", "size": meta["size"], "v": meta["ver"]},
            timeout=60)
        if r.status_code == 200 and r.content[:4] == b"\x89PNG":
            im = Image.open(io.BytesIO(r.content)).convert("RGBA")
            red, alpha = im.getchannel("R"), im.getchannel("A")
            lut = _lut(meta)
            ch = [red.point([c[k] for c in lut]) for k in range(4)]
            ch[3] = ImageChops.multiply(ch[3], alpha)       # 有効域の外は透明
            col = Image.merge("RGBA", ch)
            res = (col, ch[3].getbbox() is not None)
        else:
            print("    PAGASA画像: HTTP", r.status_code)
    except Exception as ex:
        print("    PAGASA画像エラー:", str(ex)[:90])
    _SRC[t] = res
    return res


def _warp(src, region):
    """着色済み画像を地図（Webメルカトルのタイル範囲）に合わせて切り出す"""
    meta = _meta()
    w, s, e, n = meta["bounds"]
    X0, X1, Yt = _mx(min(w, e)), _mx(max(w, e)), _my(max(s, n))
    u = (X1 - X0) / float(src.size[0])                       # 1px あたりのメートル
    z, x0, x1, y0, y1 = M._rv_geom(region)
    T = 2 * math.pi * R_EARTH / (2 ** z)
    d = T / 256.0
    Dx, Dy = -math.pi * R_EARTH + x0 * T, math.pi * R_EARTH - y0 * T
    size = ((x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256)
    a = d / u
    return src.transform(size, Image.AFFINE,
                         (a, 0, (Dx - X0) / u, 0, a, (Yt - Dy) / u),
                         resample=Image.BILINEAR, fillcolor=(0, 0, 0, 0))


def _caption(cv, ts_label):
    dr = ImageDraw.Draw(cv)
    h = cv.size[1]
    dr.rectangle([4, h - 20, 360, h - 2], fill=(255, 255, 255, 220))
    dr.text((8, h - 16), "PAGASA radar mosaic  %s  / (C) Esri" % ts_label, fill=(60, 60, 60, 255))


def collect_series(s, save):
    """radar_collect から呼ぶ。([{file, ts}], 表示名) を返す"""
    import gsmap as G
    key  = s.get("key")
    view = str(s.get("code") or "MNL")
    n    = int(s.get("frames", 12))
    meta = _meta()
    if meta and meta["times"]:
        times = sorted(meta["times"])[-n:][::-1]               # 新しい順
        with _cf.ThreadPoolExecutor(max_workers=4) as ex:
            srcs = list(ex.map(_source, times))
        if any(has for _, has in srcs):
            base = M._rv_basemap(view)
            frames = []
            for t, (col, has) in zip(times, srcs):
                if col is None:
                    continue
                dt = datetime.datetime.utcfromtimestamp(t)
                cv = base.copy()
                ov = _warp(col, view)
                cv.paste(ov, (0, 0), ov)
                _caption(cv, dt.strftime("%H%MZ"))
                ts = dt.strftime("%Y%m%d%H%M00")
                fn = save(cv.convert("RGB"), "%s_%s.jpg" % (key, ts))
                if fn:
                    frames.append({"file": fn, "ts": ts})
            print("  %-12s PAGASA %d/%d 枚" % (key, len(frames), len(times)))
            if frames:
                return frames, s.get("label_radar") or s.get("label", "")
        else:
            print("  %-12s PAGASA: エコーなし → 衛星推定に切替" % key)
    gs = dict(s, step=s.get("gsm_step", 30), frames=s.get("gsm_frames", 12))
    return G.collect_series(gs, save), s.get("label_gsm") or s.get("label", "")
