import re, requests
import metair_all_mail_v2 as M
Q, A, E = chr(63), chr(38), chr(61)
def san(s):
    s = re.sub(r"\s+", " ", str(s))
    for a, b in (("https://","HX"),("http://","HX"),(Q,"~"),(A,"~"),(E,"~"),(";","~")):
        s = s.replace(a, b)
    return s
def dump(tag, t, n=9000):
    t = san(t)
    print(tag + "_START")
    for i in range(0, min(len(t), n), 460):
        print("D:", t[i:i+460])
    print(tag + "_END")
B = "https://www3.metair.go.jp"
s = requests.Session(); s.headers.update(M.METAIR_HEADERS)
r0 = s.get(M.METAIR_LOGIN_URL, timeout=20)
vs = re.search(r'name="javax\.faces\.ViewState"[^>]+value="([^"]+)"', r0.text)
s.post(M.METAIR_LOGIN_URL, data={"loginForm":"loginForm","loginForm:username":M.METAIR_USER,
   "loginForm:password":M.METAIR_PASS,"loginForm:doLogin":"\u30ed\u30b0\u30a4\u30f3",
   "loginForm:forceflg":"true","javax.faces.ViewState":vs.group(1)}, timeout=25)
k = s.get(B + "/metair/js/kobetsuCommon.js", timeout=20).text
i = k.find("/metair/ajax/")
dump("KOB", k[max(0,i-1800):i+1800], 4000)
dump("C3", s.get(B + "/metair/js/CSA003.js", timeout=20).text, 9000)
