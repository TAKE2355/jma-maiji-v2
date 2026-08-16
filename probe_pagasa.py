import socket, requests, time, json
import metair_all_mail_v2 as M
def san(s):
    s=str(s)
    import re
    s=re.sub(r"https?://\S+","<u>",s)
    return re.sub(r"[?&=;]",".",s)[:400]
hosts=["api.meteopilipinas.gov.ph","meteopilipinas.gov.ph","www.pagasa.dost.gov.ph"]
for h in hosts:
    try:
        print("DNS", h, "->", socket.gethostbyname(h))
    except Exception as e:
        print("DNS", h, "NG", san(e))
try:
    fr=M._pagasa_frames()
    print("frames:", len(fr))
    if fr: print("newest:", fr[-1][0], san(fr[-1][1]))
except Exception as e:
    print("frames NG", san(e))