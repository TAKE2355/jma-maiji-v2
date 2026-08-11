import requests, json, time
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
       "Referer": "https://www.jma.go.jp/bosai/nowc/"}
B = "https://www.jma.go.jp/bosai/jmatile/data"
tt = requests.get(B + "/nowc/targetTimes_N1.json", headers=HDR, timeout=20).json()
print("TT", len(tt), tt[0]["basetime"], tt[0]["validtime"], tt[-1]["basetime"])
bt, vt = tt[0]["basetime"], tt[0]["validtime"]
cands = [
  ("mask",       B + "/map/none/none/none/surf/mask/{z}/{x}/{y}.png"),
  ("bordermap",  B + "/map/none/none/none/surf/bordermap/{z}/{x}/{y}.png"),
  ("bordermask", B + "/map/none/none/none/surf/bordermask/{z}/{x}/{y}.png"),
  ("basemap",    B + "/map/none/none/none/surf/basemap/{z}/{x}/{y}.png"),
  ("gsi_pale",   "https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png"),
  ("hrpns",      B + "/nowc/" + bt + "/none/" + vt + "/surf/hrpns/{z}/{x}/{y}.png"),
  ("hrpns_nd",   B + "/nowc/" + bt + "/none/" + vt + "/surf/hrpns_nd/{z}/{x}/{y}.png"),
]
for name, tpl in cands:
    hits = 0; tot = 0; sz = 0
    for x in (54, 55, 56):
        for y in (24, 25):
            u = tpl.format(z=6, x=x, y=y)
            try:
                r = requests.get(u, headers=HDR, timeout=15)
                tot += 1
                if r.status_code == 200 and len(r.content) > 100:
                    hits += 1; sz += len(r.content)
            except Exception as e:
                pass
    print("TILE", name, hits, "/", tot, "avg", (sz // hits) if hits else 0)
