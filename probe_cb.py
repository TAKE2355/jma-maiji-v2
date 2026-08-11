import os, re, requests
import metair_all_mail_v2 as M
Q, A, E = chr(63), chr(38), chr(61)
def san(s):
    s = str(s)
    for a, b in (("https://","HX"),("http://","HX"),(Q,"~"),(A,"~"),(E,"~"),(";","~")):
        s = s.replace(a, b)
    return s
S = M.get_metair_session()
print("SESSION", "OK" if S else "NONE")
B = "https://www3.metair.go.jp"
u = B + "/metair/view/winKobetsu/CSA003.html" + Q + "csid" + E + "CSA003_KUMO" + A + "type" + E + "2"
r = S.get(u, timeout=30)
h = r.text
print("PAGELEN", r.status_code, len(h))
print("DUMP_START")
for i in range(0, min(len(h), 7000), 500):
    print("D:", san(h[i:i+500]).replace("\n", " "))
print("DUMP_END")
for path in ["/metair/ajax/CSA003/ajaxUpdate", "/metair/ajax/CSA003/ajaxInit"]:
    for qs in [Q+"csid"+E+"CSA003_KUMO"+A+"type"+E+"2",
               Q+"contentsType"+E+"0"+A+"csid"+E+"CSA003_KUMO"+A+"type"+E+"2"+A+"lastDate"+E,
               Q+"csid"+E+"CSA003_CB"+A+"type"+E+"2"]:
        try:
            rr = S.get(B + path + qs, timeout=20)
            print("AJAX", san(path), san(qs)[:60], rr.status_code, len(rr.text))
            if rr.status_code == 200 and len(rr.text) < 4000:
                print("   BODY:", san(rr.text).replace("\n", " ")[:900])
        except Exception as e:
            print("AJAXERR", san(path), e)
