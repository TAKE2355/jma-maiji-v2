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
for u in ["/metair/view/header/header.html", "/metair/view/menu/menu.html",
          "/metair/view/start/XS002.html", "/metair/view/infoShow/nowLoading.html"]:
    try:
        t = s.get(B + u, timeout=20)
        ti = re.search(r"<title>([^<]*)</title>", t.text)
        print("PG", san(u)[-34:], t.status_code, len(t.text), san(ti.group(1)) if ti else "")
        for m in re.finditer(r"(CSA\d{3}|CSB\d{3}|XS\d{3})", t.text):
            pass
        ids = sorted(set(re.findall(r"(CSA\d{3}|CSB\d{3})", t.text)))
        if ids: print("   IDS", ids[:40])
    except Exception as e:
        print("PGERR", san(u)[-30:], e)
for n in range(1, 31):
    u = B + "/metair/view/winKobetsu/CSA%03d.html" % n
    try:
        r = s.get(u, timeout=15)
        ti = re.search(r"<title>([^<]*)</title>", r.text)
        t2 = san(ti.group(1)) if ti else ""
        if r.status_code == 200 and t2 and "MetAir" not in t2:
            print("KOB CSA%03d" % n, r.status_code, len(r.text), t2)
    except Exception as e:
        print("KOBERR", n, e)
