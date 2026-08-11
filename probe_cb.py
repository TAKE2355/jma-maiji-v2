import os, re, sys, datetime, requests
import metair_all_mail_v2 as M

def san(s):
    s = str(s)
    for a, b in (("https://","HX"),("http://","HX"),("?","~"),("&","~"),("=","~"),(";","~")):
        s = s.replace(a, b)
    return s

H = M.METAIR_HEADERS
try:
    S = M.get_metair_session()
except Exception as e:
    S = None
    print("SESSERR", e)
get = (S.get if S else requests.get)

PAGES = [
    "https://www3.metair.go.jp/metair/view/winKobetsu/CSA003.html" + chr(63) + "csid" + chr(61) + "CSA003_KUMO" + chr(38) + "type" + chr(61) + "2",
    "https://www3.metair.go.jp/metair/view/start/XS001.html",
]
for u in PAGES:
    try:
        r = get(u, headers=H, timeout=30)
        h = r.text
        print("PAGE", san(u)[-40:], r.status_code, len(h))
        for m in re.finditer("積乱雲", h):
            print("  CB:", san(h[max(0,m.start()-250):m.start()+250]).replace("\n"," ")[:460])
        print("  PICT:", sorted(set(san(x) for x in re.findall(r"/pict/[A-Za-z0-9_/\-]*", h)))[:60])
        print("  CSID:", sorted(set(re.findall(r"CSA[0-9]{3}_[A-Z0-9]+", h)))[:60])
        print("  ENJP:", sorted(set(re.findall(r"[A-Z]{4}[0-9]{2}_RJTD", h)))[:60])
    except Exception as e:
        print("PAGEERR", san(u)[-40:], e)

# 候補ディレクトリ／プレフィックスの総当たり
now = datetime.datetime.utcnow()
DIRS = ["alt","cb","cba","cbarea","rdca","cbtop","conv","cumulonimbus","sekiran"]
PFX  = ["ENJP60","ENJP61","ENJP62","ENJP63","ENJP64","ENJP65","ENJP66","ENJP67","ENJP68"]
found = []
for d in DIRS:
    for p in PFX:
        hit = False
        for back in range(0, 8):
            t = now - datetime.timedelta(minutes=5*back)
            t = t.replace(minute=(t.minute//5)*5, second=0, microsecond=0)
            u = "https://www3.metair.go.jp/pict/satellite/hf/%s/%s_RJTD_%s00.jpg" % (d, p, t.strftime("%Y%m%d%H%M"))
            try:
                rr = requests.head(u, headers=H, timeout=6)
                if rr.status_code == 200:
                    found.append("%s / %s / %s" % (d, p, t.strftime("%Y%m%d%H%M")))
                    hit = True
                    break
            except Exception:
                pass
        if hit:
            print("HIT", d, p)
print("FOUND", found)
