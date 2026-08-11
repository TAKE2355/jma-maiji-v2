import re, json, requests
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
u = B + "/metair/ajax/CSA003/ajaxUpdate" + Q + "did1" + E + "CSA003" + A + "did2" + E + "CSA003_KUMO" + A + "lastDate" + E
j = s.get(u, timeout=25).json()
ds = j.get("dataSet") or []
print("NSETS", len(ds))
for i, arr in enumerate(ds):
    dirs = sorted(set(re.findall(r"/pict/[a-z/]+/", " ".join(x.get("fname","") for x in arr))))
    pfx  = sorted(set(re.findall(r"([A-Z]{4}[0-9]{2})_RJTD", " ".join(x.get("fname","") for x in arr))))
    print("SET", i, "n=" + str(len(arr)), [san(d) for d in dirs], pfx,
          (arr[0]["date"] if arr else ""), (arr[-1]["date"] if arr else ""))
# 認証なしで取得できるか確認
if ds and ds[0]:
    for k in (0, 1):
        f = ds[0][k]["fname"]
        rr = requests.get(B + f, headers=M.METAIR_HEADERS, timeout=20)
        print("PUB", san(f)[-34:], rr.status_code, len(rr.content))
