#!/usr/bin/env python3
"""
気象情報メール送信 v2 (ページ単位レイアウト対応)

仕組み:
  - config.json の pages[] にページ単位でレイアウトと天気図スロットを定義
  - 各ページ: orientation(portrait/landscape), cols, rows, slots[]
  - slots[] の各要素: {"type": ..., "code": ..., "label": ...} or null
  - recipients[] に受信者を複数登録 (time_slots スケジュール付き)
  - PDFは1回生成 → 送信対象の受信者全員に個別送信
  - workflow_dispatch は全有効受信者に強制送信
"""

import os, io, json, smtplib, datetime, sys, requests
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from PIL import Image, ImageDraw, ImageFont
import img2pdf

# ── 環境変数 ────────────────────────────────────────────────────────────────
MAIL_FROM    = os.environ["MAIL_FROM"]
SMTP_HOST    = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT    = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER    = os.environ["SMTP_USER"]
SMTP_PASS    = os.environ["SMTP_PASS"]

# ── config.json 読み込み ──────────────────────────────────────────────────
def load_config():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_config()

# ── グローバル設定（ページ共通） ──────────────────────────────────────────
_pdf         = CONFIG["pdf"]
DPI          = _pdf.get("dpi", 150)        # 後方互換用（直接使用はしない）
PAGE_MARGIN  = _pdf["page_margin"]
HEADER_H     = _pdf["header_h"]
CELL_GAP     = _pdf["cell_gap"]
LABEL_H      = _pdf["label_h"]
JPEG_QUALITY = _pdf.get("jpeg_quality", 90)
MAX_DPI      = _pdf.get("max_dpi", DPI)    # DPI上限
MIN_DPI      = _pdf.get("min_dpi", 72)       # DPI下限
MAX_MAIL_MB  = float(_pdf.get("max_mail_mb", 20.0))  # メールサイズ上限(MB)

# ── オーバーレイ ──────────────────────────────────────────────────────────
_ov             = CONFIG["overlay"]
OVERLAY_ENABLED = _ov.get("enabled", True)
OVERLAY_ALPHA   = float(_ov.get("alpha", 0.2))
OVERLAY_CODES   = {"QBSA95","QBCK95","QBRA95","QBQA95","QBFF95","QBUA95","QBIG95","QBAH95"}

# ── URL定義 ───────────────────────────────────────────────────────────────
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

# ── MetAir 認証 ───────────────────────────────────────────────────────────
METAIR_USER      = os.environ.get("METAIR_USER", "")
METAIR_PASS      = os.environ.get("METAIR_PASS", "")
METAIR_LOGIN_URL = "https://www3.metair.go.jp/metair/view/login/index.html"
_metair_session  = None

def get_metair_session():
    global _metair_session
    if _metair_session is not None:
        return _metair_session
    if not METAIR_USER or not METAIR_PASS:
        print("  MetAir認証情報未設定 (METAIR_USER/METAIR_PASS)")
        return None
    import re as _re2
    try:
        s = requests.Session()
        s.headers.update(METAIR_HEADERS)
        # ① GETでViewStateトークンを取得
        r0 = s.get(METAIR_LOGIN_URL, timeout=15)
        vs_m = _re2.search(r'name="javax\.faces\.ViewState"[^>]+value="([^"]+)"', r0.text)
        if not vs_m:
            print("  MetAir ViewState取得失敗")
            return None
        # ② JSFフォームフィールドでPOST
        data = {
            "loginForm":            "loginForm",
            "loginForm:username":   METAIR_USER,
            "loginForm:password":   METAIR_PASS,
            "loginForm:doLogin":    "",
            "loginForm:forceflg":   "",
            "javax.faces.ViewState": vs_m.group(1),
        }
        r1 = s.post(METAIR_LOGIN_URL, data=data, timeout=15, allow_redirects=True)
        if "login" not in r1.url.lower():
            print(f"  MetAirログイン成功: {r1.url}")
            _metair_session = s
            return s
        print(f"  MetAirログイン失敗: {r1.url}")
    except Exception as e:
        print(f"  MetAirログインエラー: {e}")
    return None

def get_csa003_image(code):
    """CSA003チャート取得 (code例: 'CSA003_TOPH_7')"""
    import re as _re
    parts      = code.rsplit("_", 1)
    csid       = parts[0]
    chart_type = parts[1] if len(parts) == 2 else "7"
    session    = get_metair_session()
    if not session:
        return None, None
    # ① AJAX
    for ajax_url in [
        f"https://www3.metair.go.jp/metair/ajax/CSA003/ajaxUpdate?contentsType=0&csid={csid}&type={chart_type}&lastDate=",
        f"https://www3.metair.go.jp/metair/ajax/CSA003/ajaxUpdate?contentsType=0&dbKey=RJTD,{csid}&type={chart_type}&lastDate=",
    ]:
        try:
            r = session.get(ajax_url, timeout=15)
            if r.status_code == 200 and r.text.strip():
                ds = r.json().get("dataSet")
                if ds and isinstance(ds, list) and ds:
                    entry = ds[-1]
                    fname = entry.get("fname", "")
                    if fname:
                        img_url = f"https://www3.metair.go.jp{fname}" if fname.startswith("/") else fname
                        ir = session.get(img_url, timeout=30)
                        if ir.status_code == 200:
                            im = Image.open(io.BytesIO(ir.content)).convert("RGB")
                            print(f"  CSA003 AJAX取得成功: {img_url[-50:]}")
                            return im, entry.get("date", "")
        except Exception as e:
            print(f"  CSA003 AJAX失敗: {e}")
    # ② HTMLページ解析
    page_url = f"https://www3.metair.go.jp/metair/view/winKobetsu/CSA003.html?csid={csid}&type={chart_type}"
    try:
        r = session.get(page_url, timeout=30)
        print(f"  CSA003 page status={r.status_code}")
        for pat in [
            r'"fname"\s*:\s*"([^"]+\.(?:png|jpg|PNG|JPG))"',
            r"<img[^>]+src=[\"']([^\"']+\.(?:png|jpg|PNG|JPG))[\"']",
            r"src\s*=\s*[\"']([^\"']*(?:/pict/|/img/)[^\"']+)[\"']",
        ]:
            for img_path in reversed(_re.findall(pat, r.text)):
                img_url = img_path if img_path.startswith("http") else f"https://www3.metair.go.jp{img_path}"
                try:
                    ir = session.get(img_url, timeout=30)
                    if ir.status_code == 200:
                        im = Image.open(io.BytesIO(ir.content)).convert("RGB")
                        print(f"  CSA003 HTML取得成功: {img_url[-50:]}")
                        return im, None
                except Exception:
                    continue
        print(f"  CSA003 解析失敗. preview: {r.text[:200]}")
    except Exception as e:
        print(f"  CSA003 HTMLエラー: {e}")
    return None, None

# ─────────────────────────────────────────────────────────────────────────
#  スケジュール判定
# ─────────────────────────────────────────────────────────────────────────

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
        print(f"    AJAX失敗 [{wmo_code}]: {e}")
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
        print(f"  QYYA86エラー: {e}")
        return None, None

def pdf_to_image(pdf_bytes):
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(2,2))
        return Image.frombytes("RGB", [pix.width,pix.height], pix.samples)
    except Exception as e:
        print(f"  PDF→画像エラー: {e}")
        return None

def get_akuten_latest_ts():
    # まずAJAX16で取得を試みる
    try:
        r = requests.get(AJAX16, headers=METAIR_HEADERS, timeout=15)
        data = r.json()
        ds = data.get("dataSet")
        if ds:
            # ネスト構造を柔軟に解析
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
                print(f"  悪天TS (AJAX16): {ts}")
                return ts
        print(f"  WARN: AJAX16 構造不明 → 直接プローブへ")
    except Exception as e:
        print(f"  WARN: AJAX16失敗 ({e}) → 直接プローブへ")

    # フォールバック: FBSN に対して直接HEADプローブ（3時間刻みで最大24時間前まで）
    now = datetime.datetime.utcnow()
    for h in range(0, 25, 3):
        t = now - datetime.timedelta(hours=h)
        t = t.replace(minute=0, second=0, microsecond=0)
        for ts in [t.strftime("%Y%m%d%H%M%S"), t.strftime("%Y%m%d%H%M")]:
            url = f"{METAIR_BASE}/pict/akuten/FBSN/FBSN03_RJTD_{ts}.png"
            try:
                rr = requests.head(url, headers=METAIR_HEADERS, timeout=8)
                if rr.status_code == 200:
                    print(f"  悪天TS (probe): {ts}")
                    return ts
            except Exception:
                pass
    print("  WARN: 悪天TSプローブ失敗")
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
                        print(f"  overlay OK [{wmo_code}] ts={ts_fmt}")
                        return Image.blend(latest_im, old_im, alpha=OVERLAY_ALPHA)
            except Exception: pass
    except Exception as e:
        print(f"  overlay error [{wmo_code}]: {e}")
        return latest_im
    print(f"  overlay skip [{wmo_code}]: 1æéåã®ç»åãªã")
    return latest_im

# ─────────────────────────────────────────────────────────────────────────
#  スロット1枚の画像取得
# ─────────────────────────────────────────────────────────────────────────
def fetch_slot_image(slot, jma_ts, akuten_ts):
    """スロット定義1つ分の画像と表示ラベルを返す。"""
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
                        return im, f"{label}\n{ts_to_label(ts) if ts else '取得失敗'}"
                except Exception as e:
                    print(f"  QYYA86エラー: {e}")
            return None, label
        else:
            url, ts = get_csa019_latest(code)
            if url:
                im = fetch_with_echo_overlay(code, url, ts) if code in OVERLAY_CODES \
                     else fetch_image(url)
                return im, f"{label}\n{ts_to_label(ts) if ts else '取得失敗'}"
            return None, label

    elif chart_type == "metair_fb_akuten":
        if not akuten_ts:
            return None, label
        url = f"{METAIR_BASE}/pict/akuten/{code}/{code}03_RJTD_{akuten_ts}.png"
        im  = fetch_image(url)
        return im, f"{label}\n{ts_to_label(akuten_ts)} FT+03h"

    elif chart_type == "metair_csa003":
        im, date_str = get_csa003_image(code)
        lbl = f"{label}\n{date_str}" if date_str else label
        return im, lbl

    return None, label

# ─────────────────────────────────────────────────────────────────────────
#  PDF生成（ページ単位レイアウト）
# ─────────────────────────────────────────────────────────────────────────
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
        draw.text((x0+8, img_y+img_h//2-12), "データなし",
                  fill=(200,200,200), font=font_sm)
    draw.rectangle([x0, y0, x0+box_w-1, y0+box_h-1], outline=(210,210,210), width=1)

def build_one_page(page_cfg, slot_images, page_num, total_pages, dpi):
    """1ページ分のPIL Imageを生成する。"""
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
    header  = f"気象情報  {now.strftime('%Y/%m/%d %H:%M')} UTC"

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
    """全ページのデータからPDFバイト列を生成する（PIL直接出力）。"""
    n_pages = len(all_page_data)
    page_images = []

    for pg_num, (page_cfg, slot_images) in enumerate(all_page_data, start=1):
        page_img, _ = build_one_page(page_cfg, slot_images, pg_num, n_pages, dpi)
        page_images.append(page_img.convert("RGB"))

    if not page_images:
        return b'', 0

    buf = io.BytesIO()
    page_images[0].save(
        buf, format="PDF", save_all=True,
        append_images=page_images[1:],
        resolution=dpi
    )
    result = buf.getvalue()
    print(f"  PDF生成: PIL ({n_pages}p, {len(result)//1024//1024:.0f}MB)")
    return result, n_pages
def build_pdf_auto_dpi(all_page_data):
    """サイズ上限内で最大DPIをバイナリサーチで自動決定してPDFを生成する。"""
    lo, hi = MIN_DPI, MAX_DPI
    best_bytes, best_pages, best_dpi, best_size = None, 0, lo, 0.0

    while lo <= hi:
        mid = (lo + hi) // 2
        print(f"  DPI {mid} で生成中... (探索範囲: {lo}〜{hi})")
        pdf_bytes, n_pages = build_pdf(all_page_data, mid)
        size_mb = len(pdf_bytes) / (1024 * 1024)
        print(f"  → {size_mb:.1f} MB (上限: {MAX_MAIL_MB} MB)")
        if size_mb <= MAX_MAIL_MB:
            best_bytes, best_pages, best_dpi, best_size = pdf_bytes, n_pages, mid, size_mb
            lo = mid + 1
        else:
            hi = mid - 1

    if best_bytes is None:
        # MIN_DPIでも超過 → そのまま送信
        pdf_bytes, n_pages = build_pdf(all_page_data, MIN_DPI)
        size_mb = len(pdf_bytes) / (1024 * 1024)
        print(f"  ⚠ 最小DPI({MIN_DPI})でもサイズ超過 ({size_mb:.1f} MB) - そのまま送信")
        return pdf_bytes, n_pages, MIN_DPI, size_mb

    print(f"  ✓ 最適DPI: {best_dpi} ({best_size:.1f} MB / 上限 {MAX_MAIL_MB} MB)")
    return best_bytes, best_pages, best_dpi, best_size


# ─────────────────────────────────────────────────────────────────────────
#  天気図収集（ページ単位）
# ─────────────────────────────────────────────────────────────────────────
def collect_charts():
    """config.pages を走査し、全スロットの画像を取得する。
    Returns: [(page_cfg, [(im, label), ...]), ...]"""
    pages_cfg = CONFIG.get("pages", [])
    if not pages_cfg:
        print("WARN: config.json に pages が定義されていません")
        return []

    # 共通タイムスタンプ取得（JMA・悪天は1回だけ）
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
        print("=== JMA タイムスタンプ取得 ===")
        jma_ts = find_jma_timestamp()
        if not jma_ts:
            print("  WARN: JMA タイムスタンプ取得失敗")
    if needs_akuten:
        print("=== 悪天予想図タイムスタンプ取得 ===")
        akuten_ts = get_akuten_latest_ts()
        if not akuten_ts:
            print("  WARN: 悪天予想図タイムスタンプ取得失敗")

    all_page_data = []
    total_charts  = 0

    for pg_idx, page_cfg in enumerate(pages_cfg):
        print(f"\n=== ページ {pg_idx+1} ({page_cfg.get('orientation','portrait')} "
              f"{page_cfg.get('cols',2)}×{page_cfg.get('rows',4)}) ===")
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

    print(f"\n合計: {len(pages_cfg)}ページ / {total_charts}スロット")
    return all_page_data

# ─────────────────────────────────────────────────────────────────────────
#  メール送信
# ─────────────────────────────────────────────────────────────────────────
def send_email_to(recipient, pdf_bytes, n_pages, dpi=None, size_mb=None):
    now      = datetime.datetime.utcnow()
    to_addr  = recipient["email"]
    name     = recipient.get("name", "")
    subject  = f"気象情報 {now.strftime('%Y/%m/%d %H:%MZ')} ({n_pages}p)"
    filename = f"weather_{now.strftime('%Y%m%d_%H%MZ')}.pdf"
    dpi_info = f"DPI: {dpi} / サイズ: {size_mb:.1f} MB" if dpi and size_mb else ""
    body = (
        f"航空気象情報\n"
        f"取得時刻: {now.strftime('%Y/%m/%d %H:%M')} UTC\n"
        f"PDF: {n_pages}ページ\n"
        + (f"{dpi_info}\n" if dpi_info else "")
        + f"送信先: {name} <{to_addr}>\n"
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
    print(f"  ✓ 送信完了 → {name} <{to_addr}>")

# ─────────────────────────────────────────────────────────────────────────
#  メイン
# ─────────────────────────────────────────────────────────────────────────
def save_preview_cache():
    """新しいコードの画像のみ /cache/ にコミット（既存はスキップ）"""
    import base64
    token = os.environ.get("GITHUB_TOKEN", "")
    repo  = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("  GITHUB_TOKEN/GITHUB_REPOSITORY未設定 → キャッシュスキップ")
        return

    api_hdrs = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    base_url = f"https://api.github.com/repos/{repo}/contents/cache"

    # 既存キャッシュ一覧を取得
    cr = requests.get(base_url, headers=api_hdrs, timeout=10)
    existing = set()
    if cr.status_code == 200:
        existing = {f["name"] for f in cr.json() if isinstance(f, dict) and f.get("type") == "file"}
    print(f"  既存キャッシュ: {len(existing)}件")

    # タイムスタンプを取得
    jma_ts    = find_jma_timestamp()
    akuten_ts = get_akuten_latest_ts()
    print(f"  JMA TS: {jma_ts} / 悪天TS: {akuten_ts}")

    saved = 0
    for page in CONFIG.get("pages", []):
        for slot in (page.get("slots") or []):
            if not slot: continue
            chart_type = slot.get("type", "")
            code       = slot.get("code", "")
            if not code or not chart_type: continue

            fname = f"{chart_type}_{code}.png"
            if fname in existing:
                continue  # 既存はスキップ

            print(f"  📦 新規: {fname}")
            im, _ = fetch_slot_image(slot, jma_ts, akuten_ts)
            if im is None:
                print(f"    → 取得失敗")
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
                print(f"    → 保存完了")
            else:
                print(f"    → 保存失敗: {pr.status_code}")

    print(f"  キャッシュ更新: {saved}件追加")


def main():
    recipients = CONFIG.get("recipients", [])
    enabled    = [r for r in recipients if r.get("enabled", True)]

    if not enabled:
        print("有効な受信者なし - 終了")
        sys.exit(0)

    print("=== 全有効受信者に送信 ===")
    targets = enabled

    if not targets:
        print("送信対象なし - スキップ")
        sys.exit(0)

    print(f"\n送信対象: {[r.get('name','?') for r in targets]}")

    print("\n=== 天気図収集 ===")
    all_page_data = collect_charts()

    if not all_page_data:
        print("ページデータなし - 終了")
        sys.exit(1)

    print(f"\n=== PDF生成 (DPI上限: {MAX_DPI}, サイズ上限: {MAX_MAIL_MB} MB) ===")
    pdf_bytes, n_pages, used_dpi, size_mb = build_pdf_auto_dpi(all_page_data)

    print("\n=== メール送信 ===")
    for r in targets:
        send_email_to(r, pdf_bytes, n_pages, dpi=used_dpi, size_mb=size_mb)

    print(f"\n=== 完了: {n_pages}ページ (DPI:{used_dpi} / {size_mb:.1f}MB) → {len(targets)}名に送信 ===")

    print("\n=== プレビューキャッシュ更新 ===")
    save_preview_cache()

if __name__ == "__main__":
    main()
