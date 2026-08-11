import requests
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
       "Referer": "https://www.jma.go.jp/bosai/nowc/"}
B = "https://www.jma.go.jp/bosai/jmatile/data"
for p in ["/liden/targetTimes.json", "/liden/targetTimes_N1.json",
          "/nowc/targetTimes_N1.json", "/nowc/targetTimes_N3.json"]:
    try:
        r = requests.get(B + p, headers=HDR, timeout=20)
        print("TT", p, r.status_code, len(r.text), r.text[:220].replace("\n", " "))
    except Exception as e:
        print("TTERR", p, e)
n1 = requests.get(B + "/nowc/targetTimes_N1.json", headers=HDR, timeout=20).json()
bt, vt = n1[0]["basetime"], n1[0]["validtime"]
try:
    li = requests.get(B + "/liden/targetTimes.json", headers=HDR, timeout=20).json()
    lbt, lvt = li[0]["basetime"], li[0]["validtime"]
except Exception as e:
    lbt = lvt = None
    print("LIDEN TT NG", e)
print("BT", bt, vt, "LIDEN", lbt, lvt)
cands = []
for el in ("thns", "thns_nd", "liden", "liden_nd", "tons"):
    cands.append((el + "@nowc", B + "/nowc/" + bt + "/none/" + vt + "/surf/" + el + "/{z}/{x}/{y}.png"))
if lbt:
    for el in ("liden", "liden_nd"):
        cands.append((el + "@liden", B + "/liden/" + lbt + "/none/" + lvt + "/surf/" + el + "/{z}/{x}/{y}.png"))
for name, tpl in cands:
    hits = tot = sz = 0
    for x in (54, 55, 56):
        for y in (24, 25):
            try:
                r = requests.get(tpl.format(z=6, x=x, y=y), headers=HDR, timeout=15)
                tot += 1
                if r.status_code == 200 and len(r.content) > 100:
                    hits += 1; sz += len(r.content)
            except Exception:
                pass
    print("TILE", name, hits, "/", tot, "avg", (sz // hits) if hits else 0)
