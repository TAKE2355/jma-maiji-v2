import re, requests
import metair_all_mail_v2 as M
Q, A, E = chr(63), chr(38), chr(61)
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
for u in [B + "/metair/view/winKobetsu/CSA003.html" + Q + "csid" + E + "CSA003_KUMO" + A + "type" + E + "2",
          B + "/metair/ajax/CSA003/ajaxInit" + Q + "did1" + E + "CSA003" + A + "did2" + E + "CSA003_KUMO"]:
    try:
        t = s.get(u, timeout=25).text
        print("SRC", san(u)[-40:], len(t))
        for m in re.finditer(r"<option[^>]*>[^<]*</option>", t):
            print("  OPT:", san(m.group(0))[:140])
        for w in ["積乱雲", "雲頂", "可視", "赤外", "水蒸気"]:
            for m in re.finditer(w, t):
                print("  W:", w, san(t[max(0,m.start()-120):m.start()+120])[:240])
                break
    except Exception as e:
        print("ERR", san(u)[-40:], e)
