import requests, re, json
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
       "Referer": "https://www.jma.go.jp/bosai/nowc/"}
B = "https://www.jma.go.jp/bosai/jmatile/data"
def san(s):
    s = re.sub(r"\s+", " ", str(s))
    for a, b in (("https://","HX"),("http://","HX"),(chr(63),"~"),(chr(38),"~"),(chr(61),"~"),(";","~")):
        s = s.replace(a, b)
    return s
for i in range(1, 10):
    try:
        r = requests.get(B + "/nowc/targetTimes_N%d.json" % i, headers=HDR, timeout=15)
        if r.status_code == 200:
            j = r.json()
            print("N%d" % i, len(j), j[0].get("basetime"), j[0].get("validtime"), j[0].get("elements"))
        else:
            print("N%d" % i, r.status_code)
    except Exception as e:
        print("N%d ERR" % i, e)
h = requests.get("https://www.jma.go.jp/bosai/nowc/", headers=HDR, timeout=20).text
srcs = re.findall(r'src="([^"]+\.js[^"]*)"', h)
print("SRC", [san(s) for s in srcs][:12])
for s in srcs:
    u = s if s.startswith("http") else ("https://www.jma.go.jp/bosai/nowc/" + s.lstrip("./"))
    try:
        t = requests.get(u, headers=HDR, timeout=20).text
    except Exception:
        continue
    for m in re.finditer("liden", t):
        print("LD:", san(t[max(0, m.start()-220):m.start()+220])[:420])
        break
