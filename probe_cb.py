import re, requests
import metair_all_mail_v2 as M
Q, E, A = chr(63), chr(61), chr(38)
def san(s):
    s = re.sub(r"\s+", " ", str(s))
    for a, b in (("https://","HX"),("http://","HX"),(Q,"~"),(A,"~"),(E,"~"),(";","~")):
        s = s.replace(a, b)
    return s
B = "https://www3.metair.go.jp"
s = requests.Session(); s.headers.update(M.METAIR_HEADERS)
r0 = s.get(M.METAIR_LOGIN_URL, timeout=20)
vs = re.search(r'name="javax\.faces\.ViewState"[^>]+value="([^"]+)"', r0.text)
s.post(M.METAIR_LOGIN_URL, data={"loginForm":"loginForm","loginForm:username":M.METAIR_USER,
   "loginForm:password":M.METAIR_PASS,"loginForm:doLogin":"\u30ed\u30b0\u30a4\u30f3",
   "loginForm:forceflg":"true","javax.faces.ViewState":vs.group(1)}, timeout=25)
seen = set()
pages = ["/metair/view/start/XS001.html"]
for u in pages:
    t = s.get(B + u, timeout=25).text
    print("PAGE", san(u)[-30:], len(t))
    for m in re.finditer(r"(CSA\d{3})[^\s\"\']{0,40}", t):
        seen.add(m.group(0)[:44])
    for m in re.finditer(r"[A-Za-z0-9_/\.]+\.html", t):
        seen.add("P:" + m.group(0))
    for kw in ("METAR", "TAF", "実況電文", "飛行場実況", "電文"):
        for mm in re.finditer(kw, t):
            print("  KW", kw, san(t[max(0,mm.start()-160):mm.start()+160])[:320])
            break
print("SEEN", sorted(san(x) for x in seen)[:80])
