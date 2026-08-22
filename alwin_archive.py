#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ALWINの画像を時刻付きで保存庫へ積み、3日より古いものを捨てる。
   out/ にある最新のALWIN画像を arch/ へコピーし、索引 alwin_archive.json を書く。"""
import os, json, shutil, datetime, re

OUT  = "out"
ARCH = "arch"
KEEP_DAYS = 3

def main():
    try:
        mf = json.load(open(os.path.join(OUT, "manifest.json"), encoding="utf-8"))
    except Exception as e:
        print("manifestが読めません:", str(e)[:80]); return
    cat = None
    for c in mf.get("categories", []):
        if c.get("id") == "alwin": cat = c
    if not cat:
        print("ALWINがありません"); return
    os.makedirs(ARCH, exist_ok=True)
    added = 0
    for it in cat.get("items", []):
        lab = str(it.get("label") or "")
        src = os.path.join(OUT, str(it.get("file") or ""))
        cap = str(it.get("caption") or "")
        m = re.search(r"(\d{4})/(\d{2})/(\d{2})\s+(\d{2}):(\d{2})Z", cap)
        if not (lab and os.path.exists(src) and m): continue
        ts = m.group(1)+m.group(2)+m.group(3)+m.group(4)+m.group(5)+"00"
        dst = os.path.join(ARCH, lab+"_"+ts+".jpg")
        if not os.path.exists(dst):
            shutil.copyfile(src, dst); added += 1
    # 期限切れを削除
    limit = (datetime.datetime.utcnow()-datetime.timedelta(days=KEEP_DAYS)).strftime("%Y%m%d%H%M%S")
    removed = 0
    frames = {}
    for fn in sorted(os.listdir(ARCH)):
        m = re.match(r"([A-Z]{3})_(\d{14})\.jpg$", fn)
        if not m: continue
        if m.group(2) < limit:
            os.remove(os.path.join(ARCH, fn)); removed += 1; continue
        frames.setdefault(m.group(1), []).append(m.group(2))
    idx = {"generated_utc": datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"),
           "keep_days": KEEP_DAYS, "frames": frames}
    with open(os.path.join(ARCH, "index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False)
    print("ALWIN保存庫: 追加%d 削除%d 空港%d 合計%d枚"
          % (added, removed, len(frames), sum(len(v) for v in frames.values())))

if __name__ == "__main__":
    main()