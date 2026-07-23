#!/usr/bin/env python3
"""
æ°è±¡æå ±ã¡ã¼ã«éä¿¡ v2 (ãã¼ã¸åä½ã¬ã¤ã¢ã¦ãå¯¾å¿)

ä»çµã¿:
  - config.json ã® pages[] ã«ãã¼ã¸åä½ã§ã¬ã¤ã¢ã¦ãã¨å¤©æ°å³ã¹ã­ãããå®ç¾©
  - åãã¼ã¸: orientation(portrait/landscape), cols, rows, slots[]
  - slots[] ã®åè¦ç´ : {"type": ..., "code": ..., "label": ...} or null
  - recipients[] ã«åä¿¡èãè¤æ°ç»é² (time_slots ã¹ã±ã¸ã¥ã¼ã«ä»ã)
  - PDFã¯1åçæ â éä¿¡å¯¾è±¡ã®åä¿¡èå¨å¡ã«åå¥éä¿¡
  - workflow_dispatch ã¯å¨æå¹åä¿¡èã«å¼·å¶éä¿¡
"""

import os, io, json, smtplib, datetime, sys, requests
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from PIL import Image, ImageDraw, ImageFont
import img2pdf

# ââ ç°å¢å¤æ° ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
MAIL_FROM    = os.environ["MAIL_FROM"]
SMTP_HOST    = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT    = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER    = os.environ["SMTP_USER"]
SMTP_PASS    = os.environ["SMTP_PASS"]
GITHUB_EVENT = os.environ.get("GITHUB_EVENT_NAME", "schedule")

# ââ config.json èª­ã¿è¾¼ã¿ ââââââââââââââââââââââââââââââââââââââââââââââââââ
def load_config():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_config()

# ââ ã°ã­ã¼ãã«è¨­å®ï¼ãã¼ã¸å±éï¼ ââââââââââââââââââââââââââââââââââââââââââ
_pdf         = CONFIG["pdf"]
DPI          = _pdf.get("dpi", 150)        # å¾æ¹äºæç¨ï¼ç´æ¥ä½¿ç¨ã¯ããªãï¼
PAGE_MARGIN  = _pdf["page_margin"]
HEADER_H     = _pdf["header_h"]
CELL_GAP     = _pdf["cell_gap"]
LABEL_H      = _pdf["label_h"]
JPEG_QUALITY = _pdf.get("jpeg_quality", 90)
MAX_DPI      = _pdf.get("max_dpi", DPI)    # DPIä¸é
MAX_MAIL_MB  = float(_pdf.get("max_mail_mb", 20.0))  # ã¡ã¼ã«ãµã¤ãºä¸é(MB)

# ââ ãªã¼ãã¼ã¬ã¤ ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
_ov             = CONFIG["overlay"]
OVERLAY_ENABLED = _ov.get("enabled", True)
OVERLAY_ALPHA   = float(_ov.get("alpha", 0.2))
OVERLAY_CODES   = {"QBSA95","QBCK95","QBRA95","QBQA95","QBFF95","QBUA95","QBIG95","QBAH95"}

# ââ URLå®ç¾© âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
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

# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
#  ã¹ã±ã¸ã¥ã¼ã«å¤å®
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
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
        print(f"    â æéå¸¯{i+1}({start}ã{end}æ/{interval}å) {'âéä¿¡' if ok else 'âã¹ã­ãã'}")
        if ok:
            return True
    return False

# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
#  ç»ååå¾ã¦ã¼ãã£ãªãã£
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
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
        print(f"    AJAXå¤±æ [{wmo_code}]: {e}")
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
        print(f"  QYYA86ã¨ã©ã¼: {e}")
        return None, None

def pdf_to_image(pdf_bytes):
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(2,2))
        return Image.frombytes("RGB", [pix.width,pix.height], pix.samples)
    except Exception as e:
        print(f"  PDFâç»åã¨ã©ã¼: {e}")
        return None

def get_akuten_latest_ts():
    # ã¾ãAJAX16ã§åå¾ãè©¦ã¿ã
    try:
        r = requests.get(AJAX16, headers=METAIR_HEADERS, timeout=15)
        data = r.json()
        ds = data.get("dataSet")
        if ds:
            # ãã¹ãæ§é ãæè»ã«è§£æ
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
                print(f"  æªå¤©TS (AJAX16): {ts}")
                return ts
        print(f"  WARN: AJAX16 æ§é ä¸æ â ç´æ¥ãã­ã¼ãã¸")
    except Exception as e:
        print(f"  WARN: AJAX16å¤±æ ({e}) â ç´æ¥ãã­ã¼ãã¸")

    # ãã©ã¼ã«ããã¯: FBSN ã«å¯¾ãã¦ç´æ¥HEADãã­ã¼ãï¼3æéå»ã¿ã§æå¤§24æéåã¾ã§ï¼
    now = datetime.datetime.utcnow()
    for h in range(0, 25, 3):
        t = now - datetime.timedelta(hours=h)
        t = t.replace(minute=0, second=0, microsecond=0)
        for ts in [t.strftime("%Y%m%d%H%M%S"), t.strftime("%Y%m%d%H%M")]:
            url = f"{METAIR_BASE}/pict/akuten/FBSN/FBSN03_RJTD_{ts}.png"
            try:
                rr = requests.head(url, headers=METAIR_HEADERS, timeout=8)
                if rr.status_code == 200:
                    print(f"  æªå¤©TS (probe): {ts}")
                    return ts
            except Exception:
                pass
    print("  WARN: æªå¤©TSãã­ã¼ãå¤±æ")
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

# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
#  ã¹ã­ãã1æã®ç»ååå¾
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def fetch_slot_image(slot, jma_ts, akuten_ts):
    """ã¹ã­ããå®ç¾©1ã¤åã®ç»åã¨è¡¨ç¤ºã©ãã«ãè¿ãã"""
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
                        return im, f"{label}\n{ts_to_label(ts) if ts else 'åå¾å¤±æ'}"
                except Exception as e:
                    print(f"  QYYA86ã¨ã©ã¼: {e}")
            return None, label
        else:
            url, ts = get_csa019_latest(code)
            if url:
                im = fetch_with_echo_overlay(code, url, ts) if code in OVERLAY_CODES \
                     else fetch_image(url)
                return im, f"{label}\n{ts_to_label(ts) if ts else 'åå¾å¤±æ'}"
            return None, label

    elif chart_type == "metair_fb_akuten":
        if not akuten_ts:
            return None, label
        url = f"{METAIR_BASE}/pict/akuten/{code}/{code}03_RJTD_{akuten_ts}.png"
        im  = fetch_image(url)
        return im, f"{label}\n{ts_to_label(akuten_ts)} FT+03h"

    return None, label

# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
#  PDFçæï¼ãã¼ã¸åä½ã¬ã¤ã¢ã¦ãï¼
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
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
        draw.text((x0+8, img_y+img_h//2-12), "ãã¼ã¿ãªã",
                  fill=(200,200,200), font=font_sm)
    draw.rectangle([x0, y0, x0+box_w-1, y0+box_h-1], outline=(210,210,210), width=1)

def build_one_page(page_cfg, slot_images, page_num, total_pages, dpi):
    """1ãã¼ã¸åã®PIL Imageãçæããã"""
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
    header  = f"æ°è±¡æå ±  {now.strftime('%Y/%m/%d %H:%M')} UTC"

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
    """å¨ãã¼ã¸ã®ãã¼ã¿ããPDFãã¤ãåãçæããã"""
    jpegs   = []
    layouts = []
    n_pages = len(all_page_data)

    for pg_num, (page_cfg, slot_images) in enumerate(all_page_data, start=1):
        page_img, a4_pt = build_one_page(page_cfg, slot_images, pg_num, n_pages, dpi)
        buf = io.BytesIO()
        page_img.save(buf, "JPEG", quality=JPEG_QUALITY, dpi=(dpi, dpi))
        jpegs.append(buf.getvalue())
        layouts.append(a4_pt)

    # è¤æ°ãµã¤ãºå¯¾å¿: åãã¼ã¸ãã¨ã« layout_fun ãé©ç¨
    pdf_parts = []
    for jpeg, a4_pt in zip(jpegs, layouts):
        pdf_parts.append(img2pdf.convert(jpeg, layout_fun=img2pdf.get_layout_fun(a4_pt)))

    # å¨ãã¼ã¸ãçµåï¼PyMuPDFï¼
    try:
        import fitz
        doc = fitz.open()
        for part in pdf_parts:
            tmp = fitz.open(stream=part, filetype="pdf")
            doc.insert_pdf(tmp)
        return doc.tobytes(), n_pages
    except ImportError:
        a4_pt = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))
        return img2pdf.convert(jpegs, layout_fun=img2pdf.get_layout_fun(a4_pt)), n_pages

def build_pdf_auto_dpi(all_page_data):
    """ãµã¤ãºä¸éåã§æå¤§DPIã®PDFãèªåçæããã"""
    # DPIãæ®µéçã«ä¸ããã¹ãããï¼MAX_DPIä»¥ä¸ã®ã¿ä½¿ç¨ï¼
    dpi_steps = [d for d in [300, 250, 216, 180, 150, 120, 96, 72] if d <= MAX_DPI]
    if not dpi_steps or dpi_steps[0] != MAX_DPI:
        dpi_steps = [MAX_DPI] + dpi_steps

    for dpi in dpi_steps:
        print(f"  DPI {dpi} ã§çæä¸­...")
        pdf_bytes, n_pages = build_pdf(all_page_data, dpi)
        size_mb = len(pdf_bytes) / (1024 * 1024)
        print(f"  â ãµã¤ãº: {size_mb:.1f} MB (ä¸é: {MAX_MAIL_MB} MB)")
        if size_mb <= MAX_MAIL_MB:
            print(f"  â DPI {dpi} ã§éä¿¡ ({size_mb:.1f} MB)")
            return pdf_bytes, n_pages, dpi, size_mb

    # æå°DPIã§ãè¶éããå ´åã¯ãã®ã¾ã¾éä¿¡
    print(f"  â  æå°DPI({dpi_steps[-1]})ã§ããµã¤ãºè¶é ({size_mb:.1f} MB) - ãã®ã¾ã¾éä¿¡")
    return pdf_bytes, n_pages, dpi_steps[-1], size_mb

# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
#  å¤©æ°å³åéï¼ãã¼ã¸åä½ï¼
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def collect_charts():
    """config.pages ãèµ°æ»ããå¨ã¹ã­ããã®ç»åãåå¾ããã
    Returns: [(page_cfg, [(im, label), ...]), ...]"""
    pages_cfg = CONFIG.get("pages", [])
    if not pages_cfg:
        print("WARN: config.json ã« pages ãå®ç¾©ããã¦ãã¾ãã")
        return []

    # å±éã¿ã¤ã ã¹ã¿ã³ãåå¾ï¼JMAã»æªå¤©ã¯1åã ãï¼
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
        print("=== JMA ã¿ã¤ã ã¹ã¿ã³ãåå¾ ===")
        jma_ts = find_jma_timestamp()
        if not jma_ts:
            print("  WARN: JMA ã¿ã¤ã ã¹ã¿ã³ãåå¾å¤±æ")
    if needs_akuten:
        print("=== æªå¤©äºæ³å³ã¿ã¤ã ã¹ã¿ã³ãåå¾ ===")
        akuten_ts = get_akuten_latest_ts()
        if not akuten_ts:
            print("  WARN: æªå¤©äºæ³å³ã¿ã¤ã ã¹ã¿ã³ãåå¾å¤±æ")

    all_page_data = []
    total_charts  = 0

    for pg_idx, page_cfg in enumerate(pages_cfg):
        print(f"\n=== ãã¼ã¸ {pg_idx+1} ({page_cfg.get('orientation','portrait')} "
              f"{page_cfg.get('cols',2)}Ã{page_cfg.get('rows',4)}) ===")
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

    print(f"\nåè¨: {len(pages_cfg)}ãã¼ã¸ / {total_charts}ã¹ã­ãã")
    return all_page_data

# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
#  ã¡ã¼ã«éä¿¡
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def send_email_to(recipient, pdf_bytes, n_pages, dpi=None, size_mb=None):
    now      = datetime.datetime.utcnow()
    to_addr  = recipient["email"]
    name     = recipient.get("name", "")
    subject  = f"æ°è±¡æå ± {now.strftime('%Y/%m/%d %H:%MZ')} ({n_pages}p)"
    filename = f"weather_{now.strftime('%Y%m%d_%H%MZ')}.pdf"
    dpi_info = f"DPI: {dpi} / ãµã¤ãº: {size_mb:.1f} MB" if dpi and size_mb else ""
    body = (
        f"èªç©ºæ°è±¡æå ±\n"
        f"åå¾æå»: {now.strftime('%Y/%m/%d %H:%M')} UTC\n"
        f"PDF: {n_pages}ãã¼ã¸\n"
        + (f"{dpi_info}\n" if dpi_info else "")
        + f"éä¿¡å: {name} <{to_addr}>\n"
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
    print(f"  â éä¿¡å®äº â {name} <{to_addr}>")

# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
#  ã¡ã¤ã³
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def save_preview_cache():
    """æ°ããã³ã¼ãã®ç»åã®ã¿ /cache/ ã«ã³ãããï¼æ¢å­ã¯ã¹ã­ããï¼"""
    import base64
    token = os.environ.get("GITHUB_TOKEN", "")
    repo  = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("  GITHUB_TOKEN/GITHUB_REPOSITORYæªè¨­å® â ã­ã£ãã·ã¥ã¹ã­ãã")
        return

    api_hdrs = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    base_url = f"https://api.github.com/repos/{repo}/contents/cache"

    # æ¢å­ã­ã£ãã·ã¥ä¸è¦§ãåå¾
    cr = requests.get(base_url, headers=api_hdrs, timeout=10)
    existing = set()
    if cr.status_code == 200:
        existing = {f["name"] for f in cr.json() if isinstance(f, dict) and f.get("type") == "file"}
    print(f"  æ¢å­ã­ã£ãã·ã¥: {len(existing)}ä»¶")

    # ã¿ã¤ã ã¹ã¿ã³ããåå¾
    jma_ts    = find_jma_timestamp()
    akuten_ts = get_akuten_latest_ts()
    print(f"  JMA TS: {jma_ts} / æªå¤©TS: {akuten_ts}")

    saved = 0
    for page in CONFIG.get("pages", []):
        for slot in (page.get("slots") or []):
            if not slot: continue
            chart_type = slot.get("type", "")
            code       = slot.get("code", "")
            if not code or not chart_type: continue

            fname = f"{chart_type}_{code}.png"
            if fname in existing:
                continue  # æ¢å­ã¯ã¹ã­ãã

            print(f"  ð¦ æ°è¦: {fname}")
            im, _ = fetch_slot_image(slot, jma_ts, akuten_ts)
            if im is None:
                print(f"    â åå¾å¤±æ")
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
                print(f"    â ä¿å­å®äº")
            else:
                print(f"    â ä¿å­å¤±æ: {pr.status_code}")

    print(f"  ã­ã£ãã·ã¥æ´æ°: {saved}ä»¶è¿½å ")


def main():
    recipients = CONFIG.get("recipients", [])
    enabled    = [r for r in recipients if r.get("enabled", True)]

    if not enabled:
        print("æå¹ãªåä¿¡èãªã - çµäº")
        sys.exit(0)

    if GITHUB_EVENT == "workflow_dispatch":
        print("=== workflow_dispatch: å¨åä¿¡èã«éä¿¡ ===")
        targets = enabled
    else:
        print("=== ã¹ã±ã¸ã¥ã¼ã«å®è¡: éä¿¡å¯¾è±¡ãå¤å® ===")
        targets = [r for r in enabled if should_send_to_recipient(r)]

    if not targets:
        print("éä¿¡å¯¾è±¡ãªã - ã¹ã­ãã")
        sys.exit(0)

    print(f"\néä¿¡å¯¾è±¡: {[r.get('name','?') for r in targets]}")

    print("\n=== å¤©æ°å³åé ===")
    all_page_data = collect_charts()

    if not all_page_data:
        print("ãã¼ã¸ãã¼ã¿ãªã - çµäº")
        sys.exit(1)

    print(f"\n=== PDFçæ (DPIä¸é: {MAX_DPI}, ãµã¤ãºä¸é: {MAX_MAIL_MB} MB) ===")
    pdf_bytes, n_pages, used_dpi, size_mb = build_pdf_auto_dpi(all_page_data)

    print("\n=== ã¡ã¼ã«éä¿¡ ===")
    for r in targets:
        send_email_to(r, pdf_bytes, n_pages, dpi=used_dpi, size_mb=size_mb)

    print(f"\n=== å®äº: {n_pages}ãã¼ã¸ (DPI:{used_dpi} / {size_mb:.1f}MB) â {len(targets)}åã«éä¿¡ ===")

    print("\n=== ãã¬ãã¥ã¼ã­ã£ãã·ã¥æ´æ° ===")
    save_preview_cache()

if __name__ == "__main__":
    main()
