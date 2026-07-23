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
GITHUB_EVENT = os.environ.get("GITHUB_EVENT_NAME", "schedule")

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

# ─────────────────────────────────────────────────────────────────────────
#  スケジュール判定
# ─────────────────────────────────────────────────────────────────────────
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
        print(f"    → 時間帯{i+1}({start}〜{end}時/{interval}分) {'✓送信' if ok else '✗スキップ'}")
        if ok:
            return True
    return False

# ─────────────────────────────────────────────────────────────────────────
#  画像取得ユーティリティ
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
    try:
        r = requests.get(AJAX16, headers=METAIR_HEADERS, timeout=15)
        fname = r.json()["dataSet"][0][0][0]["fname"]
        return fname.split("_RJTD_")[1].replace(".png","")
    except Exception: return None

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
    """全ページのデータからPDFバイト列を生成する。"""
    jpegs   = []
    layouts = []
    n_pages = len(all_page_data)

    for pg_num, (page_cfg, slot_images) in enumerate(all_page_data, start=1):
        page_img, a4_pt = build_one_page(page_cfg, slot_images, pg_num, n_pages, dpi)
        buf = io.BytesIO()
        page_img.save(buf, "JPEG", quality=JPEG_QUALITY, dpi=(dpi, dpi))
        jpegs.append(buf.getvalue())
        layouts.append(a4_pt)

    # 複数サイズ対応: 各ページごとに layout_fun を適用
    pdf_parts = []
    for jpeg, a4_pt in zip(jpegs, layouts):
        pdf_parts.append(img2pdf.convert(jpeg, layout_fun=img2pdf.get_layout_fun(a4_pt)))

    # 全ページを結合（PyMuPDF）
    try:
        import fitz
        doc = fitz.open()
        for part in pdf_parts:
            tmp = fitz.open(stream=part, filetype="pdf")
            doc.insert_pdf(tmp)
        return doc.tobytes(), n_pages
    except ImportError:
        # fitz なしの場合: 全ページ同一サイズとして結合（フォールバック）
        a4_pt = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))
        return img2pdf.convert(jpegs, layout_fun=img2pdf.get_layout_fun(a4_pt)), n_pages

def build_pdf_auto_dpi(all_page_data):
    """サイズ上限内で最大DPIのPDFを自動生成する。"""
    dpi_steps = [d for d in [300, 250, 216, 180, 150, 120, 96, 72] if d <= MAX_DPI]
    if not dpi_steps or dpi_steps[0] != MAX_DPI:
        dpi_steps = [MAX_DPI] + dpi_steps
    pdf_bytes, n_pages, size_mb = None, 0, 0.0
    for dpi in dpi_steps:
        print(f"  DPI {dpi} で生成中...")
        pdf_bytes, n_pages = build_pdf(all_page_data, dpi)
        size_mb = len(pdf_bytes) / (1024 * 1024)
        print(f"  → サイズ: {size_mb:.1f} MB (上限: {MAX_MAIL_MB} MB)")
        if size_mb <= MAX_MAIL_MB:
            print(f"  ✓ DPI {dpi} で送信 ({size_mb:.1f} MB)")
            return pdf_bytes, n_pages, dpi, size_mb
    print(f"  ⚠ 最小DPI({dpi_steps[-1]})でもサイズ超過 ({size_mb:.1f} MB) - そのまま送信")
    return pdf_bytes, n_pages, dpi_steps[-1], size_mb

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
def main():
    recipients = CONFIG.get("recipients", [])
    enabled    = [r for r in recipients if r.get("enabled", True)]

    if not enabled:
        print("有効な受信者なし - 終了")
        sys.exit(0)

    if GITHUB_EVENT == "workflow_dispatch":
        print("=== workflow_dispatch: 全受信者に送信 ===")
        targets = enabled
    else:
        print("=== スケジュール実行: 送信対象を判定 ===")
        targets = [r for r in enabled if should_send_to_recipient(r)]

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

if __name__ == "__main__":
    main()
