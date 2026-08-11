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

import os, io, re, json, time, smtplib, datetime, sys, requests
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
_pdf         = (CONFIG.get("pdf") or {})
DPI          = _pdf.get("dpi", 150)        # 後方互換用（直接使用はしない）
PAGE_MARGIN  = _pdf["page_margin"]
HEADER_H     = _pdf["header_h"]
CELL_GAP     = _pdf["cell_gap"]
LABEL_H      = _pdf.get("label_h", 50)   # 旧設定（レイアウトには未使用）
TITLE_SIZE   = float(_pdf.get("title_size", 7))  # タイトル文字サイズ(pt)
STAMP_SIZE   = float(_pdf.get("stamp_size", 7))   # スタンプ文字サイズ(pt)
STAMP_X      = float(_pdf.get("stamp_x", 25))    # スタンプ横位置(0=左端, 100=右端)
JPEG_QUALITY = _pdf.get("jpeg_quality", 90)
MAX_DPI      = _pdf.get("max_dpi", DPI)    # DPI上限
MIN_DPI      = _pdf.get("min_dpi", 72)       # DPI下限
MAX_MAIL_MB  = float(_pdf.get("max_mail_mb", 20.0))  # メールサイズ上限(MB)

# ── オーバーレイ ──────────────────────────────────────────────────────────
_ov             = (CONFIG.get("overlay") or {})
OVERLAY_ENABLED = _ov.get("enabled", True)
OVERLAY_ALPHA   = float(_ov.get("alpha", 0.2))
OVERLAY_LAYERS  = _ov.get("layers") or [{"minutes": 60, "alpha": OVERLAY_ALPHA}]
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
            "loginForm:doLogin":    "\u30ed\u30b0\u30a4\u30f3",
            "loginForm:forceflg":   "false",
            "javax.faces.ViewState": vs_m.group(1),
        }
        print(f"  ViewState取得: {len(vs_m.group(1))}文字")
        print(f"  POST送信: user={METAIR_USER[:4]}*** fields={list(data.keys())}")
        r1 = s.post(METAIR_LOGIN_URL, data=data, timeout=15, allow_redirects=True)
        print(f"  POSTステータス: {r1.status_code} url={r1.url}")
        print(f"  レスポンス先頭: {r1.text[:2000]}")
        if "login" not in r1.url.lower():
            print(f"  MetAirログイン成功: {r1.url}")
            _metair_session = s
            return s
        print(f"  MetAirログイン失敗: {r1.url}")
    except Exception as e:
        print(f"  MetAirログインエラー: {e}")
    return None

def get_csa003_image(code):
    """CSA003レーダー合成図頂高度取得 (認証不要・直接URLアクセス)
    code末尾 _NNN でN分前の画像を取得 (例: CSA003_TOPH_7_30 → 30分前)"""
    import datetime as _dt, re as _re2
    m = _re2.search(r'_(\d{2,3})$', code)
    offset_min = int(m.group(1)) if m else 0
    now = _dt.datetime.utcnow()
    for delta in range(10):
        ts_dt = now - _dt.timedelta(minutes=offset_min + delta)
        ts = ts_dt.strftime('%Y%m%d%H%M00')
        img_url = f"https://www3.metair.go.jp/pict/radar/rectp99/RECTP99_RJTD_{ts}.png"
        try:
            r = requests.get(img_url, headers=METAIR_HEADERS, timeout=15)
            if r.status_code == 200:
                im = Image.open(io.BytesIO(r.content)).convert("RGB")
                print(f"  CSA003取得成功: offset={offset_min}min ts={ts}")
                return im, ts
        except Exception:
            continue
    print(f"  CSA003取得失敗 (offset={offset_min}min)")
    return None, None
def get_font(size=36):
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", size)
    except Exception:
        return ImageFont.load_default()

def get_mono_font(size=30):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return get_font(size)

AWC_API = "https://aviationweather.gov/api/data/metar"

_METAR_CACHE = {}

def fetch_metar_text(row):
    """METAR/TAFをAWC公式APIから取得（認証不要・結果はキャッシュ）"""
    _ck = (str(row.get("ids","")).strip().upper(), int(row.get("hours",3) or 3),
           bool(row.get("metar", True)), bool(row.get("taf", True)))
    if _ck in _METAR_CACHE:
        return _METAR_CACHE[_ck]
    ids = (row.get("ids") or "").strip()
    if not ids:
        return []
    want_metar = row.get("metar", True)
    want_taf   = row.get("taf", True)
    if not want_metar and not want_taf:
        return []
    hours = int(row.get("hours", 3) or 3)
    try:
        params = {"ids": ids, "format": "raw", "taf": "true" if want_taf else "false"}
        if want_metar:
            params["hours"] = hours
        else:
            params["hours"] = 0
        r = requests.get(AWC_API, params=params, timeout=25)
        if r.status_code != 200:
            print(f"    METAR HTTP {r.status_code} [{ids}]")
            return [f"{ids}: 取得失敗 (HTTP {r.status_code})"]
        lines = [ln.rstrip() for ln in r.text.splitlines() if ln.strip()]
        if not want_metar:
            lines = [ln for ln in lines if not ln.startswith("METAR ")]
        print(f"    METAR OK [{ids}] {len(lines)}行")
        _METAR_CACHE[_ck] = lines
        return lines
    except Exception as e:
        print(f"    METARエラー [{ids}]: {e}")
        return [f"{ids}: 取得エラー"]

def build_metar_page(page_cfg, page_num, total_pages, dpi):
    """METAR/TAFを1ページに全て収める（幅はA4のまま、縦を内容に応じて伸ばす／黒地・白文字）"""
    orient = page_cfg.get("orientation", "portrait")
    if orient == "landscape":
        pw = int(297 / 25.4 * dpi); base_h = int(210 / 25.4 * dpi)
        a4_pt = (img2pdf.mm_to_pt(297), img2pdf.mm_to_pt(210))
    else:
        pw = int(210 / 25.4 * dpi); base_h = int(297 / 25.4 * dpi)
        a4_pt = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))

    rows   = page_cfg.get("metar_rows", []) or []
    blocks = []
    for row in rows:
        lines = fetch_metar_text(row)
        if lines:
            blocks.append(((row.get("ids") or "").upper(), lines))

    probe = Image.new("RGB", (8, 8))
    pdraw = ImageDraw.Draw(probe)
    max_w = pw - 2*PAGE_MARGIN - 8
    top0  = PAGE_MARGIN + int(round(STAMP_SIZE*dpi/72)) + 16

    fs = max(8, int(round(9 * dpi / 72)))
    while True:
        font = get_mono_font(fs)
        def _w(t):
            try:    return pdraw.textlength(t, font=font)
            except Exception: return len(t) * fs * 0.6
        lh = int(fs * 1.35)
        wrapped = []
        for ids, lines in blocks:
            out = []
            for ln in lines:
                s = ln
                while _w(s) > max_w and len(s) > 6:
                    cut = max(6, int(len(s) * max_w / max(_w(s), 1)))
                    out.append(s[:cut]); s = "   " + s[cut:]
                out.append(s)
            wrapped.append((ids, out))
        total_h = top0 + PAGE_MARGIN + sum((len(o) + 1) * lh + int(lh * 0.5) for _, o in wrapped)
        if total_h <= base_h * 4 or fs <= 8:
            break
        fs = max(8, int(fs * 0.85))

    ph = max(base_h, total_h)
    page_img = Image.new("RGB", (pw, ph), (0, 0, 0))
    draw     = ImageDraw.Draw(page_img)

    y = top0
    for ids, out in wrapped:
        draw.rectangle([PAGE_MARGIN, y-2, pw-PAGE_MARGIN, y+lh-2], fill=(48, 48, 52))
        draw.text((PAGE_MARGIN+6, y), ids, fill=(255, 210, 30), font=font)
        y += lh
        for ln in out:
            draw.text((PAGE_MARGIN+6, y), ln, fill=(240, 240, 240), font=font)
            y += lh
        y += int(lh * 0.5)

    now    = datetime.datetime.utcnow()
    header = f"{now.strftime('%H:%M')} UTC  {now.strftime('%m/%d/%Y')}"
    s_fs   = max(6, int(round(STAMP_SIZE * dpi / 72)))
    draw.text((int(pw * STAMP_X / 100), PAGE_MARGIN), header, fill=(235,235,235), font=get_font(s_fs))
    print(f"  METARページ: {pw}x{ph}px fs={fs} blocks={len(wrapped)}")
    return page_img, a4_pt

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
                rr = requests.head(url, headers=_hdr, timeout=6)
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

_ASHFALL_CACHE = {}

def _ashfall_batch():
    """最新発表の降灰予報PDFを全て取得し、PDF内の火山名で対応表を作る。
    ファイル名末尾の2桁は火山番号ではなく発表内の連番なので、
    毎回中身を読んで判定しないと別の火山を掴んでしまう。"""
    if _ASHFALL_CACHE:
        return _ASHFALL_CACHE
    try:
        r = requests.get(METAIR_BASE + "/metair/ajax/CSA019/ajaxUpdate",
            params={"contentsType": "2", "dbKey": "RJTD,VAFALLR", "lastDate": ""},
            headers=METAIR_HEADERS, timeout=20)
        ds = r.json().get("dataSet") or []
        if isinstance(ds, str):
            ds = json.loads(ds)
        ds = [d for d in ds if len(d.get("date", "")) == 14]
        if not ds:
            return {}
        newest = max(d["date"][:12] for d in ds)          # 最新の発表時刻
        batch  = [d for d in ds if d["date"][:12] == newest]
        import fitz
        for d in batch:
            url = METAIR_BASE + d["fname"]
            try:
                rr = requests.get(url, headers=METAIR_HEADERS, timeout=30)
                if rr.status_code != 200:
                    continue
                doc  = fitz.open(stream=rr.content, filetype="pdf")
                text = doc[0].get_text() or ""
                doc.close()
                name = None
                for v in ("阿蘇山", "桜島", "霧島山", "諏訪之瀬島", "浅間山", "十勝岳",
                          "口永良部島", "新燃岳", "雌阿寒岳", "吾妻山", "草津白根山",
                          "那須岳", "焼岳", "御嶽山", "三宅島", "薩摩硫黄島", "阿蘇"):
                    if v in text:
                        name = v
                        break
                if name:
                    _ASHFALL_CACHE[name] = (url, d["date"], rr.content)
                    print(f"    降灰予報: {d['date'][-2:]} → {name}")
            except Exception as ex:
                print(f"    降灰PDF読取失敗: {str(ex)[:60]}")
    except Exception as e:
        print(f"    降灰予報一覧エラー: {e}")
    return _ASHFALL_CACHE

def get_ashfall_latest(code):
    """降灰予報(VAFALLR)を火山名で取得。数字が来た場合は旧仕様の連番として扱う。"""
    try:
        key = str(code).strip()
        table = _ashfall_batch()
        if key.isdigit():
            # 旧設定との互換（連番指定）: 番号→名前の対応は保証されない
            print(f"    降灰予報: 番号指定[{key}]は非推奨（火山名で指定してください）")
            for name, v in table.items():
                if v[1][-2:] == key.zfill(2):
                    return v[0], v[1]
            return None, None
        hit = table.get(key)
        if not hit:
            # 「霧島山」と「新燃岳」など表記ゆれを吸収
            for name, v in table.items():
                if key in name or name in key:
                    hit = v
                    break
        if not hit:
            print(f"    降灰予報: {key} のデータなし（発表中: {', '.join(table.keys()) or 'なし'}）")
            return None, None
        return hit[0], hit[1]
    except Exception as e:
        print(f"    降灰予報エラー[{code}]: {e}")
        return None, None

IMOC_HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.imocwx.com/"}

def get_imoc_thunder(time_idx):
    """IMOC 発雷確率（GSMガイダンス）を予想時刻インデックスで取得
    ページから画像URLと対象期間を抽出する"""
    import re as _re
    try:
        t = int(time_idx)
        url = f"https://www.imocwx.com/guid.php?Type=3&Area=0&Time={t}"
        r = requests.get(url, headers=IMOC_HDR, timeout=20)
        if r.status_code != 200:
            print(f"    発雷確率: ページHTTP {r.status_code}")
            return None, None
        m = _re.search(r'<img src="(guid/[^"]+)"', r.text)
        if not m:
            print("    発雷確率: 画像URL見つからず")
            return None, None
        img_url = "https://www.imocwx.com/" + m.group(1)
        periods = _re.findall(r'<li class="active">([^<]*)</li>', r.text)
        period = periods[-1].strip() if periods else ""
        ri = requests.get(img_url, headers=IMOC_HDR, timeout=25)
        if ri.status_code != 200 or "image" not in ri.headers.get("Content-Type", ""):
            print(f"    発雷確率: 画像HTTP {ri.status_code}")
            return None, None
        im = Image.open(io.BytesIO(ri.content)).convert("RGB")
        print(f"  発雷確率取得: Time={t} {period} {im.size}")
        return im, period
    except Exception as e:
        print(f"  発雷確率エラー[{time_idx}]: {e}")
        return None, None

CWA_HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
           "Referer": "https://www.cwa.gov.tw/V8/E/W/OBS_Radar.html"}
CWA_RADAR = {
    "TW":      "CV1_TW_3600",
    "WIDE":    "CV1_3600",
    "TW_1000": "CV1_TW_3600",
    "TW_3600": "CV1_TW_3600",
    "1000":    "CV1_3600",
    "3600":    "CV1_3600",
}

def _cwa_get(url):
    """台湾CWAから画像を取得（専用ヘッダ付き）"""
    try:
        r = requests.get(url, headers=CWA_HDR, timeout=60)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print(f"    CWA取得失敗: {e}")
    return None

def _cwa_latest_ts():
    """台湾時間(UTC+8)10分刻みで存在する最新タイムスタンプを返す"""
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    now = now.replace(minute=(now.minute // 10) * 10, second=0, microsecond=0)
    for back in range(0, 13):
        dt = now - datetime.timedelta(minutes=10 * back)
        ts = dt.strftime("%Y%m%d%H%M")
        try:
            rr = requests.head("https://www.cwa.gov.tw/Data/radar/CV1_3600_" + ts + ".png",
                               headers=CWA_HDR, timeout=8)
            if rr.status_code == 200:
                return ts
        except Exception:
            pass
    return None

def get_cwa_radar(code, overlay=False):
    """台湾中央気象署(CWA)の合成レーダー画像。overlay=True で過去画像を重ねる。"""
    try:
        stem = CWA_RADAR.get(str(code))
        if not stem:
            print(f"    台湾レーダー: 未知のコード {code}")
            return None, None
        base = "https://www.cwa.gov.tw/Data/radar/"
        ts = _cwa_latest_ts()
        im = _cwa_get(base + stem + "_" + ts + ".png") if ts else None
        if im is None:
            ts = None
            im = _cwa_get(base + stem + ".png")
        if im is None:
            print(f"    台湾レーダー: 取得失敗 {code}")
            return None, None
        print(f"  台湾レーダー取得: {code} {stem} {im.size} tw{ts}")
        if overlay and ts:
            def _u(dt):
                d = dt.replace(minute=(dt.minute // 10) * 10, second=0, microsecond=0)
                return [base + stem + "_" + d.strftime("%Y%m%d%H%M") + ".png"]
            im = apply_overlay_layers(im, ts, _u, headers=CWA_HDR, fetcher=_cwa_get)
        out_ts = None
        if ts:
            out_ts = (datetime.datetime.strptime(ts, "%Y%m%d%H%M")
                      - datetime.timedelta(hours=8)).strftime("%Y%m%d%H%M%S")
        return im, out_ts
    except Exception as e:
        print(f"  台湾レーダーエラー[{code}]: {e}")
        return None, None

HKO_HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
           "Referer": "https://www.hko.gov.hk/tc/wxinfo/radars/radar.htm"}
HKO_RADAR = {
    "064": ("rad_064_png", "2d064nradar"),
    "128": ("rad_128_png", "2d128nradar"),
    "256": ("rad_256_png", "2d256nradar"),
}

def _hko_get(url):
    """香港天文台(HKO)から画像を取得"""
    try:
        r = requests.get(url, headers=HKO_HDR, timeout=30)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print(f"    HKO取得失敗: {e}")
    return None

def get_hko_radar(code, overlay=False):
    """香港天文台の気象レーダー画像(64/128/256km)。overlay=True で過去画像を重ねる。"""
    try:
        ent = HKO_RADAR.get(str(code))
        if not ent:
            print(f"    香港レーダー: 未知のコード {code}")
            return None, None
        d, pfx = ent
        base = "https://www.hko.gov.hk/wxinfo/radars/" + d + "/" + pfx + "_"
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=8)   # 香港時間
        now = now.replace(minute=(now.minute // 6) * 6, second=0, microsecond=0)
        im, ts = None, None
        for back in range(0, 12):
            dt = now - datetime.timedelta(minutes=6 * back)
            cand = dt.strftime("%Y%m%d%H%M")
            im = _hko_get(base + cand + ".jpg")
            if im:
                ts = cand
                break
        if im is None:
            print(f"    香港レーダー: 取得失敗 {code}")
            return None, None
        print(f"  香港レーダー取得: {code}km {im.size} hk{ts}")
        if overlay:
            def _u(dt):
                dd = dt.replace(minute=(dt.minute // 6) * 6, second=0, microsecond=0)
                return [base + dd.strftime("%Y%m%d%H%M") + ".jpg"]
            im = apply_overlay_layers(im, ts, _u, headers=HKO_HDR, fetcher=_hko_get)
        out_ts = (datetime.datetime.strptime(ts, "%Y%m%d%H%M")
                  - datetime.timedelta(hours=8)).strftime("%Y%m%d%H%M%S")
        return im, out_ts
    except Exception as e:
        print(f"  香港レーダーエラー[{code}]: {e}")
        return None, None

PAGASA_HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
              "X-Requested-With": "XMLHttpRequest",
              "Accept": "*/*",
              "Origin": "https://www.pagasa.dost.gov.ph",
              "Referer": "https://www.pagasa.dost.gov.ph/radar"}
# レーダーモザイク画像の地理範囲 (EPSG:4326) と画素数
PAGASA_EXT = (115.969111093, 3.80912641587, 129.511990464, 22.322581275)
PAGASA_PX  = (1020, 1393)
# 表示範囲プリセット: 西, 南, 東, 北, 出力幅, 出力高
PAGASA_VIEWS = {
    "PH":  (115.969111093, 3.80912641587, 129.511990464, 22.322581275, 1020, 1393),
    "MNL": (118.0, 11.6, 124.0, 17.6, 1100, 1100),
}
_ARCGIS_CACHE = {}
_PAGASA_FRAMES = None

def _arcgis_base(w, s, e, n, px, py_):
    """ArcGIS World_Topo_Map から EPSG:4326 の地図画像を1リクエストで取得"""
    key = f"{w},{s},{e},{n},{px},{py_}"
    if key in _ARCGIS_CACHE:
        return _ARCGIS_CACHE[key].copy()
    try:
        prm = {"bbox": f"{w},{s},{e},{n}", "bboxSR": "4326", "imageSR": "4326",
               "size": f"{px},{py_}", "format": "png", "transparent": "false", "f": "image"}
        rr = requests.get("https://services.arcgisonline.com/ArcGIS/rest/services/"
                          "World_Topo_Map/MapServer/export",
                          params=prm, headers=PAGASA_HDR, timeout=60)
        if rr.status_code != 200:
            print(f"    ArcGIS: HTTP {rr.status_code}")
            return None
        im = Image.open(io.BytesIO(rr.content)).convert("RGB")
        _ARCGIS_CACHE[key] = im
        return im.copy()
    except Exception as ex:
        print(f"    ArcGISエラー: {ex}")
        return None

def _pagasa_frames():
    """PAGASAのレーダーモザイク時系列を取得 [(フィリピン時刻datetime, url), ...]"""
    global _PAGASA_FRAMES
    if _PAGASA_FRAMES is not None:
        return _PAGASA_FRAMES
    frames = []
    try:
        data = []
        for _try in range(3):
            rr = requests.post("https://www.pagasa.dost.gov.ph/api/HybridTimeline",
                               headers=PAGASA_HDR, timeout=40)
            ct = (rr.headers.get("Content-Type") or "").split(";")[0]
            if "json" in ct and rr.text:
                data = rr.json().get("rainfall_estimate", [])
                break
            print(f"    PAGASA API 応答異常: {rr.status_code} {ct} len{len(rr.text)}")
            time.sleep(2)
        for a in data:
            u = a.get("url", "")
            m = re.search(r"_(\d{14})", u)
            if not m:
                continue
            try:
                dt = datetime.datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
            except Exception:
                continue
            frames.append((dt, u))
        frames.sort()
    except Exception as ex:
        print(f"    PAGASA時系列エラー: {ex}")
    _PAGASA_FRAMES = frames
    return frames

def _pagasa_compose(url, view):
    """レーダーオーバーレイを地図に重ねて指定範囲で切り出す"""
    w, s, e, n, ow, oh = view
    try:
        # api.meteopilipinas.gov.ph は中間CA証明書を配信しないため
        # この公開画像の取得に限り証明書検証を無効化する
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass
        rr = requests.get(url, headers=PAGASA_HDR, timeout=60, verify=False)
        if rr.status_code != 200:
            print(f"    PAGASA画像: HTTP {rr.status_code}")
            return None
        ov = Image.open(io.BytesIO(rr.content)).convert("RGBA")
    except Exception as ex:
        print(f"    PAGASA画像エラー: {ex}")
        return None
    if ov.size != PAGASA_PX:
        ov = ov.resize(PAGASA_PX, Image.LANCZOS)
    W0, S0, E0, N0 = PAGASA_EXT
    px, pyy = PAGASA_PX
    x0 = int(round((w - W0) / (E0 - W0) * px))
    x1 = int(round((e - W0) / (E0 - W0) * px))
    y0 = int(round((N0 - n) / (N0 - S0) * pyy))
    y1 = int(round((N0 - s) / (N0 - S0) * pyy))
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(px, x1), min(pyy, y1)
    ov = ov.crop((x0, y0, x1, y1)).resize((ow, oh), Image.LANCZOS)
    base = _arcgis_base(w, s, e, n, ow, oh)
    if base is None:
        base = Image.new("RGB", (ow, oh), (255, 255, 255))
    base.paste(ov, (0, 0), ov)
    return base

def get_pagasa_radar(code, overlay=False):
    """PAGASA(フィリピン気象庁)のレーダーモザイク。overlay=True で過去画像を重ねる。"""
    try:
        view = PAGASA_VIEWS.get(str(code))
        if not view:
            print(f"    マニラレーダー: 未知のコード {code}")
            return None, None
        frames = _pagasa_frames()
        if not frames:
            print("    マニラレーダー: 時系列取得失敗")
            return None, None
        by_url = {u: dt for dt, u in frames}
        base_dt, base_url = frames[-1]
        im = _pagasa_compose(base_url, view)
        if im is None:
            print(f"    マニラレーダー: 取得失敗 {code}")
            return None, None
        print(f"  マニラレーダー取得: {code} {im.size} ph{base_dt.strftime('%Y%m%d%H%M')} (frames:{len(frames)})")
        if overlay:
            def _u(dt):
                best, bd = None, None
                for fd, fu in frames:
                    diff = abs((fd - dt).total_seconds())
                    if diff <= 450 and (bd is None or diff < bd):
                        best, bd = fu, diff
                return [best] if best else []
            im = apply_overlay_layers(im, base_dt.strftime("%Y%m%d%H%M%S"), _u,
                                      headers=PAGASA_HDR,
                                      fetcher=lambda u: _pagasa_compose(u, view))
        out_ts = (base_dt - datetime.timedelta(hours=8)).strftime("%Y%m%d%H%M%S")
        return im, out_ts
    except Exception as e:
        print(f"  マニラレーダーエラー[{code}]: {e}")
        return None, None

KUMO_BASE = "https://www3.metair.go.jp/pict/satellite/hf/alt/ENJP64_RJTD_"

def _kumo_url(dt):
    """雲頂高度情報(ENJP64)のURL。5分刻み。"""
    d = dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)
    return KUMO_BASE + d.strftime("%Y%m%d%H%M00") + ".jpg"

CB_BASE = "https://www3.metair.go.jp/pict/satellite/hf/cov/ENJP61_RJTD_"

def _cb_url(dt):
    """積乱雲情報(ENJP61)のURL。5分刻み。"""
    d = dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)
    return CB_BASE + d.strftime("%Y%m%d%H%M00") + ".jpg"

def get_cb_image(code, overlay=False):
    """MetAir 積乱雲情報。code は遡る分数(0=最新, 60=1時間前, 120=2時間前)。"""
    try:
        try:
            offset = int(str(code))
        except Exception:
            offset = 0
        base_dt = datetime.datetime.utcnow() - datetime.timedelta(minutes=offset)
        im, ts = None, None
        for back in range(0, 12):
            dt = base_dt - datetime.timedelta(minutes=5 * back)
            url = _cb_url(dt)
            try:
                rr = requests.get(url, headers=METAIR_HEADERS, timeout=20)
                if rr.status_code == 200 and len(rr.content) > 2000:
                    im = Image.open(io.BytesIO(rr.content)).convert("RGB")
                    ts = url[-18:-4]
                    break
            except Exception:
                continue
        if im is None:
            print(f"    積乱雲域: 取得失敗 offset={offset}min")
            return None, None
        print(f"  積乱雲域取得: offset={offset}min {im.size} ts={ts}")
        if overlay and ts:
            im = apply_overlay_layers(im, ts, lambda d: [_cb_url(d)])
        return im, ts
    except Exception as e:
        print(f"  積乱雲域エラー[{code}]: {e}")
        return None, None

def get_kumo_image(code, overlay=False):
    """MetAir 雲頂高度情報。code は遡る分数(0=最新, 60=1時間前, 120=2時間前)。"""
    try:
        try:
            offset = int(str(code))
        except Exception:
            offset = 0
        base_dt = datetime.datetime.utcnow() - datetime.timedelta(minutes=offset)
        im, ts = None, None
        for back in range(0, 12):
            dt = base_dt - datetime.timedelta(minutes=5 * back)
            url = _kumo_url(dt)
            try:
                rr = requests.get(url, headers=METAIR_HEADERS, timeout=20)
                if rr.status_code == 200 and len(rr.content) > 2000:
                    im = Image.open(io.BytesIO(rr.content)).convert("RGB")
                    ts = url[-18:-4]
                    break
            except Exception:
                continue
        if im is None:
            print(f"    雲頂高度: 取得失敗 offset={offset}min")
            return None, None
        print(f"  雲頂高度取得: offset={offset}min {im.size} ts={ts}")
        if overlay and ts:
            im = apply_overlay_layers(im, ts, lambda d: [_kumo_url(d)])
        return im, ts
    except Exception as e:
        print(f"  雲頂高度エラー[{code}]: {e}")
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

def apply_overlay_layers(base_im, base_ts, url_fn, headers=None, fetcher=None):
    """base_im に OVERLAY_LAYERS を重ねる汎用関数。
    url_fn(dt) は datetime を受け取り候補URLのリストを返す。
    画像欠落時は5分刻みで最大30分さらに遡る。"""
    if base_im is None or not OVERLAY_ENABLED or not base_ts: return base_im
    try:
        fmt = "%Y%m%d%H%M%S" if len(base_ts)==14 else "%Y%m%d%H%M"
        base_dt = datetime.datetime.strptime(base_ts, fmt)
    except Exception:
        return base_im
    _hdr = headers or METAIR_HEADERS
    _get = fetcher or fetch_image
    result = base_im
    for ly in OVERLAY_LAYERS:
        if not ly.get("enabled", True): continue
        try:
            minutes = int(ly.get("minutes", 60))
            alpha   = float(ly.get("alpha", OVERLAY_ALPHA))
        except Exception:
            continue
        old_im = None
        tried = set()
        for extra in (0, 5, 10, 15, 20, 25, 30):
            dt_old = base_dt - datetime.timedelta(minutes=minutes+extra)
            for url in url_fn(dt_old):
                if url in tried: continue
                tried.add(url)
                try:
                    rr = requests.head(url, headers=METAIR_HEADERS, timeout=6)
                    if rr.status_code == 200:
                        old_im = _get(url)
                        if old_im:
                            print(f"  overlay OK -{minutes+extra}min alpha={alpha}")
                            break
                except Exception: pass
            if old_im: break
        if old_im:
            if old_im.size != result.size:
                old_im = old_im.resize(result.size, Image.LANCZOS)
            result = Image.blend(result, old_im, alpha=alpha)
        else:
            print(f"  overlay skip -{minutes}min: 画像なし")
    return result
def fetch_slot_image(slot, jma_ts, akuten_ts):
    """スロット定義1つ分の画像と表示ラベルを返す。slot.overlay=true なら過去レイヤーを重ねる。"""
    if slot is None:
        return None, ""
    chart_type = slot.get("type", "")
    code       = slot.get("code", "")
    label      = slot.get("label", code)
    want_ov    = bool(slot.get("overlay"))

    if chart_type in ("jma_wanlc", "jma_wanlf"):
        if not jma_ts:
            return None, label
        prefix = "WANLC" if chart_type == "jma_wanlc" else "WANLF"
        url    = f"{JMA_BASE}{prefix}{code}_RJTD_{jma_ts}.PNG"
        im     = fetch_image(url)
        if want_ov and im is not None:
            def _urls(dt):
                dt = dt.replace(minute=(dt.minute//30)*30)  # 30分グリッドに丸め
                b = dt.strftime("%Y%m%d%H%M")
                return [f"{JMA_BASE}{prefix}{code}_RJTD_{b}00.PNG",
                        f"{JMA_BASE}{prefix}{code}_RJTD_{b}.PNG"]
            im = apply_overlay_layers(im, jma_ts, _urls)
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
                im = fetch_image(url)
                dir_path = CSA019_DIR.get(code)
                if want_ov and im is not None and dir_path and ts:
                    def _urls(dt):
                        return [f"{METAIR_BASE}{dir_path}{code}_RJTD_{dt.strftime('%Y%m%d%H%M%S')}.png",
                                f"{METAIR_BASE}{dir_path}{code}_RJTD_{dt.strftime('%Y%m%d%H%M')}.png"]
                    im = apply_overlay_layers(im, ts, _urls)
                return im, f"{label}\n{ts_to_label(ts) if ts else '取得失敗'}"
            return None, label

    elif chart_type == "metair_fb_akuten":
        if not akuten_ts:
            return None, label
        url = f"{METAIR_BASE}/pict/akuten/{code}/{code}03_RJTD_{akuten_ts}.png"
        im  = fetch_image(url)
        if want_ov and im is not None:
            def _urls(dt):
                dt = dt.replace(hour=(dt.hour//3)*3, minute=0)  # 3時間グリッドに丸め
                b = dt.strftime("%Y%m%d%H%M")
                return [f"{METAIR_BASE}/pict/akuten/{code}/{code}03_RJTD_{b}00.png",
                        f"{METAIR_BASE}/pict/akuten/{code}/{code}03_RJTD_{b}.png"]
            im = apply_overlay_layers(im, akuten_ts, _urls)
        return im, f"{label}\n{ts_to_label(akuten_ts)} FT+03h"

    elif chart_type == "metair_csa003":
        im, date_str = get_csa003_image(code)
        if want_ov and im is not None and date_str:
            def _urls(dt):
                dt = dt.replace(minute=(dt.minute//5)*5)  # 5分グリッドに丸め
                return [f"https://www3.metair.go.jp/pict/radar/rectp99/RECTP99_RJTD_{dt.strftime('%Y%m%d%H%M')}00.png"]
            im = apply_overlay_layers(im, date_str, _urls)
        lbl = f"{label}\n{date_str}" if date_str else label
        return im, lbl

    elif chart_type == "imoc_thunder":
        im, period = get_imoc_thunder(code)
        return im, (f"{label}  {period}" if period else label)

    elif chart_type == "metair_cb":
        im, ts = get_cb_image(code, overlay=want_ov)
        return im, (f"{label}  {ts_to_label(ts)}" if ts else label)
    elif chart_type == "metair_kumo":
        im, ts = get_kumo_image(code, overlay=want_ov)
        return im, (f"{label}  {ts_to_label(ts)}" if ts else label)
    elif chart_type == "pagasa_radar":
        im, ts = get_pagasa_radar(code, overlay=want_ov)
        return im, (f"{label}  {ts_to_label(ts)}" if ts else label)
    elif chart_type == "pagasa_radar":
        im, ts = get_pagasa_radar(code, overlay=want_ov)
        return im, (f"{label}  {ts_to_label(ts)}" if ts else label)
    elif chart_type == "hko_radar":
        im, ts = get_hko_radar(code, overlay=want_ov)
        return im, (f"{label}  {ts_to_label(ts)}" if ts else label)
    elif chart_type == "cwa_radar":
        im, ts = get_cwa_radar(code, overlay=want_ov)
        return im, (f"{label}  {ts_to_label(ts)}" if ts else label)

    elif chart_type == "metair_ashfall":
        url, ts = get_ashfall_latest(code)
        if url:
            try:
                rr = requests.get(url, headers=METAIR_HEADERS, timeout=30)
                if rr.status_code == 200:
                    im = pdf_to_image(rr.content)
                    return im, f"{label}\n{ts_to_label(ts[:12]) if ts else '取得失敗'}"
            except Exception as e:
                print(f"  降灰予報取得エラー: {e}")
        return None, label

    elif chart_type == "metair_csa024a":
        im, ts = get_csa024a_image(code, overlay=want_ov)
        lbl = f"{label}\n{ts_to_label(ts)}" if ts else label
        return im, lbl

    return None, label

# ─────────────────────────────────────────────────────────────────────────
#  PDF生成（ページ単位レイアウト）
# ─────────────────────────────────────────────────────────────────────────
def _draw_image_in_box(page, im, label, x0, y0, box_w, box_h, dpi=300):
    """画像はマス全体に配置し、タイトルはその上に重ねて描画する。
    タイトルのサイズは画像の大きさ・位置に影響しない。"""
    draw    = ImageDraw.Draw(page)
    lines   = label.split("\n")[:1]
    max_w   = box_w - 12

    def _tw(fnt, txt):
        try:
            return draw.textlength(txt, font=fnt)
        except Exception:
            try:
                return fnt.getsize(txt)[0]
            except Exception:
                return max_w + 1

    # ── 画像をマス全体に配置（タイトルの影響を受けない） ──
    if im is not None:
        ratio = min(box_w / im.width, box_h / im.height)
        nw, nh = int(im.width * ratio), int(im.height * ratio)
        page.paste(im.resize((nw, nh), Image.LANCZOS),
                   (x0 + (box_w - nw) // 2, y0 + (box_h - nh) // 2))
    else:
        draw.text((x0+8, y0+box_h//2-12), "データなし",
                  fill=(200,200,200), font=get_font(30))
    draw.rectangle([x0, y0, x0+box_w-1, y0+box_h-1], outline=(210,210,210), width=1)

    # ── タイトルを画像の上に重ねて描画 ──
    base_fs = max(6, int(round(TITLE_SIZE * dpi / 72)))
    fs_t, font_t = base_fs, get_font(base_fs)
    for size in range(base_fs, 5, -1):
        fnt = get_font(size)
        ws = [_tw(fnt, ln) for ln in lines if ln]
        if ws and max(ws) <= max_w:
            fs_t, font_t = size, fnt
            break
    pad = max(1, fs_t // 8)
    for i, line in enumerate(lines):
        if not line: continue
        tw = _tw(font_t, line)
        row_y = y0 + i * (fs_t + pad)
        # 左上隅に密着させる（読みやすさ確保のため文字の背後だけ白地）
        draw.rectangle([x0, row_y, x0+int(tw)+pad*2, row_y+fs_t+pad], fill=(255,255,255))
        draw.text((x0, row_y), line, fill=(0,0,120), font=font_t)
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
    cell_h = (ph - 2*PAGE_MARGIN - (rows-1)*CELL_GAP) // rows

    now     = datetime.datetime.utcnow()
    header  = f"{now.strftime('%H:%M')} UTC  {now.strftime('%m/%d/%Y')}"

    page_img = Image.new("RGB", (pw, ph), (255, 255, 255))
    draw     = ImageDraw.Draw(page_img)

    for idx, (im, label) in enumerate(slot_images):
        if idx >= cols * rows:
            break
        if not label:
            continue
        if page_cfg.get("order") == "col":
            row = idx % rows
            col = idx // rows
        else:
            col = idx % cols
            row = idx // cols
        x0  = PAGE_MARGIN + col * (cell_w + CELL_GAP)
        y0  = PAGE_MARGIN + row * (cell_h + CELL_GAP)
        _draw_image_in_box(page_img, im, label, x0, y0, cell_w, cell_h, dpi)

    # スタンプ・ページ番号を最前面に描画（文字の背後だけ白地を敷く）
    s_fs   = max(6, int(round(STAMP_SIZE * dpi / 72)))
    s_font = get_font(s_fs)
    try:
        s_w = draw.textlength(header, font=s_font)
    except Exception:
        try:
            s_w = s_font.getsize(header)[0]
        except Exception:
            s_w = len(header) * s_fs * 0.6
    s_pad = max(2, s_fs // 6)
    s_x   = max(0, min(pw - int(s_w) - s_pad*2, int(pw * STAMP_X / 100)))
    draw.rectangle([s_x-s_pad, PAGE_MARGIN-s_pad,
                    s_x+int(s_w)+s_pad, PAGE_MARGIN+s_fs+s_pad], fill=(255,255,255))
    draw.text((s_x, PAGE_MARGIN), header, fill=(60,60,60), font=s_font)
    draw.rectangle([pw-PAGE_MARGIN-155, PAGE_MARGIN-3, pw-PAGE_MARGIN, PAGE_MARGIN+36], fill=(255,255,255))
    draw.text((pw-PAGE_MARGIN-150, PAGE_MARGIN),
              f"P.{page_num}/{total_pages}", fill=(130,130,130), font=get_font(30))

    return page_img, a4_pt

def build_pdf(all_page_data, dpi):
    """全ページのデータからPDFバイト列を生成する（PIL直接出力）。"""
    n_pages = len(all_page_data)
    page_images = []

    for pg_num, (page_cfg, slot_images) in enumerate(all_page_data, start=1):
        if page_cfg.get("mode") == "metar":
            page_img, _ = build_metar_page(page_cfg, pg_num, n_pages, dpi)
        else:
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
_SLOT_CACHE = {}

def fetch_slot_image_cached(slot, jma_ts, akuten_ts):
    """受信者をまたいで同じスロットを再取得しないようキャッシュする"""
    if slot is None:
        return None, ""
    try:
        ovsig = ""
        if slot.get("overlay"):
            ovsig = json.dumps([OVERLAY_ENABLED, OVERLAY_ALPHA, OVERLAY_LAYERS],
                               sort_keys=True, ensure_ascii=False)
        key = (json.dumps(slot, sort_keys=True, ensure_ascii=False), jma_ts, akuten_ts, ovsig)
    except Exception:
        return fetch_slot_image(slot, jma_ts, akuten_ts)
    if key in _SLOT_CACHE:
        return _SLOT_CACHE[key]
    v = fetch_slot_image(slot, jma_ts, akuten_ts)
    _SLOT_CACHE[key] = v
    return v

def apply_overlay_cfg(ov):
    """受信者ごとのレイヤー設定をグローバルへ反映"""
    global OVERLAY_ENABLED, OVERLAY_ALPHA, OVERLAY_LAYERS
    ov = ov or {}
    OVERLAY_ENABLED = ov.get("enabled", True)
    OVERLAY_ALPHA   = float(ov.get("alpha", 0.2))
    OVERLAY_LAYERS  = ov.get("layers") or [{"minutes": 60, "alpha": OVERLAY_ALPHA}]

def collect_charts(pages_cfg=None):
    """pages 定義を走査し、全スロットの画像を取得する。
    Returns: [(page_cfg, [(im, label), ...]), ...]"""
    if pages_cfg is None:
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
        slots      = [] if page_cfg.get("mode") == "metar" else page_cfg.get("slots", [])
        slot_images = []
        for s_idx, slot in enumerate(slots):
            if slot is None:
                slot_images.append((None, ""))
                continue
            im, label = fetch_slot_image_cached(slot, jma_ts, akuten_ts)
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


def jst_now():
    """日本標準時 (UTC+9) の現在時刻"""
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)

def find_time_slot(rcp, now_jst):
    """現在時刻(JST)が属する時間帯を返す。日をまたぐ指定(21→5時)にも対応。"""
    h = now_jst.hour
    for s in (rcp.get("time_slots") or []):
        try:
            st = int(s.get("start", 0)); en = int(s.get("end", 24))
        except Exception:
            continue
        inside = (st <= h < en) if st < en else (h >= st or h < en)
        if inside:
            return s
    return None

def should_send_now(rcp, now_jst):
    """この受信者に今送るべきか判定する。
    cron が毎時 02/17/32/47分(=15分刻み)で起動する前提で、
    JSTの0時を基点とした15分ティックが送信間隔の倍数のときだけ送る。
    Returns: (bool, 理由)"""
    slots = rcp.get("time_slots") or []
    if not slots:
        return True, "時間帯未設定のため常時送信"
    s = find_time_slot(rcp, now_jst)
    if s is None:
        return False, "時間帯外"
    try:
        iv = int(s.get("interval_minutes", 15))
    except Exception:
        iv = 15
    iv   = max(15, iv)
    tick = (now_jst.hour * 60 + now_jst.minute) // 15
    step = max(1, iv // 15)
    label = f"{s.get('start')}-{s.get('end')}時 / {iv}分間隔"
    if tick % step == 0:
        return True, label
    return False, label + " のタイミング外"

def main():
    recipients = CONFIG.get("recipients", [])
    enabled    = [r for r in recipients if r.get("enabled", True)]

    if not enabled:
        print("有効な受信者なし - 終了")
        sys.exit(0)

    event   = os.environ.get("GITHUB_EVENT_NAME", "")
    now_jst = jst_now()
    print(f"現在 JST {now_jst.strftime('%Y-%m-%d %H:%M')}  (起動: {event or 'local'})")

    if event == "schedule":
        print("=== 定時起動: 送信時間帯を判定 ===")
        targets = []
        for r in enabled:
            ok, why = should_send_now(r, now_jst)
            print(f"  {r.get('name','?')}: {'送信' if ok else 'スキップ'}  [{why}]")
            if ok:
                targets.append(r)
    else:
        print("=== 手動起動: 全有効受信者に送信 ===")
        targets = enabled

    if not targets:
        print("送信対象なし - スキップ")
        sys.exit(0)

    print(f"\n送信対象: {[r.get('name','?') for r in targets]}")

    sent = 0
    for r in targets:
        name = r.get("name", "?")
        pages_cfg = r.get("pages") or CONFIG.get("pages", [])
        if not pages_cfg:
            print(f"\n--- {name}: 天気図が未設定のためスキップ ---")
            continue
        apply_overlay_cfg(r.get("overlay") or CONFIG.get("overlay"))

        print(f"\n=== 天気図収集: {name} ===")
        all_page_data = collect_charts(pages_cfg)
        if not all_page_data:
            print(f"  {name}: ページデータなし - スキップ")
            continue

        print(f"\n=== PDF生成: {name} (DPI上限: {MAX_DPI}, サイズ上限: {MAX_MAIL_MB} MB) ===")
        pdf_bytes, n_pages, used_dpi, size_mb = build_pdf_auto_dpi(all_page_data)

        print(f"\n=== メール送信: {name} ===")
        send_email_to(r, pdf_bytes, n_pages, dpi=used_dpi, size_mb=size_mb)
        sent += 1
        print(f"--- {name}: {n_pages}ページ (DPI:{used_dpi} / {size_mb:.1f}MB) 送信完了 ---")

    print(f"\n=== 完了: {sent}名に送信 ===")

    print("\n=== プレビューキャッシュ更新 ===")
    save_preview_cache()





















def get_csa024a_image(code, overlay=False):
    """CSA024A ウィンドプロファイラ(ALWIN)最新画像取得
    フォームログイン + ajaxUpdate(dbKey="PLACE,KIND") 方式
    code形式: PLACE_KIND (例: RJAA_ALWIN1)"""
    import re as _re, os as _os
    try:
        place, kind = code.split("_", 1)
    except ValueError:
        print(f"  CSA024A: code形式不正 {code}")
        return None, None
    user = _os.environ.get("METAIR_USER", "")
    pw   = _os.environ.get("METAIR_PASS", "")
    sess = requests.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    login_url = METAIR_BASE + "/metair/view/login/index.html"
    def _vs(html):
        for m in _re.finditer(r'<input[^>]+>', html):
            inp = m.group(0)
            if "javax.faces.ViewState" in inp:
                vm = _re.search(r'value="([^"]+)"', inp)
                if vm: return vm.group(1)
        return None
    try:
        rL = sess.get(login_url, timeout=15)
        vs1 = _vs(rL.text)
        if not vs1:
            print("  CSA024A: ViewState取得失敗"); return None, None
        rP = sess.post(login_url, data={"loginForm":"loginForm","loginForm:username":user,"loginForm:password":pw,"loginForm:doLogin":"ログイン","loginForm:forceflg":"false","javax.faces.ViewState":vs1}, timeout=15, allow_redirects=True)
        if "loginForm" in rP.text:
            if "強制ログイン" not in rP.text:
                print("  CSA024A: ログイン失敗"); return None, None
            vs2 = _vs(rP.text)
            if not vs2:
                print("  CSA024A: ViewState2取得失敗"); return None, None
            rP = sess.post(login_url, data={"loginForm":"loginForm","loginForm:username":user,"loginForm:password":pw,"loginForm:doforcelogin":"force","loginForm:forceflg":"true","javax.faces.ViewState":vs2}, timeout=15, allow_redirects=True)
            if "loginForm" in rP.text:
                print("  CSA024A: 強制ログイン失敗"); return None, None
        page_url = METAIR_BASE + "/metair/view/winKobetsu/CSA024A.html"
        sess.get(page_url, params={"csid":"CSA024A","editPlace":place,"dataKindCode":kind}, timeout=20)
        ra = sess.get(METAIR_BASE + "/metair/ajax/CSA024A/ajaxUpdate",
            params={"did1":"CSA024A","dbKey":place+","+kind,"lastDate":""},
            headers={"X-Requested-With":"XMLHttpRequest"}, timeout=20)
        ds = (ra.json() or {}).get("dataSet") or []
        if not ds:
            print("  CSA024A: dataSet空"); return None, None
        latest = max(ds, key=lambda x: x.get("date",""))
        ri = sess.get(METAIR_BASE + latest["fname"], timeout=30)
        if ri.status_code == 200 and "image" in ri.headers.get("Content-Type",""):
            im = Image.open(io.BytesIO(ri.content)).convert("RGB")
            print(f"  CSA024A取得成功: {code} ts={latest.get('date')}")
            if overlay and OVERLAY_ENABLED:
                try:
                    base_dt = datetime.datetime.strptime(latest["date"], "%Y%m%d%H%M%S")
                    for ly in OVERLAY_LAYERS:
                        if not ly.get("enabled", True): continue
                        minutes = int(ly.get("minutes", 60))
                        alpha   = float(ly.get("alpha", OVERLAY_ALPHA))
                        tgt = (base_dt - datetime.timedelta(minutes=minutes)).strftime("%Y%m%d%H%M%S")
                        olds = [e for e in ds if e.get("date","") <= tgt]
                        if not olds:
                            print(f"  CSA024A overlay skip -{minutes}min"); continue
                        ent = max(olds, key=lambda x: x.get("date",""))
                        ro = sess.get(METAIR_BASE + ent["fname"], timeout=30)
                        if ro.status_code == 200 and "image" in ro.headers.get("Content-Type",""):
                            oim = Image.open(io.BytesIO(ro.content)).convert("RGB")
                            if oim.size != im.size:
                                oim = oim.resize(im.size, Image.LANCZOS)
                            im = Image.blend(im, oim, alpha=alpha)
                            print(f"  CSA024A overlay OK ts={ent.get('date')} alpha={alpha}")
                except Exception as e:
                    print(f"  CSA024A overlayエラー: {e}")
            return im, latest.get("date")
        print(f"  CSA024A: 画像DL失敗 status={ri.status_code}")
    except Exception as e:
        print(f"  CSA024Aエラー: {e}")
    return None, None

if __name__ == "__main__":
    main()
