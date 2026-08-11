import re, requests
import metair_all_mail_v2 as M
Q, A, E = chr(63), chr(38), chr(61)
def san(s):
    s = str(s)
    for a, b in (("https://","HX"),("http://","HX"),(Q,"~"),(A,"~"),(E,"~"),(";","~")):
        s = s.replace(a, b)
    return s
B = "https://www3.metair.go.jp"
s = requests.Session(); s.headers.update(M.METAIR_HEADERS)
r0 = s.get(M.METAIR_LOGIN_URL, timeout=20)
vs = re.search(r'name="javax\.faces\.ViewState"[^>]+value="([^"]+)"', r0.text)
data = {"loginForm":"loginForm","loginForm:username":M.METAIR_USER,
        "loginForm:password":M.METAIR_PASS,"loginForm:doLogin":"\u30ed\u30b0\u30a4\u30f3",
        "loginForm:forceflg":"true","javax.faces.ViewState":vs.group(1)}
s.post(M.METAIR_LOGIN_URL, data=data, timeout=25)
for j in ["/metair/js/CSA003.js", "/metair/js/common/CSAcommon.js", "/metair/js/common/baseImage.js", "/metair/js/kobetsuCommon.js", "/metair/js/singleImageFunc.js"]:
    try:
        r = s.get(B + j, timeout=20)
        t = r.text
        print("JS", san(j), r.status_code, len(t))
        if r.status_code != 200: continue
        for pat, tag in [(r"/pict/[^\"\'\s]*", "PICT"), (r"ajax[A-Za-z0-9_]*", "AJAX"), (r"csid[^\"\'\s,)]*", "CSID"), (r"[A-Z]{4}[0-9]{2}", "CODE")]:
            v = sorted(set(re.findall(pat, t)))[:40]
            if v: print("   " + tag + ":", [san(x) for x in v])
        for m in re.finditer(r"(url|src|path|dir)\s*[:=]\s*[\"\'][^\"\']{4,120}[\"\']", t):
            print("   U:", san(m.group(0))[:150])
    except Exception as e:
        print("JSERR", san(j), e)
