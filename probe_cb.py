import re, requests
import metair_all_mail_v2 as M
Q, A, E = chr(63), chr(38), chr(61)
def san(s):
    s = re.sub(r"\s+", " ", str(s))
    for a, b in (("https://","HX"),("http://","HX"),(Q,"~"),(A,"~"),(E,"~"),(";","~")):
        s = s.replace(a, b)
    return s
for area in (0, 1, 2):
    for t in range(4):
        u = "https://www.imocwx.com/guid.php" + Q + "Type" + E + "3" + A + "Area" + E + str(area) + A + "Time" + E + str(t)
        try:
            r = requests.get(u, headers=M.IMOC_HDR, timeout=20)
            h = r.text
            m = re.search(r'<img src="(guid/[^"]+)"', h)
            per = re.findall(r'<li class="active">([^<]*)</li>', h)
            areas = re.findall(r'Area' + E + r'(\d)[^>]*>([^<]{1,12})<', h)
            print("T", area, t, r.status_code, san(m.group(1)) if m else "NOIMG", "|", [san(p.strip()) for p in per], "|", [(a, san(b)) for a, b in areas][:8])
        except Exception as e:
            print("ERR", area, t, e)
