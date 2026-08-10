#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NIMBUS OFFLINE 画像コレクタ
  offline_config.json を読み、静止画像と連続再生用フレームを out/ に集めて
  manifest.json を書き出す。out/ は孤立ブランチ offline-cache に強制上書きされる。
"""
import os, io, json, datetime, concurrent.futures as _cf
import requests
from PIL import Image

import metair_all_mail_v2 as M   # 既存の取得ロジックを再利用

OUT = "out"
JPEG_Q = 80
MAXW   = 1600          # 長辺の上限（オフライン用に縮小）

def save(im, name):
    """RGB化・縮小してJPEGで保存し、ファイル名を返す"""
    if im is None:
        return None
    try:
        if im.mode != "RGB":
            im = im.convert("RGB")
        w, h = im.size
        if max(w, h) > MAXW:
            r = MAXW / float(max(w, h))
            im = im.resize((int(w * r), int(h * r)), Image.LANCZOS)
        path = os.path.join(OUT, name)
        im.save(path, "JPEG", quality=JPEG_Q, optimize=True)
        return name
    except Exception as e:
        print("    保存失敗", name, e)
        return None

def get_bytes(url, headers=None, timeout=25):
    try:
        r = requests.get(url, headers=headers or M.METAIR_HEADERS, timeout=timeout)
        if r.status_code == 200 and len(r.content) > 1500:
            return r.content
    except Exception:
        pass
    return None

# ── 連続再生シリーズ ──────────────────────────────────────────────
def frames_kumo(step, n):
    base = datetime.datetime.utcnow()
    base = base.replace(minute=(base.minute // step) * step, second=0, microsecond=0)
    out = []
    for i in range(n):
        dt = base - datetime.timedelta(minutes=step * i)
        ts = dt.strftime("%Y%m%d%H%M00")
        out.append((ts, "https://www3.metair.go.jp/pict/satellite/hf/alt/ENJP64_RJTD_" + ts + ".jpg", None))
    return out

def frames_echotop(step, n):
    base = datetime.datetime.utcnow()
    base = base.replace(minute=(base.minute // step) * step, second=0, microsecond=0)
    out = []
    for i in range(n):
        dt = base - datetime.timedelta(minutes=step * i)
        ts = dt.strftime("%Y%m%d%H%M00")
        out.append((ts, "https://www3.metair.go.jp/pict/radar/rectp99/RECTP99_RJTD_" + ts + ".png", None))
    return out

def frames_cwa(code, step, n):
    stem = "CV1_TW_1000" if str(code) == "TW" else "CV1_1000"
    base = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    base = base.replace(minute=(base.minute // step) * step, second=0, microsecond=0)
    out = []
    for i in range(n):
        dt = base - datetime.timedelta(minutes=step * i)
        ts = dt.strftime("%Y%m%d%H%M")
        utc = (dt - datetime.timedelta(hours=8)).strftime("%Y%m%d%H%M00")
        out.append((utc, "https://www.cwa.gov.tw/Data/radar/" + stem + "_" + ts + ".png", M.CWA_HDR))
    return out

def frames_hko(code, step, n):
    d, pfx = M.HKO_RADAR[str(code)]
    base = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    base = base.replace(minute=(base.minute // step) * step, second=0, microsecond=0)
    out = []
    for i in range(n):
        dt = base - datetime.timedelta(minutes=step * i)
        ts = dt.strftime("%Y%m%d%H%M")
        utc = (dt - datetime.timedelta(hours=8)).strftime("%Y%m%d%H%M00")
        out.append((utc, "https://www.hko.gov.hk/wxinfo/radars/" + d + "/" + pfx + "_" + ts + ".jpg", M.HKO_HDR))
    return out

def frames_jma(prefix, code, step, n, base_ts):
    """WANLC/WANLF は30分グリッド。base_ts から遡る。"""
    if not base_ts:
        return []
    base = datetime.datetime.strptime(str(base_ts)[:12], "%Y%m%d%H%M")
    out = []
    for i in range(n):
        dt = base - datetime.timedelta(minutes=step * i)
        b  = dt.strftime("%Y%m%d%H%M")
        out.append((b + "00", M.JMA_BASE + prefix + code + "_RJTD_" + b + "00.PNG", None))
    return out

def frames_akuten(code, step, n, base_ts):
    """悪天予想図は3時間グリッド。"""
    if not base_ts:
        return []
    base = datetime.datetime.strptime(str(base_ts)[:12], "%Y%m%d%H%M")
    out = []
    for i in range(n):
        dt = base - datetime.timedelta(minutes=step * i)
        b  = dt.strftime("%Y%m%d%H%M")
        out.append((b + "00",
                    M.METAIR_BASE + "/pict/akuten/" + code + "/" + code + "03_RJTD_" + b + "00.png",
                    None))
    return out

def collect_series(s, jma_ts=None, akuten_ts=None):
    """1シリーズ分のフレームを集めて [{file, ts}] を返す（新しい順）"""
    kind = s.get("kind")
    key  = s.get("key")
    step = int(s.get("step", 10))
    n    = int(s.get("frames", 12))
    view = None
    if kind == "kumo":     specs = frames_kumo(step, n)
    elif kind == "echotop":specs = frames_echotop(step, n)
    elif kind == "cwa":    specs = frames_cwa(s.get("code"), step, n)
    elif kind == "hko":    specs = frames_hko(s.get("code"), step, n)
    elif kind == "jma":    specs = frames_jma(s.get("prefix"), s.get("code"), step, n, jma_ts)
    elif kind == "akuten": specs = frames_akuten(s.get("code"), step, n, akuten_ts)
    elif kind == "pagasa":
        fr = M._pagasa_frames()
        view = M.PAGASA_VIEWS.get(str(s.get("code")))
        specs = [(dt.strftime("%Y%m%d%H%M00"), u, None) for dt, u in reversed(fr)]
    else:
        return []

    def one(idx_spec):
        idx, (ts, url, hdr) = idx_spec
        try:
            if kind == "pagasa":
                im = M._pagasa_compose(url, view)
            else:
                b = get_bytes(url, hdr)
                im = Image.open(io.BytesIO(b)) if b else None
            if im is None:
                return None
            fn = save(im, "%s_%02d.jpg" % (key, idx))
            return {"file": fn, "ts": ts} if fn else None
        except Exception:
            return None

    res = [None] * len(specs)
    with _cf.ThreadPoolExecutor(max_workers=8) as ex:
        for i, r in zip(range(len(specs)), ex.map(one, list(enumerate(specs)))):
            res[i] = r
    frames = [r for r in res if r]
    print("  %-12s %d/%d 枚" % (key, len(frames), len(specs)))
    return frames

# ── 静止画像 ────────────────────────────────────────────────────
def collect_static(cat, jma_ts, akuten_ts):
    items = []
    for i, it in enumerate(cat.get("items", [])):
        slot = {"type": it["type"], "code": it["code"], "label": it.get("label", ""), "overlay": False}
        try:
            im, label = M.fetch_slot_image(slot, jma_ts, akuten_ts)
        except Exception as e:
            im, label = None, it.get("label", "")
            print("    取得例外", it.get("label"), e)
        fn = save(im, "%s_%02d.jpg" % (cat["id"], i))
        print("    [%s] %s" % ("OK" if fn else "NG", it.get("label", "")))
        if fn:
            items.append({"file": fn, "label": it.get("label", ""), "caption": label or ""})
    return items

def main():
    os.makedirs(OUT, exist_ok=True)
    conf = json.load(open("offline_config.json", encoding="utf-8"))
    cats = conf.get("categories", [])

    kinds = set()
    for c in cats:
        for s in c.get("series", []):
            kinds.add(s.get("kind"))
    need_jma    = ("jma" in kinds) or any(it.get("type", "").startswith("jma_")
                     for c in cats for it in c.get("items", []))
    need_akuten = ("akuten" in kinds) or any(it.get("type") == "metair_fb_akuten"
                     for c in cats for it in c.get("items", []))
    jma_ts = M.find_jma_timestamp() if need_jma else None
    akuten_ts = M.get_akuten_latest_ts() if need_akuten else None

    manifest = {"generated_utc": datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"), "categories": []}
    total = 0
    for cat in cats:
        print("\n=== %s ===" % cat.get("label"))
        entry = {"id": cat["id"], "label": cat.get("label", ""), "mode": cat.get("mode", "static")}
        if cat.get("mode") == "series":
            entry["series"] = []
            for s in cat.get("series", []):
                fr = collect_series(s, jma_ts, akuten_ts)
                total += len(fr)
                entry["series"].append({"key": s["key"], "label": s.get("label", ""), "frames": fr})
        else:
            entry["items"] = collect_static(cat, jma_ts, akuten_ts)
            total += len(entry["items"])
        manifest["categories"].append(entry)

    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    size = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print("\n=== 収集完了: %d枚 / %.1f MB ===" % (total, size / 1024 / 1024))

if __name__ == "__main__":
    main()
