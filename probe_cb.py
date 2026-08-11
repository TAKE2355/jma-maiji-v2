import requests, re, json
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
       "Referer": "https://www.jma.go.jp/bosai/nowc/"}
B = "https://www.jma.go.jp/bosai/jmatile/data"
Q, E = chr(63), chr(61)
def san(s):
    s = re.sub(r"\s+", " ", str(s))
    for a, b in (("https://","HX"),("http://","HX"),(Q,"~"),(chr(38),"~"),(E,"~"),(";","~")):
        s = s.replace(a, b)
    return s
n3 = requests.get(B + "/nowc/targetTimes_N3.json", headers=HDR, timeout=20).json()
lid = [e for e in n3 if "liden" in (e.get("elements") or [])]
print("LIDEN ENTRIES", len(lid), [e["validtime"] for e in lid[:6]])
for e in lid[:4]:
    u = B + "/nowc/" + e["basetime"] + "/none/" + e["validtime"] + "/surf/liden/data.geojson" + Q + "id" + E + "liden"
    try:
        r = requests.get(u, headers=HDR, timeout=20)
        print("GJ", e["validtime"], r.status_code, len(r.text))
        if r.status_code == 200:
            j = r.json()
            fs = j.get("features") or []
            print("   feats", len(fs), san(json.dumps(fs[0], ensure_ascii=False))[:300] if fs else "")
    except Exception as ex:
        print("GJERR", e["validtime"], ex)
th = [e for e in n3 if e["validtime"] <= e["basetime"] and "thns" in (e.get("elements") or [])]
print("THNS OBS", len(th), [e["validtime"] for e in th[:5]], [e["validtime"] for e in th[-2:]])
