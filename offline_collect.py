#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NIMBUS OFFLINE 画像コレクタ
  offline_config.json を読み、静止画像と連続再生用フレームを out/ に集めて
  manifest.json を書き出す。out/ は孤立ブランチ offline-cache に強制上書きされる。
"""
import os, io, json, time, datetime, concurrent.futures as _cf
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
        # 透過PNG（気象庁の断面図・平面図など）は白地に合成する。
        # そのまま convert("RGB") すると透明部が黒くなり色が反転して見える。
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        elif im.mode != "RGB":
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

def frames_cb(step, n):
    base = datetime.datetime.utcnow()
    base = base.replace(minute=(base.minute // step) * step, second=0, microsecond=0)
    out = []
    for i in range(n):
        dt = base - datetime.timedelta(minutes=step * i)
        ts = dt.strftime("%Y%m%d%H%M00")
        out.append((ts, "https://www3.metair.go.jp/pict/satellite/hf/cov/ENJP61_RJTD_" + ts + ".jpg", None))
    return out

def frames_wv(step, n):
    base = datetime.datetime.utcnow()
    base = base.replace(minute=(base.minute // step) * step, second=0, microsecond=0)
    out = []
    for i in range(n):
        dt = base - datetime.timedelta(minutes=step * i)
        ts = dt.strftime("%Y%m%d%H%M00")
        out.append((ts, "https://www3.metair.go.jp/pict/satellite/ea/ir3_h/ENJP26_RJTD_" + ts + ".jpg", None))
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

def frames_csa019(code, n):
    """CSA019のAJAX一覧(dataSet)から過去n枚を新しい順で返す"""
    try:
        r = requests.get(M.AJAX19.format(code=code), headers=M.METAIR_HEADERS, timeout=20)
        ds = r.json().get("dataSet")
        if isinstance(ds, str):
            ds = json.loads(ds)
        if not ds:
            return []
        out = []
        for e in reversed(ds[-int(n):]):
            fn = e.get("fname", "")
            try:
                ts = fn.split("_RJTD_")[1].replace(".png", "")
            except Exception:
                ts = ""
            out.append((ts, M.METAIR_BASE + fn, None))
        return out
    except Exception as ex:
        print("    CSA019一覧失敗", code, str(ex)[:80])
        return []

def collect_series(s, jma_ts=None, akuten_ts=None):
    """1シリーズ分のフレームを集めて [{file, ts}] を返す（新しい順）"""
    kind = s.get("kind")
    key  = s.get("key")
    step = int(s.get("step", 10))
    n    = int(s.get("frames", 12))
    view = None
    if kind == "kumo":     specs = frames_kumo(step, n)
    elif kind == "cb":     specs = frames_cb(step, n)
    elif kind == "wv":     specs = frames_wv(step, n)
    elif kind == "echotop":specs = frames_echotop(step, n)
    elif kind == "cwa":    specs = frames_cwa(s.get("code"), step, n)
    elif kind == "hko":    specs = frames_hko(s.get("code"), step, n)
    elif kind == "jma":    specs = frames_jma(s.get("prefix"), s.get("code"), step, n, jma_ts)
    elif kind == "akuten": specs = frames_akuten(s.get("code"), step, n, akuten_ts)
    elif kind == "csa019": specs = frames_csa019(s.get("code"), n)
    elif kind == "nowc":
        tt = M.nowc_times()[:n]
        specs = [(e.get("validtime"), e.get("basetime"), None) for e in tt]
        view = str(s.get("code") or "JP")
        M._nowc_basemap(view)          # 地図タイルを先に1回だけ作ってスレッド間で共有
    elif kind == "thnc":
        sp = M.nowc_thunder_specs(n)
        specs = [(vt, (bt, vt2, lbt, lvt), None) for vt, bt, vt2, lbt, lvt in sp]
        M._nowc_basemap()
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
            elif kind == "nowc":
                im, _ts = M.get_nowc_hrpns(url, ts, view or "JP")
            elif kind == "thnc":
                im, _ts = M.get_nowc_thunder(*url)
            else:
                b = get_bytes(url, hdr)
                im = Image.open(io.BytesIO(b)) if b else None
            if im is None:
                return None
            # 時刻をファイル名に含める → 端末側で「持っていないコマだけ」取得できる
            stamp = (ts or ("%014d" % idx))
            fn = save(im, "%s_%s.jpg" % (key, stamp))
            return {"file": fn, "ts": ts} if fn else None
        except Exception:
            return None

    res = [None] * len(specs)
    with _cf.ThreadPoolExecutor(max_workers=16) as ex:
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

def _split_by_station(lines, icaos):
    """AWCのraw出力を空港ごとに振り分ける（TAFの継続行は直前のブロックに属する）"""
    want = set(icaos)
    out, cur = {}, None
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        head = s.split()
        if ln[:1] not in (" ", "\t") and head:
            code = None
            if head[0] in ("METAR", "SPECI", "TAF"):
                for tok in head[1:4]:
                    if tok in want:
                        code = tok
                        break
            elif head[0] in want:
                code = head[0]
            if code:
                cur = code
                out.setdefault(cur, []).append(ln.rstrip())
                continue
        if cur:
            out[cur].append(ln.rstrip())
    return {k: "\n".join(v) for k, v in out.items()}

def collect_text(cat):
    """METAR/TAFをまとめて取得（12空港ずつの一括リクエスト＋欠けた分だけ個別再取得）"""
    items = []
    for it in cat.get("items", []):
        icaos = [s.strip().upper() for s in str(it.get("ids", "")).split(",") if s.strip()]
        hours = it.get("hours", 3)
        wm, wt = it.get("metar", True), it.get("taf", True)
        texts = {}

        def grab(ids):
            for attempt in range(3):
                try:
                    lines = M.fetch_metar_text({"ids": ",".join(ids), "hours": hours,
                                                "metar": wm, "taf": wt})
                except Exception:
                    lines = []
                bad = (not lines) or any("取得失敗" in l or "取得エラー" in l for l in lines)
                if not bad:
                    return _split_by_station(lines, ids)
                time.sleep(1.2 * (attempt + 1))
            return {}

        CH = 12
        for i in range(0, len(icaos), CH):
            chunk = icaos[i:i + CH]
            texts.update(grab(chunk))

        missing = [c for c in icaos if not texts.get(c)]
        for c in missing:
            d = grab([c])
            if d.get(c):
                texts[c] = d[c]

        ok = sum(1 for c in icaos if texts.get(c))
        print("    METAR/TAF %d/%d 空港" % (ok, len(icaos)))
        items.append({"label": it.get("label", ""),
                      "groups": [{"icao": c, "text": texts.get(c, "")} for c in icaos]})
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
    def do_cat(cat):
        _t0 = time.time()
        entry = {"id": cat["id"], "label": cat.get("label", ""), "mode": cat.get("mode", "static")}
        n = 0
        try:
            if cat.get("mode") == "text":
                entry["items"] = collect_text(cat)
                n += len(entry["items"])
            else:
                # items(静止画) と series(連続再生) は同じカテゴリに併存できる
                if cat.get("items"):
                    entry["items"] = collect_static(cat, jma_ts, akuten_ts)
                    n += len(entry["items"])
                if cat.get("series"):
                    entry["series"] = []
                    for s in cat.get("series", []):
                        _s0 = time.time()
                        fr = collect_series(s, jma_ts, akuten_ts)
                        print("    [TIME] %s %.1fs (%d枚)" % (s.get("label"), time.time() - _s0, len(fr)))
                        n += len(fr)
                        entry["series"].append({"key": s["key"], "label": s.get("label", ""), "frames": fr})
        except Exception as ex:
            print("  カテゴリ失敗 %s: %s" % (cat.get("label"), str(ex)[:120]))
        print("=== %s 完了 %.1fs (%d枚) ===" % (cat.get("label"), time.time() - _t0, n))
        return entry, n

    # カテゴリを並行処理（直列だと合計5分かかるため）。
    # 各カテゴリの中でさらに16並列で取得するので、外側は3までに抑える。
    total = 0
    with _cf.ThreadPoolExecutor(max_workers=3) as ex:
        for entry, n in ex.map(do_cat, cats):
            total += n
            manifest["categories"].append(entry)
    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    size = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print("\n=== 収集完了: %d枚 / %.1f MB ===" % (total, size / 1024 / 1024))

if __name__ == "__main__":
    main()
