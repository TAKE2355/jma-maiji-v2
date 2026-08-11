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
dump("CC", s.get(B + "/metair/js/common/CSAcommon.js", timeout=20).text, 2400)
pg = s.get(B + "/metair/view/winKobetsu/CSA003.html" + Q + "csid" + E + "CSA003_KUMO" + A + "type" + E + "2", timeout=25).text
for m in re.finditer(r"dataId[12]", pg):
    print("PGID:", san(pg[max(0,m.start()-160):m.start()+220]))
for m in re.finditer(r"<input[^>]*type=\"hidden\"[^>]*>", pg):
    print("HID:", san(m.group(0))[:200])
combos = [("CSA003","CSA003","CSA003_KUMO"),("CSA003","CSA003_KUMO","2"),
          ("CSA003_KUMO","CSA003_KUMO","2"),("CSA003","CSA003_KUMO","1"),("CSA003","KUMO","2")]
for path, d1, d2 in combos:
    u = B + "/metair/ajax/" + path + "/ajaxUpdate" + Q + "did1" + E + d1 + A + "did2" + E + d2 + A + "lastDate" + E
    try:
        rr = s.get(u, timeout=20)
        print("AJ", path, d1, d2, rr.status_code, len(rr.text))
        if rr.status_code == 200:
            print("   B:", san(rr.text)[:900])
    except Exception as e:
        print("AJERR", path, d1, d2, e)
