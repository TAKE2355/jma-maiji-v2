#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""METAR/TAFだけを取得して metar.json に書き出す（軽量・単独実行用）。
   画像は一切取得しないため数十秒で完了する。"""
import json, datetime
import offline_collect as OC

def main():
    conf = json.load(open("offline_config.json", encoding="utf-8"))
    cat = None
    for c in conf.get("categories", []):
        if c.get("mode") == "text":
            cat = c
            break
    if not cat:
        print("テキストカテゴリが見つかりません")
        return
    items = OC.collect_text(cat)
    first = items[0] if items else {}
    groups = first.get("groups") or []
    out = {"generated_utc": datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"),
           "label": first.get("label", ""),
           "groups": groups}
    with open("metar.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    ok = sum(1 for g in groups if g.get("text"))
    print("metar.json 書き出し %d/%d 空港" % (ok, len(groups)))

if __name__ == "__main__":
    main()
