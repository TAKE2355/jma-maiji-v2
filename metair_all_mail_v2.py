#!/usr/bin/env python3
"""
Ã¦Â°ÂÃ¨Â±Â¡Ã¦ÂÂÃ¥Â Â±Ã£ÂÂ¡Ã£ÂÂ¼Ã£ÂÂ«Ã©ÂÂÃ¤Â¿Â¡ v2 (Ã£ÂÂÃ£ÂÂ¼Ã£ÂÂ¸Ã¥ÂÂÃ¤Â½ÂÃ£ÂÂ¬Ã£ÂÂ¤Ã£ÂÂ¢Ã£ÂÂ¦Ã£ÂÂÃ¥Â¯Â¾Ã¥Â¿Â)

Ã¤Â»ÂÃ§ÂµÂÃ£ÂÂ¿:
  - config.json Ã£ÂÂ® pages[] Ã£ÂÂ«Ã£ÂÂÃ£ÂÂ¼Ã£ÂÂ¸Ã¥ÂÂÃ¤Â½ÂÃ£ÂÂ§Ã£ÂÂ¬Ã£ÂÂ¤Ã£ÂÂ¢Ã£ÂÂ¦Ã£ÂÂÃ£ÂÂ¨Ã¥Â¤Â©Ã¦Â°ÂÃ¥ÂÂ³Ã£ÂÂ¹Ã£ÂÂ­Ã£ÂÂÃ£ÂÂÃ£ÂÂÃ¥Â®ÂÃ§Â¾Â©
  - Ã¥ÂÂÃ£ÂÂÃ£ÂÂ¼Ã£ÂÂ¸: orientation(portrait/landscape), cols, rows, slots[]
  - slots[] Ã£ÂÂ®Ã¥ÂÂÃ¨Â¦ÂÃ§Â´Â : {"type": ..., "code": ..., "label": ...} or null
  - recipients[] Ã£ÂÂ«Ã¥ÂÂÃ¤Â¿Â¡Ã¨ÂÂÃ£ÂÂÃ¨Â¤ÂÃ¦ÂÂ°Ã§ÂÂ»Ã©ÂÂ² (time_slots Ã£ÂÂ¹Ã£ÂÂ±Ã£ÂÂ¸Ã£ÂÂ¥Ã£ÂÂ¼Ã£ÂÂ«Ã¤Â»ÂÃ£ÂÂ)
  - PDFÃ£ÂÂ¯1Ã¥ÂÂÃ§ÂÂÃ¦ÂÂ Ã¢ÂÂ Ã©ÂÂÃ¤Â¿Â¡Ã¥Â¯Â¾Ã¨Â±Â¡Ã£ÂÂ®Ã¥ÂÂÃ¤Â¿Â¡Ã¨ÂÂÃ¥ÂÂ¨Ã¥ÂÂ¡Ã£ÂÂ«Ã¥ÂÂÃ¥ÂÂ¥Ã©ÂÂÃ¤Â¿Â¡
  - workflow_dispatch Ã£ÂÂ¯Ã¥ÂÂ¨Ã¦ÂÂÃ¥ÂÂ¹Ã¥ÂÂÃ¤Â¿Â¡Ã¨ÂÂÃ£ÂÂ«Ã¥Â¼Â·Ã¥ÂÂ¶Ã©ÂÂÃ¤Â¿Â¡
"""

import os, io, json, smtplib, datetime, sys, requests
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from PIL import Image, ImageDraw, ImageFont
import img2pdf

# Ã¢ÂÂÃ¢ÂÂ Ã§ÂÂ°Ã¥Â¢ÂÃ¥Â¤ÂÃ¦ÂÂ° Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
MAIL_FROM    = os.environ["MAIL_FROM"]
SMTP_HOST    = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT    = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER    = os.environ["SMTP_USER"]
SMTP_PASS    = os.environ["SMTP_PASS"]
GITHUB_EVENT = os.environ.get("GITHUB_EVENT_NAME", "schedule")

# Ã¢ÂÂÃ¢ÂÂ config.json Ã¨ÂªÂ­Ã£ÂÂ¿Ã¨Â¾Â¼Ã£ÂÂ¿ Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
def load_config():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_config()

# Ã¢ÂÂÃ¢ÂÂ Ã£ÂÂ°Ã£ÂÂ­Ã£ÂÂ¼Ã£ÂÂÃ£ÂÂ«Ã¨Â¨Â­Ã¥Â®ÂÃ¯Â¼ÂÃ£ÂÂÃ£ÂÂ¼Ã£ÂÂ¸Ã¥ÂÂ±Ã©ÂÂÃ¯Â¼Â Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
_pdf         = CONFIG["pdf"]
DPI          = _pdf.get("dpi", 150)        # Ã¥Â¾ÂÃ¦ÂÂ¹Ã¤ÂºÂÃ¦ÂÂÃ§ÂÂ¨Ã¯Â¼ÂÃ§ÂÂ´Ã¦ÂÂ¥Ã¤Â½Â¿Ã§ÂÂ¨Ã£ÂÂ¯Ã£ÂÂÃ£ÂÂªÃ£ÂÂÃ¯Â¼Â
PAGE_MARGIN  = _pdf["page_margin"]
HEADER_H     = _pdf["header_h"]
CELL_GAP     = _pdf["cell_gap"]
LABEL_H      = _pdf["label_h"]
JPEG_QUALITY = _pdf.get("jpeg_quality", 90)
MAX_DPI      = _pdf.get("max_dpi", DPI)    # DPIÃ¤Â¸ÂÃ©ÂÂ
MAX_MAIL_MB  = float(_pdf.get("max_mail_mb", 20.0))  # Ã£ÂÂ¡Ã£ÂÂ¼Ã£ÂÂ«Ã£ÂÂµÃ£ÂÂ¤Ã£ÂÂºÃ¤Â¸ÂÃ©ÂÂ(MB)

# Ã¢ÂÂÃ¢ÂÂ Ã£ÂÂªÃ£ÂÂ¼Ã£ÂÂÃ£ÂÂ¼Ã£ÂÂ¬Ã£ÂÂ¤ Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
_ov             = CONFIG["overlay"]
OVERLAY_ENABLED = _ov.get("enabled", True)
OVERLAY_ALPHA   = float(_ov.get("alpha", 0.2))
OVERLAY_CODES   = {"QBSA95","QBCK95","QBRA95","QBQA95","QBFF95","QBUA95","QBIG95","QBAH95"}

# Ã¢ÂÂÃ¢ÂÂ URLÃ¥Â®ÂÃ§Â¾Â© Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
JMA_BASE    = "https://www.data.jma.go.jp/airinfo/data/pict/maiji/"
METAIR_BASE = "https://www3.metair.go.jp"
AJAX19      = METAIR_BASE + "/metair/ajax/CSA019/ajaxUpdate?contentsType=0&dbKey=RJTD,{code}&lastDate="
AJAX19_PDF  = METAIR_BASE + "/metair/ajax/CSA019/ajaxUpdate?contentsType=2&dbKey=RJTD,QYYA86&lastDate="
AJAX16      = METAIR_BASE + "/metair/ajax/CSA016/ajaxUpdate?did1=CSA016&did2=0&lastDate="

CSA019_DIR = {
    "QBCK95":"/pict/UBCK/", "QBSA95":"/pict/UBSA/", "QBQA95":"/pict/UBTT/",
    "QBRA95":"/pict/UBGG/", "QBUA95":"/pict/UBBB/", "QBFF95":"/pict/UBFF/",
    "QBAH95":"/pict/UBAH/", "QBIG95":"/pict/UBIG/", "QACA95":"/pict/SPAS/",
    "QACE98":"/pict/FSAS24/","QBMA98":"/pict/ABJP/", "QBEY10":"/pict/FBJP/",
    "QYYA82":"/airport/all/wxcarea/","QNSA22":"/pict/TSAT_1/","QRAI85":"/pict/FXJP854/",
}
METAIR_HEADERS = {
    "Referer":    "https://www3.metair.go.jp/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
#  Ã£ÂÂ¹Ã£ÂÂ±Ã£ÂÂ¸Ã£ÂÂ¥Ã£ÂÂ¼Ã£ÂÂ«Ã¥ÂÂ¤Ã¥Â®Â
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
def should_send_to_recipient(r):
    time_slots = r.get("time_slots", [])
    if not time_slots:
        return False
    JST       = datetime.timezone(datetime.timedelta(hours=9))
    now_jst   = datetime.datetime.now(JST)
    h, m      = now_jst.hour, now_jst.minute
    total_min = h * 60 + m
    print(f"    [{r.get('name','?')}] JST {h:02d}:{m:02d}")
    for i, slot in enumerate(time_slots):
        start    = int(slot.get("start", 0))
        end      = int(slot.get("end", 24))
        interval = int(slot.get("interval_minutes", 60))
        end_h    = 0 if end >= 24 else end
        if start <= (end if end < 24 else 24):
            in_slot = start <= h < (end if end < 24 else 24) or (end >= 24 and h == 0 and m < 15)
        else:
            in_slot = h >= start or h < end_h
        if not in_slot:
            continue
        ok = (total_min % interval) < 15
        print(f"    Ã¢ÂÂ Ã¦ÂÂÃ©ÂÂÃ¥Â¸Â¯{i+1}({start}Ã£ÂÂ{end}Ã¦ÂÂ/{interval}Ã¥ÂÂ) {'Ã¢ÂÂÃ©ÂÂÃ¤Â¿Â¡' if ok else 'Ã¢ÂÂÃ£ÂÂ¹Ã£ÂÂ­Ã£ÂÂÃ£ÂÂ'}")
        if ok:
            return True
    return False

# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
#  Ã§ÂÂ»Ã¥ÂÂÃ¥ÂÂÃ¥Â¾ÂÃ£ÂÂ¦Ã£ÂÂ¼Ã£ÂÂÃ£ÂÂ£Ã£ÂÂªÃ£ÂÂÃ£ÂÂ£
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
def get_font(size=36):
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", size)
    except Exception:
        return ImageFont.load_default()

def fetch_image(url):
    hdrs = METAIR_HEADERS if "metair.go.jp" in url else {}
    try:
        r = requests.get(url, headers=hdrs, timeout=30)
        if r.status_code != 200:
            print(f"    HTTP {r.status_code}: {url}")
            return None
        im = Image.open(io.BytesIO(r.content))
        if im.mode in ("RGBA","LA") or (im.mode=="P" and "transparency" in im.info):
            im = im.convert("RGBA")
            bg = Image.new("RGBA", im.size, (255,255,255,255))
            im = Image.alpha_composite(bg, im).convert("RGB")
        else:
            im = im.convert("RGB")
        return im
    except Exception as e:
        print(f"    fetch error [{url}]: {e}")
        return None

def ts_to_label(ts):
    try:
        if len(ts)==14: return datetime.datetime.strptime(ts,"%Y%m%d%H%M%S").strftime("%Y/%m/%d %H:%MZ")
        if len(ts)==12: return datetime.datetime.strptime(ts,"%Y%m%d%H%M").strftime("%Y/%m/%d %H:%MZ")
    except Exception: pass
    return ts

def find_jma_timestamp():
    now = datetime.datetime.utcnow()
    for delta in range(12):
        t = now - datetime.timedelta(minutes=30*delta)
        t = t.replace(minute=(t.minute//30)*30, second=0, microsecond=0)
        for ts in [t.strftime("%Y%m%d%H%M")+"00", t.strftime("%Y%m%d%H%M")]:
            url = f"{JMA_BASE}WANLC101_RJTD_{ts}.PNG"
            try:
                r = requests.head(url, timeout=10)
                if r.status_code == 200:
                    print(f"  JMA timestamp: {ts}")
                    return ts
            except Exception: pass
    return None

def probe_metair_direct(wmo_code):
    dir_path = CSA019_DIR.get(wmo_code)
    if not dir_path: return None, None
    now = datetime.datetime.utcnow()
    for delta in range(49):
        t = now - datetime.timedelta(minutes=30*delta)
        t = t.replace(minute=(t.minute//30)*30, second=0, microsecond=0)
        for ts in [t.strftime("%Y%m%d%H%M%S"), t.strftime("%Y%m%d%H%M")]:
            url = f"{METAIR_BASE}{dir_path}{wmo_code}_RJTD_{ts}.png"
            try:
                rr = requests.head(url, headers=METAIR_HEADERS, timeout=6)
                if rr.status_code == 200:
                    return url, ts
            except Exception: pass
    return None, None

def get_csa019_latest(wmo_code):
    try:
        r = requests.get(AJAX19.format(code=wmo_code), headers=METAIR_HEADERS, timeout=15)
        ds = r.json().get("dataSet")
        if ds and isinstance(ds,list) and len(ds)>0:
            fname = ds[-1]["fname"]
            ts    = fname.split("_RJTD_")[1].replace(".png","")
            return METAIR_BASE+fname, ts
    except Exception as e:
        print(f"    AJAXÃ¥Â¤Â±Ã¦ÂÂ [{wmo_code}]: {e}")
    return probe_metair_direct(wmo_code)

def get_qyya86_latest():
    try:
        r  = requests.get(AJAX19_PDF, headers=METAIR_HEADERS, timeout=15)
        ds = r.json().get("dataSet")
        if not ds: return None, None
        if isinstance(ds, str): ds = json.loads(ds)
        entry = ds[-1]
        return METAIR_BASE+entry["fname"], entry["date"]
    except Exception as e:
        print(f"  QYYA86Ã£ÂÂ¨Ã£ÂÂ©Ã£ÂÂ¼: {e}")
        return None, None

def pdf_to_image(pdf_bytes):
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(2,2))
        return Image.frombytes("RGB", [pix.width,pix.height], pix.samples)
    except Exception as e:
        print(f"  PDFÃ¢ÂÂÃ§ÂÂ»Ã¥ÂÂÃ£ÂÂ¨Ã£ÂÂ©Ã£ÂÂ¼: {e}")
        return None

def get_akuten_latest_ts():
    # Ã£ÂÂ¾Ã£ÂÂAJAX16Ã£ÂÂ§Ã¥ÂÂÃ¥Â¾ÂÃ£ÂÂÃ¨Â©Â¦Ã£ÂÂ¿Ã£ÂÂ
    try:
        r = requests.get(AJAX16, headers=METAIR_HEADERS, timeout=15)
        data = r.json()
        ds = data.get("dataSet")
        if ds:
            # Ã£ÂÂÃ£ÂÂ¹Ã£ÂÂÃ¦Â§ÂÃ©ÂÂ Ã£ÂÂÃ¦ÂÂÃ¨Â»ÂÃ£ÂÂ«Ã¨Â§Â£Ã¦ÂÂ
            items = ds
            for _ in range(3):
                if isinstance(items, list) and items:
                    if isinstance(items[0], dict) and "fname" in items[0]:
                        break
                    items = items[0]
                else:
                    break
            if isinstance(items, dict) and "fname" in items:
                fname = items["fname"]
            elif isinstance(items, list) and items and isinstance(items[0], dict) and "fname" in items[0]:
                fname = items[0]["fname"]
            else:
                fname = None
            if fname and "_RJTD_" in fname:
                ts = fname.split("_RJTD_")[1].replace(".png","")
                print(f"  Ã¦ÂÂªÃ¥Â¤Â©TS (AJAX16): {ts}")
                return ts
        print(f"  WARN: AJAX16 Ã¦Â§ÂÃ©ÂÂ Ã¤Â¸ÂÃ¦ÂÂ Ã¢ÂÂ Ã§ÂÂ´Ã¦ÂÂ¥Ã£ÂÂÃ£ÂÂ­Ã£ÂÂ¼Ã£ÂÂÃ£ÂÂ¸")
    except Exception as e:
        print(f"  WARN: AJAX16Ã¥Â¤Â±Ã¦ÂÂ ({e}) Ã¢ÂÂ Ã§ÂÂ´Ã¦ÂÂ¥Ã£ÂÂÃ£ÂÂ­Ã£ÂÂ¼Ã£ÂÂÃ£ÂÂ¸")

    # Ã£ÂÂÃ£ÂÂ©Ã£ÂÂ¼Ã£ÂÂ«Ã£ÂÂÃ£ÂÂÃ£ÂÂ¯: FBSN Ã£ÂÂ«Ã¥Â¯Â¾Ã£ÂÂÃ£ÂÂ¦Ã§ÂÂ´Ã¦ÂÂ¥HEADÃ£ÂÂÃ£ÂÂ­Ã£ÂÂ¼Ã£ÂÂÃ¯Â¼Â3Ã¦ÂÂÃ©ÂÂÃ¥ÂÂ»Ã£ÂÂ¿Ã£ÂÂ§Ã¦ÂÂÃ¥Â¤Â§24Ã¦ÂÂÃ©ÂÂÃ¥ÂÂÃ£ÂÂ¾Ã£ÂÂ§Ã¯Â¼Â
    now = datetime.datetime.utcnow()
    for h in range(0, 25, 3):
        t = now - datetime.timedelta(hours=h)
        t = t.replace(minute=0, second=0, microsecond=0)
        for ts in [t.strftime("%Y%m%d%H%M%S"), t.strftime("%Y%m%d%H%M")]:
            url = f"{METAIR_BASE}/pict/akuten/FBSN/FBSN03_RJTD_{ts}.png"
            try:
                rr = requests.head(url, headers=METAIR_HEADERS, timeout=8)
                if rr.status_code == 200:
                    print(f"  Ã¦ÂÂªÃ¥Â¤Â©TS (probe): {ts}")
                    return ts
            except Exception:
                pass
    print("  WARN: Ã¦ÂÂªÃ¥Â¤Â©TSÃ£ÂÂÃ£ÂÂ­Ã£ÂÂ¼Ã£ÂÂÃ¥Â¤Â±Ã¦ÂÂ")
    return None

def fetch_with_echo_overlay(wmo_code, latest_url, latest_ts):
    latest_im = fetch_image(latest_url)
    if latest_im is None or not OVERLAY_ENABLED: return latest_im
    dir_path  = CSA019_DIR.get(wmo_code)
    if not dir_path or not latest_ts: return latest_im
    try:
        fmt = "%Y%m%d%H%M%S" if len(latest_ts)==14 else "%Y%m%d%H%M"
        dt_old = datetime.datetime.strptime(latest_ts, fmt) - datetime.timedelta(hours=1)
        for ts_fmt in [dt_old.strftime("%Y%m%d%H%M%S"), dt_old.strftime("%Y%m%d%H%M")]:
            url_old = f"{METAIR_BASE}{dir_path}{wmo_code}_RJTD_{ts_fmt}.png"
            try:
                rr = requests.head(url_old, headers=METAIR_HEADERS, timeout=6)
                if rr.status_code == 200:
                    old_im = fetch_image(url_old)
                    if old_im:
                        if old_im.size != latest_im.size:
                            old_im = old_im.resize(latest_im.size, Image.LANCZOS)
                        return Image.blend(latest_im, old_im, alpha=OVERLAY_ALPHA)
            except Exception: pass
    except Exception as e:
        print(f"  overlay error [{wmo_code}]: {e}")
    return latest_im

# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
#  Ã£ÂÂ¹Ã£ÂÂ­Ã£ÂÂÃ£ÂÂ1Ã¦ÂÂÃ£ÂÂ®Ã§ÂÂ»Ã¥ÂÂÃ¥ÂÂÃ¥Â¾Â
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
def fetch_slot_image(slot, jma_ts, akuten_ts):
    """Ã£ÂÂ¹Ã£ÂÂ­Ã£ÂÂÃ£ÂÂÃ¥Â®ÂÃ§Â¾Â©1Ã£ÂÂ¤Ã¥ÂÂÃ£ÂÂ®Ã§ÂÂ»Ã¥ÂÂÃ£ÂÂ¨Ã¨Â¡Â¨Ã§Â¤ÂºÃ£ÂÂ©Ã£ÂÂÃ£ÂÂ«Ã£ÂÂÃ¨Â¿ÂÃ£ÂÂÃ£ÂÂ"""
    if slot is None:
        return None, ""
    chart_type = slot.get("type", "")
    code       = slot.get("code", "")
    label      = slot.get("label", code)

    if chart_type in ("jma_wanlc", "jma_wanlf"):
        if not jma_ts:
            return None, label
        prefix = "WANLC" if chart_type == "jma_wanlc" else "WANLF"
        url    = f"{JMA_BASE}{prefix}{code}_RJTD_{jma_ts}.PNG"
        im     = fetch_image(url)
        return im, f"{label}\n{ts_to_label(jma_ts)}"

    elif chart_type == "metair_csa019":
        if code == "QYYA86":
            url, ts = get_qyya86_latest()
            if url:
                try:
                    rr = requests.get(url, headers=METAIR_HEADERS, timeout=30)
                    if rr.status_code == 200:
                        im = pdf_to_image(rr.content)
                        return im, f"{label}\n{ts_to_label(ts) if ts else 'Ã¥ÂÂÃ¥Â¾ÂÃ¥Â¤Â±Ã¦ÂÂ'}"
                except Exception as e:
                    print(f"  QYYA86Ã£ÂÂ¨Ã£ÂÂ©Ã£ÂÂ¼: {e}")
            return None, label
        else:
            url, ts = get_csa019_latest(code)
            if url:
                im = fetch_with_echo_overlay(code, url, ts) if code in OVERLAY_CODES \
                     else fetch_image(url)
                return im, f"{label}\n{ts_to_label(ts) if ts else 'Ã¥ÂÂÃ¥Â¾ÂÃ¥Â¤Â±Ã¦ÂÂ'}"
            return None, label

    elif chart_type == "metair_fb_akuten":
        if not akuten_ts:
            return None, label
        url = f"{METAIR_BASE}/pict/akuten/{code}/{code}03_RJTD_{akuten_ts}.png"
        im  = fetch_image(url)
        return im, f"{label}\n{ts_to_label(akuten_ts)} FT+03h"

    return None, label

# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
#  PDFÃ§ÂÂÃ¦ÂÂÃ¯Â¼ÂÃ£ÂÂÃ£ÂÂ¼Ã£ÂÂ¸Ã¥ÂÂÃ¤Â½ÂÃ£ÂÂ¬Ã£ÂÂ¤Ã£ÂÂ¢Ã£ÂÂ¦Ã£ÂÂÃ¯Â¼Â
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
def _draw_image_in_box(page, im, label, x0, y0, box_w, box_h):
    draw    = ImageDraw.Draw(page)
    font_sm = get_font(26)
    for i, line in enumerate(label.split("\n")[:2]):
        draw.text((x0+4, y0+i*24), line, fill=(0,0,120), font=font_sm)
    img_y = y0 + LABEL_H
    img_w = box_w
    img_h = box_h - LABEL_H
    if im is not None:
        ratio = min(img_w/im.width, img_h/im.height)
        nw, nh = int(im.width*ratio), int(im.height*ratio)
        page.paste(im.resize((nw,nh), Image.LANCZOS),
                   (x0+(img_w-nw)//2, img_y+(img_h-nh)//2))
    else:
        draw.text((x0+8, img_y+img_h//2-12), "Ã£ÂÂÃ£ÂÂ¼Ã£ÂÂ¿Ã£ÂÂªÃ£ÂÂ",
                  fill=(200,200,200), font=font_sm)
    draw.rectangle([x0, y0, x0+box_w-1, y0+box_h-1], outline=(210,210,210), width=1)

def build_one_page(page_cfg, slot_images, page_num, total_pages, dpi):
    """1Ã£ÂÂÃ£ÂÂ¼Ã£ÂÂ¸Ã¥ÂÂÃ£ÂÂ®PIL ImageÃ£ÂÂÃ§ÂÂÃ¦ÂÂÃ£ÂÂÃ£ÂÂÃ£ÂÂ"""
    cols    = page_cfg.get("cols", 2)
    rows    = page_cfg.get("rows", 4)
    orient  = page_cfg.get("orientation", "portrait")

    if orient == "landscape":
        pw = int(297 / 25.4 * dpi)
        ph = int(210 / 25.4 * dpi)
        a4_pt = (img2pdf.mm_to_pt(297), img2pdf.mm_to_pt(210))
    else:
        pw = int(210 / 25.4 * dpi)
        ph = int(297 / 25.4 * dpi)
        a4_pt = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))

    cell_w = (pw - 2*PAGE_MARGIN - (cols-1)*CELL_GAP) // cols
    cell_h = (ph - 2*PAGE_MARGIN - HEADER_H - (rows-1)*CELL_GAP) // rows

    now     = datetime.datetime.utcnow()
    header  = f"Ã¦Â°ÂÃ¨Â±Â¡Ã¦ÂÂÃ¥Â Â±  {now.strftime('%Y/%m/%d %H:%M')} UTC"

    page_img = Image.new("RGB", (pw, ph), (255, 255, 255))
    draw     = ImageDraw.Draw(page_img)
    draw.text((PAGE_MARGIN, PAGE_MARGIN), header, fill=(60,60,60), font=get_font(34))
    draw.text((pw-PAGE_MARGIN-150, PAGE_MARGIN),
              f"P.{page_num}/{total_pages}", fill=(130,130,130), font=get_font(30))

    for idx, (im, label) in enumerate(slot_images):
        if idx >= cols * rows:
            break
        if not label:
            continue
        col = idx % cols
        row = idx // cols
        x0  = PAGE_MARGIN + col * (cell_w + CELL_GAP)
        y0  = PAGE_MARGIN + HEADER_H + row * (cell_h + CELL_GAP)
        _draw_image_in_box(page_img, im, label, x0, y0, cell_w, cell_h)

    return page_img, a4_pt

def build_pdf(all_page_data, dpi):
    """全ページのデータからPDFバイト列を生成する。"""
    n_pages = len(all_page_data)
    page_images = []
    layouts     = []

    for pg_num, (page_cfg, slot_images) in enumerate(all_page_data, start=1):
        page_img, a4_pt = build_one_page(page_cfg, slot_images, pg_num, n_pages, dpi)
        page_images.append(page_img.convert("RGB"))
        layouts.append(a4_pt)

    if not page_images:
        return b'', 0

    # ① PyMuPDF + img2pdf（A4正確サイズ）
    try:
        import fitz
        doc = fitz.open()
        for im, a4_pt in zip(page_images, layouts):
            jpeg_buf = io.BytesIO()
            im.save(jpeg_buf, "JPEG", quality=JPEG_QUALITY, dpi=(dpi, dpi))
            jpeg_buf.seek(0)
            part_bytes = img2pdf.convert(jpeg_buf, layout_fun=img2pdf.get_layout_fun(a4_pt))
            tmp = fitz.open(stream=bytes(part_bytes), filetype="pdf")
            doc.insert_pdf(tmp)
            tmp.close()
        result = bytes(doc.tobytes())
        doc.close()
        print(f"  PDF生成: PyMuPDF+img2pdf ({n_pages}p)")
        return result, n_pages
    except Exception as e:
        print(f"  PyMuPDF失敗 ({e}) → PIL fallback")

    # ② PIL直接PDF出力（確実に開けるPDFを生成）
    buf = io.BytesIO()
    page_images[0].save(
        buf, format="PDF", save_all=True,
        append_images=page_images[1:],
        resolution=dpi
    )
    result = buf.getvalue()
    print(f"  PDF生成: PIL fallback ({n_pages}p)")
    return result, n_pages
def build_pdf_auto_dpi(all_page_data):
    """Ã£ÂÂµÃ£ÂÂ¤Ã£ÂÂºÃ¤Â¸ÂÃ©ÂÂÃ¥ÂÂÃ£ÂÂ§Ã¦ÂÂÃ¥Â¤Â§DPIÃ£ÂÂ®PDFÃ£ÂÂÃ¨ÂÂªÃ¥ÂÂÃ§ÂÂÃ¦ÂÂÃ£ÂÂÃ£ÂÂÃ£ÂÂ"""
    # DPIÃ£ÂÂÃ¦Â®ÂµÃ©ÂÂÃ§ÂÂÃ£ÂÂ«Ã¤Â¸ÂÃ£ÂÂÃ£ÂÂÃ£ÂÂ¹Ã£ÂÂÃ£ÂÂÃ£ÂÂÃ¯Â¼ÂMAX_DPIÃ¤Â»Â¥Ã¤Â¸ÂÃ£ÂÂ®Ã£ÂÂ¿Ã¤Â½Â¿Ã§ÂÂ¨Ã¯Â¼Â
    dpi_steps = [d for d in [300, 250, 216, 180, 150, 120, 96, 72] if d <= MAX_DPI]
    if not dpi_steps or dpi_steps[0] != MAX_DPI:
        dpi_steps = [MAX_DPI] + dpi_steps

    for dpi in dpi_steps:
        print(f"  DPI {dpi} Ã£ÂÂ§Ã§ÂÂÃ¦ÂÂÃ¤Â¸Â­...")
        pdf_bytes, n_pages = build_pdf(all_page_data, dpi)
        size_mb = len(pdf_bytes) / (1024 * 1024)
        print(f"  Ã¢ÂÂ Ã£ÂÂµÃ£ÂÂ¤Ã£ÂÂº: {size_mb:.1f} MB (Ã¤Â¸ÂÃ©ÂÂ: {MAX_MAIL_MB} MB)")
        if size_mb <= MAX_MAIL_MB:
            print(f"  Ã¢ÂÂ DPI {dpi} Ã£ÂÂ§Ã©ÂÂÃ¤Â¿Â¡ ({size_mb:.1f} MB)")
            return pdf_bytes, n_pages, dpi, size_mb

    # Ã¦ÂÂÃ¥Â°ÂDPIÃ£ÂÂ§Ã£ÂÂÃ¨Â¶ÂÃ©ÂÂÃ£ÂÂÃ£ÂÂÃ¥Â Â´Ã¥ÂÂÃ£ÂÂ¯Ã£ÂÂÃ£ÂÂ®Ã£ÂÂ¾Ã£ÂÂ¾Ã©ÂÂÃ¤Â¿Â¡
    print(f"  Ã¢ÂÂ  Ã¦ÂÂÃ¥Â°ÂDPI({dpi_steps[-1]})Ã£ÂÂ§Ã£ÂÂÃ£ÂÂµÃ£ÂÂ¤Ã£ÂÂºÃ¨Â¶ÂÃ©ÂÂ ({size_mb:.1f} MB) - Ã£ÂÂÃ£ÂÂ®Ã£ÂÂ¾Ã£ÂÂ¾Ã©ÂÂÃ¤Â¿Â¡")
    return pdf_bytes, n_pages, dpi_steps[-1], size_mb

# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
#  Ã¥Â¤Â©Ã¦Â°ÂÃ¥ÂÂ³Ã¥ÂÂÃ©ÂÂÃ¯Â¼ÂÃ£ÂÂÃ£ÂÂ¼Ã£ÂÂ¸Ã¥ÂÂÃ¤Â½ÂÃ¯Â¼Â
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
def collect_charts():
    """config.pages Ã£ÂÂÃ¨ÂµÂ°Ã¦ÂÂ»Ã£ÂÂÃ£ÂÂÃ¥ÂÂ¨Ã£ÂÂ¹Ã£ÂÂ­Ã£ÂÂÃ£ÂÂÃ£ÂÂ®Ã§ÂÂ»Ã¥ÂÂÃ£ÂÂÃ¥ÂÂÃ¥Â¾ÂÃ£ÂÂÃ£ÂÂÃ£ÂÂ
    Returns: [(page_cfg, [(im, label), ...]), ...]"""
    pages_cfg = CONFIG.get("pages", [])
    if not pages_cfg:
        print("WARN: config.json Ã£ÂÂ« pages Ã£ÂÂÃ¥Â®ÂÃ§Â¾Â©Ã£ÂÂÃ£ÂÂÃ£ÂÂ¦Ã£ÂÂÃ£ÂÂ¾Ã£ÂÂÃ£ÂÂ")
        return []

    # Ã¥ÂÂ±Ã©ÂÂÃ£ÂÂ¿Ã£ÂÂ¤Ã£ÂÂ Ã£ÂÂ¹Ã£ÂÂ¿Ã£ÂÂ³Ã£ÂÂÃ¥ÂÂÃ¥Â¾ÂÃ¯Â¼ÂJMAÃ£ÂÂ»Ã¦ÂÂªÃ¥Â¤Â©Ã£ÂÂ¯1Ã¥ÂÂÃ£ÂÂ Ã£ÂÂÃ¯Â¼Â
    needs_jma    = any(
        s and s.get("type") in ("jma_wanlc","jma_wanlf")
        for pg in pages_cfg for s in pg.get("slots",[])
    )
    needs_akuten = any(
        s and s.get("type") == "metair_fb_akuten"
        for pg in pages_cfg for s in pg.get("slots",[])
    )

    jma_ts    = None
    akuten_ts = None
    if needs_jma:
        print("=== JMA Ã£ÂÂ¿Ã£ÂÂ¤Ã£ÂÂ Ã£ÂÂ¹Ã£ÂÂ¿Ã£ÂÂ³Ã£ÂÂÃ¥ÂÂÃ¥Â¾Â ===")
        jma_ts = find_jma_timestamp()
        if not jma_ts:
            print("  WARN: JMA Ã£ÂÂ¿Ã£ÂÂ¤Ã£ÂÂ Ã£ÂÂ¹Ã£ÂÂ¿Ã£ÂÂ³Ã£ÂÂÃ¥ÂÂÃ¥Â¾ÂÃ¥Â¤Â±Ã¦ÂÂ")
    if needs_akuten:
        print("=== Ã¦ÂÂªÃ¥Â¤Â©Ã¤ÂºÂÃ¦ÂÂ³Ã¥ÂÂ³Ã£ÂÂ¿Ã£ÂÂ¤Ã£ÂÂ Ã£ÂÂ¹Ã£ÂÂ¿Ã£ÂÂ³Ã£ÂÂÃ¥ÂÂÃ¥Â¾Â ===")
        akuten_ts = get_akuten_latest_ts()
        if not akuten_ts:
            print("  WARN: Ã¦ÂÂªÃ¥Â¤Â©Ã¤ÂºÂÃ¦ÂÂ³Ã¥ÂÂ³Ã£ÂÂ¿Ã£ÂÂ¤Ã£ÂÂ Ã£ÂÂ¹Ã£ÂÂ¿Ã£ÂÂ³Ã£ÂÂÃ¥ÂÂÃ¥Â¾ÂÃ¥Â¤Â±Ã¦ÂÂ")

    all_page_data = []
    total_charts  = 0

    for pg_idx, page_cfg in enumerate(pages_cfg):
        print(f"\n=== Ã£ÂÂÃ£ÂÂ¼Ã£ÂÂ¸ {pg_idx+1} ({page_cfg.get('orientation','portrait')} "
              f"{page_cfg.get('cols',2)}ÃÂ{page_cfg.get('rows',4)}) ===")
        slots      = page_cfg.get("slots", [])
        slot_images = []
        for s_idx, slot in enumerate(slots):
            if slot is None:
                slot_images.append((None, ""))
                continue
            im, label = fetch_slot_image(slot, jma_ts, akuten_ts)
            slot_images.append((im, label))
            total_charts += 1
            print(f"  [{s_idx+1}] [{'OK' if im else 'NG'}] {slot.get('label', slot.get('code',''))}")
        all_page_data.append((page_cfg, slot_images))

    print(f"\nÃ¥ÂÂÃ¨Â¨Â: {len(pages_cfg)}Ã£ÂÂÃ£ÂÂ¼Ã£ÂÂ¸ / {total_charts}Ã£ÂÂ¹Ã£ÂÂ­Ã£ÂÂÃ£ÂÂ")
    return all_page_data

# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
#  Ã£ÂÂ¡Ã£ÂÂ¼Ã£ÂÂ«Ã©ÂÂÃ¤Â¿Â¡
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
def send_email_to(recipient, pdf_bytes, n_pages, dpi=None, size_mb=None):
    now      = datetime.datetime.utcnow()
    to_addr  = recipient["email"]
    name     = recipient.get("name", "")
    subject  = f"Ã¦Â°ÂÃ¨Â±Â¡Ã¦ÂÂÃ¥Â Â± {now.strftime('%Y/%m/%d %H:%MZ')} ({n_pages}p)"
    filename = f"weather_{now.strftime('%Y%m%d_%H%MZ')}.pdf"
    dpi_info = f"DPI: {dpi} / Ã£ÂÂµÃ£ÂÂ¤Ã£ÂÂº: {size_mb:.1f} MB" if dpi and size_mb else ""
    body = (
        f"Ã¨ÂÂªÃ§Â©ÂºÃ¦Â°ÂÃ¨Â±Â¡Ã¦ÂÂÃ¥Â Â±\n"
        f"Ã¥ÂÂÃ¥Â¾ÂÃ¦ÂÂÃ¥ÂÂ»: {now.strftime('%Y/%m/%d %H:%M')} UTC\n"
        f"PDF: {n_pages}Ã£ÂÂÃ£ÂÂ¼Ã£ÂÂ¸\n"
        + (f"{dpi_info}\n" if dpi_info else "")
        + f"Ã©ÂÂÃ¤Â¿Â¡Ã¥ÂÂ: {name} <{to_addr}>\n"
    )
    msg            = MIMEMultipart()
    msg["From"]    = MAIL_FROM
    msg["To"]      = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    att = MIMEBase("application", "pdf")
    att.set_payload(pdf_bytes)
    encoders.encode_base64(att)
    att.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(att)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    print(f"  Ã¢ÂÂ Ã©ÂÂÃ¤Â¿Â¡Ã¥Â®ÂÃ¤ÂºÂ Ã¢ÂÂ {name} <{to_addr}>")

# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
#  Ã£ÂÂ¡Ã£ÂÂ¤Ã£ÂÂ³
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
def save_preview_cache():
    """Ã¦ÂÂ°Ã£ÂÂÃ£ÂÂÃ£ÂÂ³Ã£ÂÂ¼Ã£ÂÂÃ£ÂÂ®Ã§ÂÂ»Ã¥ÂÂÃ£ÂÂ®Ã£ÂÂ¿ /cache/ Ã£ÂÂ«Ã£ÂÂ³Ã£ÂÂÃ£ÂÂÃ£ÂÂÃ¯Â¼ÂÃ¦ÂÂ¢Ã¥Â­ÂÃ£ÂÂ¯Ã£ÂÂ¹Ã£ÂÂ­Ã£ÂÂÃ£ÂÂÃ¯Â¼Â"""
    import base64
    token = os.environ.get("GITHUB_TOKEN", "")
    repo  = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("  GITHUB_TOKEN/GITHUB_REPOSITORYÃ¦ÂÂªÃ¨Â¨Â­Ã¥Â®Â Ã¢ÂÂ Ã£ÂÂ­Ã£ÂÂ£Ã£ÂÂÃ£ÂÂ·Ã£ÂÂ¥Ã£ÂÂ¹Ã£ÂÂ­Ã£ÂÂÃ£ÂÂ")
        return

    api_hdrs = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    base_url = f"https://api.github.com/repos/{repo}/contents/cache"

    # Ã¦ÂÂ¢Ã¥Â­ÂÃ£ÂÂ­Ã£ÂÂ£Ã£ÂÂÃ£ÂÂ·Ã£ÂÂ¥Ã¤Â¸ÂÃ¨Â¦Â§Ã£ÂÂÃ¥ÂÂÃ¥Â¾Â
    cr = requests.get(base_url, headers=api_hdrs, timeout=10)
    existing = set()
    if cr.status_code == 200:
        existing = {f["name"] for f in cr.json() if isinstance(f, dict) and f.get("type") == "file"}
    print(f"  Ã¦ÂÂ¢Ã¥Â­ÂÃ£ÂÂ­Ã£ÂÂ£Ã£ÂÂÃ£ÂÂ·Ã£ÂÂ¥: {len(existing)}Ã¤Â»Â¶")

    # Ã£ÂÂ¿Ã£ÂÂ¤Ã£ÂÂ Ã£ÂÂ¹Ã£ÂÂ¿Ã£ÂÂ³Ã£ÂÂÃ£ÂÂÃ¥ÂÂÃ¥Â¾Â
    jma_ts    = find_jma_timestamp()
    akuten_ts = get_akuten_latest_ts()
    print(f"  JMA TS: {jma_ts} / Ã¦ÂÂªÃ¥Â¤Â©TS: {akuten_ts}")

    saved = 0
    for page in CONFIG.get("pages", []):
        for slot in (page.get("slots") or []):
            if not slot: continue
            chart_type = slot.get("type", "")
            code       = slot.get("code", "")
            if not code or not chart_type: continue

            fname = f"{chart_type}_{code}.png"
            if fname in existing:
                continue  # Ã¦ÂÂ¢Ã¥Â­ÂÃ£ÂÂ¯Ã£ÂÂ¹Ã£ÂÂ­Ã£ÂÂÃ£ÂÂ

            print(f"  Ã°ÂÂÂ¦ Ã¦ÂÂ°Ã¨Â¦Â: {fname}")
            im, _ = fetch_slot_image(slot, jma_ts, akuten_ts)
            if im is None:
                print(f"    Ã¢ÂÂ Ã¥ÂÂÃ¥Â¾ÂÃ¥Â¤Â±Ã¦ÂÂ")
                continue

            buf = io.BytesIO()
            im.convert("RGB").save(buf, "PNG")
            content_b64 = base64.b64encode(buf.getvalue()).decode()

            pr = requests.put(
                f"{base_url}/{fname}",
                headers=api_hdrs,
                json={"message": f"cache: add {fname}", "content": content_b64},
                timeout=30,
            )
            if pr.status_code in (200, 201):
                saved += 1
                print(f"    Ã¢ÂÂ Ã¤Â¿ÂÃ¥Â­ÂÃ¥Â®ÂÃ¤ÂºÂ")
            else:
                print(f"    Ã¢ÂÂ Ã¤Â¿ÂÃ¥Â­ÂÃ¥Â¤Â±Ã¦ÂÂ: {pr.status_code}")

    print(f"  Ã£ÂÂ­Ã£ÂÂ£Ã£ÂÂÃ£ÂÂ·Ã£ÂÂ¥Ã¦ÂÂ´Ã¦ÂÂ°: {saved}Ã¤Â»Â¶Ã¨Â¿Â½Ã¥ÂÂ ")


def main():
    recipients = CONFIG.get("recipients", [])
    enabled    = [r for r in recipients if r.get("enabled", True)]

    if not enabled:
        print("Ã¦ÂÂÃ¥ÂÂ¹Ã£ÂÂªÃ¥ÂÂÃ¤Â¿Â¡Ã¨ÂÂÃ£ÂÂªÃ£ÂÂ - Ã§ÂµÂÃ¤ÂºÂ")
        sys.exit(0)

    if GITHUB_EVENT == "workflow_dispatch":
        print("=== workflow_dispatch: Ã¥ÂÂ¨Ã¥ÂÂÃ¤Â¿Â¡Ã¨ÂÂÃ£ÂÂ«Ã©ÂÂÃ¤Â¿Â¡ ===")
        targets = enabled
    else:
        print("=== Ã£ÂÂ¹Ã£ÂÂ±Ã£ÂÂ¸Ã£ÂÂ¥Ã£ÂÂ¼Ã£ÂÂ«Ã¥Â®ÂÃ¨Â¡Â: Ã©ÂÂÃ¤Â¿Â¡Ã¥Â¯Â¾Ã¨Â±Â¡Ã£ÂÂÃ¥ÂÂ¤Ã¥Â®Â ===")
        targets = [r for r in enabled if should_send_to_recipient(r)]

    if not targets:
        print("Ã©ÂÂÃ¤Â¿Â¡Ã¥Â¯Â¾Ã¨Â±Â¡Ã£ÂÂªÃ£ÂÂ - Ã£ÂÂ¹Ã£ÂÂ­Ã£ÂÂÃ£ÂÂ")
        sys.exit(0)

    print(f"\nÃ©ÂÂÃ¤Â¿Â¡Ã¥Â¯Â¾Ã¨Â±Â¡: {[r.get('name','?') for r in targets]}")

    print("\n=== Ã¥Â¤Â©Ã¦Â°ÂÃ¥ÂÂ³Ã¥ÂÂÃ©ÂÂ ===")
    all_page_data = collect_charts()

    if not all_page_data:
        print("Ã£ÂÂÃ£ÂÂ¼Ã£ÂÂ¸Ã£ÂÂÃ£ÂÂ¼Ã£ÂÂ¿Ã£ÂÂªÃ£ÂÂ - Ã§ÂµÂÃ¤ÂºÂ")
        sys.exit(1)

    print(f"\n=== PDFÃ§ÂÂÃ¦ÂÂ (DPIÃ¤Â¸ÂÃ©ÂÂ: {MAX_DPI}, Ã£ÂÂµÃ£ÂÂ¤Ã£ÂÂºÃ¤Â¸ÂÃ©ÂÂ: {MAX_MAIL_MB} MB) ===")
    pdf_bytes, n_pages, used_dpi, size_mb = build_pdf_auto_dpi(all_page_data)

    print("\n=== Ã£ÂÂ¡Ã£ÂÂ¼Ã£ÂÂ«Ã©ÂÂÃ¤Â¿Â¡ ===")
    for r in targets:
        send_email_to(r, pdf_bytes, n_pages, dpi=used_dpi, size_mb=size_mb)

    print(f"\n=== Ã¥Â®ÂÃ¤ÂºÂ: {n_pages}Ã£ÂÂÃ£ÂÂ¼Ã£ÂÂ¸ (DPI:{used_dpi} / {size_mb:.1f}MB) Ã¢ÂÂ {len(targets)}Ã¥ÂÂÃ£ÂÂ«Ã©ÂÂÃ¤Â¿Â¡ ===")

    print("\n=== Ã£ÂÂÃ£ÂÂ¬Ã£ÂÂÃ£ÂÂ¥Ã£ÂÂ¼Ã£ÂÂ­Ã£ÂÂ£Ã£ÂÂÃ£ÂÂ·Ã£ÂÂ¥Ã¦ÂÂ´Ã¦ÂÂ° ===")
    save_preview_cache()

if __name__ == "__main__":
    main()
