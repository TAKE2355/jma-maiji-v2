import re, requests
import metair_all_mail_v2 as M
Q, E, A = chr(63), chr(61), chr(38)
def san(s):
    s = re.sub(r"\s+", " ", str(s))
    for a, b in (("https://","HX"),("http://","HX"),(Q,"~"),(A,"~"),(E,"~"),(";","~")):
        s = s.replace(a, b)
    return s
HDR={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
print("=== D-ATIS clowd ===")
for i in ["RJTT","RJAA","RJBB","KJFK","KLAX"]:
    try:
        r=requests.get("https://datis.clowd.io/api/"+i, timeout=20, headers=HDR)
        print("  DATIS", i, r.status_code, san(r.text)[:160])
    except Exception as e:
        print("  DATISERR", i, e)
print("=== MetAir ===")
s=requests.Session(); s.headers.update(M.METAIR_HEADERS)
r0=s.get(M.METAIR_LOGIN_URL, timeout=20)
vs=re.search(r'name="javax\.faces\.ViewState"[^>]+value="([^"]+)"', r0.text)
s.post(M.METAIR_LOGIN_URL, data={"loginForm":"loginForm","loginForm:username":M.METAIR_USER,
  "loginForm:password":M.METAIR_PASS,"loginForm:doLogin":"\u30ed\u30b0\u30a4\u30f3",
  "loginForm:forceflg":"true","javax.faces.ViewState":vs.group(1)}, timeout=25)
B="https://www3.metair.go.jp"
for n in range(1, 31):
    u = B + "/metair/view/winKobetsu/CSA%03d.html" % n
    try:
        r = s.get(u, timeout=10)
        if r.status_code == 200 and "ATIS" in r.text:
            print("  METAIR-ATIS CSA%03d" % n, len(r.text))
    except Exception:
        pass
print("  METAIR done")
