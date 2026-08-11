import requests, re
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
       "Referer": "https://www.jma.go.jp/bosai/nowc/"}
B = "https://www.jma.go.jp/bosai/jmatile/data"
def san(s):
    s = re.sub(r"\s+", " ", str(s))
    for a, b in (("https://","HX"),("http://","HX"),(chr(63),"~"),(chr(38),"~"),(chr(61),"~"),(";","~")):
        s = s.replace(a, b)
    return s
n3 = requests.get(B + "/nowc/targetTimes_N3.json", headers=HDR, timeout=20).json()
obs = [e for e in n3 if e["validtime"] <= e["basetime"]]
print("N3 total", len(n3), "obs", len(obs))
for e in n3[:3] + obs[:3]:
    print("  E", e["basetime"], e["validtime"], e["elements"])
if obs:
    bt, vt = obs[0]["basetime"], obs[0]["validtime"]
    for el in ("thns", "thns_nd", "liden", "liden_nd", "trns"):
        hits = tot = sz = 0
        for x in (54, 55, 56):
            for y in (24, 25):
                u = B + "/nowc/" + bt + "/none/" + vt + "/surf/" + el + "/6/%d/%d.png" % (x, y)
                try:
                    r = requests.get(u, headers=HDR, timeout=15)
                    tot += 1
                    if r.status_code == 200 and len(r.content) > 100:
                        hits += 1; sz += len(r.content)
                except Exception:
                    pass
        print("OBS-TILE", el, hits, "/", tot, "avg", (sz // hits) if hits else 0)
js = requests.get("https://www.jma.go.jp/bosai/nowc/../jmatile/js/jmatile.bundle__284fe80563cf414cd78c.js".replace("nowc/../", ""), headers=HDR, timeout=30).text
print("JSLEN", len(js))
for kw in ("thns", "liden", "surf/"):
    ms = [m.start() for m in re.finditer(kw, js)][:3]
    for m in ms:
        print("KW", kw, san(js[max(0, m-260):m+260])[:500])
