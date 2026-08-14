#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""海外レーダー（台湾・香港・マニラ）だけを集める。
   通常収集とは別のブランチ radar-cache へ書き出すため、保存先を out_radar/ に切り替える。"""
import os, json, time, datetime
import offline_collect as OC

OUT = "out_radar"

def main():
    conf = json.load(open("radar_config.json", encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    OC.OUT = OUT                     # save() の保存先を切り替える
    series, total = [], 0
    for s in conf.get("series", []):
        t0 = time.time()
        fr = OC.collect_series(s)
        total += len(fr)
        print("  [TIME] %s %.1fs (%d枚)" % (s.get("label"), time.time() - t0, len(fr)))
        series.append({"key": s["key"], "label": s.get("label", ""), "frames": fr})
    mf = {"generated_utc": datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"),
          "series": series}
    with open(os.path.join(OUT, "radar_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(mf, f, ensure_ascii=False)
    print("海外レーダー 合計 %d枚" % total)

if __name__ == "__main__":
    main()
