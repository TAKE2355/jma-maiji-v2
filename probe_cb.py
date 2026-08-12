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
h = s.get(B + "/metair/view/header/header.html", timeout=20).text
t = san(h)
print("HDR_START")
for i in range(0, min(len(t), 5200), 460):
    print("D:", t[i:i+460])
print("HDR_END")
# 電文系画面の探索
for pre in ("CSB", "CSC", "CSD", "CST", "CSE"):
    for n in range(1, 26):
        u = B + "/metair/view/winKobetsu/%s%03d.html" % (pre, n)
        try:
            r = s.get(u, timeout=10)
            ti = re.search(r"<title>([^<]*)</title>", r.text)
            t2 = san(ti.group(1)) if ti else ""
            if r.status_code == 200 and t2 and "MetAir" not in t2:
                print("HIT", pre, n, len(r.text), t2)
        except Exception:
            pass
