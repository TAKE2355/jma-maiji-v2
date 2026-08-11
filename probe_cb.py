import requests, re
import metair_all_mail_v2 as M
def san(s):
    s = str(s)
    for a, b in (("https://","HX"),("http://","HX"),(chr(63),"~"),(chr(38),"~"),(chr(61),"~"),(";","~")):
        s = s.replace(a, b)
    return s
H = M.METAIR_HEADERS
B = "https://www3.metair.go.jp"
for p in ["/pict/", "/pict/satellite/", "/pict/satellite/hf/", "/pict/satellite/hf/alt/"]:
    try:
        r = requests.get(B + p, headers=H, timeout=20)
        print("DIR", san(p), r.status_code, len(r.text))
        if r.status_code == 200:
            hrefs = sorted(set(re.findall(r'href="([^"]+)"', r.text)))
            print("   HREF:", [san(x) for x in hrefs][:120])
            if not hrefs:
                print("   RAW:", san(r.text).replace("\n"," ")[:600])
    except Exception as e:
        print("DIRERR", san(p), e)
