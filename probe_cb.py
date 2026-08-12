import re, requests
Q, E, A = chr(63), chr(61), chr(38)
def san(s):
    s = re.sub(r"\s+", " ", str(s))
    for a, b in (("https://","HX"),("http://","HX"),(Q,"~"),(A,"~"),(E,"~"),(";","~")):
        s = s.replace(a, b)
    return s
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
IDS = ["RJTH", "RJTA", "RJAH", "RJAA"]
print("=== AWC metar ===")
for i in IDS:
    try:
        r = requests.get("https://aviationweather.gov/api/data/metar",
                         params={"ids": i, "format": "raw", "hours": 12}, timeout=25, headers=HDR)
        print(" AWC", i, r.status_code, len(r.text.strip()), san(r.text.strip()[:90]))
    except Exception as e:
        print(" AWCERR", i, e)
print("=== NOAA tgftp ===")
for i in IDS:
    for base in ["https://tgftp.nws.noaa.gov/data/observations/metar/stations/%s.TXT",
                 "https://tgftp.nws.noaa.gov/data/forecasts/taf/stations/%s.TXT"]:
        try:
            r = requests.get(base % i, timeout=20, headers=HDR)
            print(" TG", i, base.split("/")[-2], r.status_code, len(r.text.strip()), san(r.text.strip().replace(chr(10)," ")[:90]))
        except Exception as e:
            print(" TGERR", i, e)
print("=== ogimet ===")
for i in ["RJTH", "RJTA"]:
    try:
        u = ("https://www.ogimet.com/display_metars2.php" + Q + "lang" + E + "en" + A + "lugar" + E + i
             + A + "tipo" + E + "SA" + A + "ord" + E + "REV" + A + "nil" + E + "NO" + A + "fmt" + E + "txt"
             + A + "ano" + E + "2026" + A + "mes" + E + "08" + A + "day" + E + "12" + A + "hora" + E + "00"
             + A + "anof" + E + "2026" + A + "mesf" + E + "08" + A + "dayf" + E + "12" + A + "horaf" + E + "23" + A + "minf" + E + "59" + A + "send" + E + "send")
        r = requests.get(u, timeout=30, headers=HDR)
        body = re.sub(r"<[^>]+>", " ", r.text)
        hit = [l for l in body.split(chr(10)) if i in l][:3]
        print(" OGI", i, r.status_code, len(r.text), [san(x.strip())[:110] for x in hit])
    except Exception as e:
        print(" OGIERR", i, e)
