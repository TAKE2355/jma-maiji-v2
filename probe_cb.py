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
pg = s.get(B + "/metair/view/winKobetsu/CSA003.html" + Q + "csid" + E + "CSA003_EISI" + A + "type" + E + "5", timeout=25).text
print("PG", len(pg))
ti = re.search(r"<title>([^<]*)</title>", pg)
print("TITLE", san(ti.group(1)) if ti else "")
for m in re.finditer(r"<option[^>]*>[^<]*</option>", pg):
    print("  OPT:", san(m.group(0))[:160])
j = s.get(B + "/metair/ajax/CSA003/ajaxUpdate" + Q + "did1" + E + "CSA003" + A + "did2" + E + "CSA003_EISI" + A + "lastDate" + E, timeout=25).json()
ds = j.get("dataSet") or []
print("NSETS", len(ds))
for i, arr in enumerate(ds):
    names = " ".join(x.get("fname", "") for x in arr)
    dirs = sorted(set(re.findall(r"/pict/[a-zA-Z0-9_/]+/", names)))
    pfx = sorted(set(re.findall(r"([A-Z0-9]{4,8})_[A-Z]{4}_", names)))
    ext = sorted(set(re.findall(r"\.[a-z]{3}$", " ".join(x.get("fname","")[-4:] for x in arr))))
    print("SET", i, "n=" + str(len(arr)), [san(d) for d in dirs], pfx,
          (arr[0]["date"] if arr else ""), (arr[-1]["date"] if arr else ""),
          san(arr[0]["fname"])[-42:] if arr else "")
if ds and ds[0]:
    f = ds[0][0]["fname"]
    rr = requests.get(B + f, headers=M.METAIR_HEADERS, timeout=20)
    print("PUB", san(f)[-40:], rr.status_code, len(rr.content))
