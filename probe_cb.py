import os, re, requests
import metair_all_mail_v2 as M
Q, A, E = chr(63), chr(38), chr(61)
def san(s):
    s = str(s)
    for a, b in (("https://","HX"),("http://","HX"),(Q,"~"),(A,"~"),(E,"~"),(";","~")):
        s = s.replace(a, b)
    return s
B = "https://www3.metair.go.jp"
s = requests.Session()
s.headers.update(M.METAIR_HEADERS)
r0 = s.get(M.METAIR_LOGIN_URL, timeout=20)
vs = re.search(r'name="javax\.faces\.ViewState"[^>]+value="([^"]+)"', r0.text)
print("VS", bool(vs))
data = {"loginForm":"loginForm","loginForm:username":M.METAIR_USER,
        "loginForm:password":M.METAIR_PASS,"loginForm:doLogin":"\u30ed\u30b0\u30a4\u30f3",
        "loginForm:forceflg":"true","javax.faces.ViewState":vs.group(1) if vs else ""}
r1 = s.post(M.METAIR_LOGIN_URL, data=data, timeout=25, allow_redirects=True)
print("LOGIN", r1.status_code, san(r1.url)[-46:], len(r1.text))
u = B + "/metair/view/winKobetsu/CSA003.html" + Q + "csid" + E + "CSA003_KUMO" + A + "type" + E + "2"
r = s.get(u, timeout=30)
h = r.text
print("PAGELEN", r.status_code, san(r.url)[-46:], len(h))
print("DUMP_START")
for i in range(0, min(len(h), 9000), 480):
    print("D:", san(h[i:i+480]).replace("\n", " "))
print("DUMP_END")
