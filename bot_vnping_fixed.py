#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telebot
from telebot import types
import json, os, datetime, threading, time, random, string, requests, base64, re, subprocess, sys


# Cấu hình bí mật (gộp từ secret_config.py) — không chia sẻ
_ENC_PARTNER_ID  = "OTIzOTM4NzU2OA=="
_ENC_PARTNER_KEY = "MThlYjUyMzY2Y2IzM2FiMTdlOGY4MzNmNmExOTUzYjY="
_ENC_WALLET_ID   = "NjEwNDE1ODE4NQ=="


def _decode(value: str) -> str:
    try:
        return base64.b64decode(value.encode()).decode()
    except Exception:
        return ""


def get_the_cao_secrets():
    return (
        _decode(_ENC_PARTNER_ID),
        _decode(_ENC_PARTNER_KEY),
        _decode(_ENC_WALLET_ID),
    )


def update_secret(partner_id=None, partner_key=None, wallet_id=None):
    if partner_id:
        print(f'_ENC_PARTNER_ID  = "{base64.b64encode(partner_id.encode()).decode()}"')
    if partner_key:
        print(f'_ENC_PARTNER_KEY = "{base64.b64encode(partner_key.encode()).decode()}"')
    if wallet_id:
        print(f'_ENC_WALLET_ID   = "{base64.b64encode(wallet_id.encode()).decode()}"')


try:
    _THE_CAO_PID, _THE_CAO_KEY, _THE_CAO_WALLET = get_the_cao_secrets()
except Exception:
    _THE_CAO_PID, _THE_CAO_KEY, _THE_CAO_WALLET = "", "", ""

BOT_TOKEN  = os.getenv("BOT_TOKEN", "8637746220:AAGDcwEVyhZDHn2vcWqhmw134MEUjqXP2yY")
SUPER_ADMIN = int(os.getenv("SUPER_ADMIN", "7655649084"))
ADMIN_IDS  = [int(x) for x in os.getenv("ADMIN_IDS", "7655649084").split(",") if x.strip().isdigit()]
DATA_FILE  = os.getenv("DATA_FILE", "data_ff.json")
RENTAL_END_AT = os.getenv("RENTAL_END_AT", "")

# GÓI THUÊ BOT
RENT_BOT_PRICE = 25000
RENT_BOT_DURATION = "1 Tuần"
RENT_BOT_DESCRIPTION = (
    "🤖 Bạn sẽ được cấp một bot riêng chạy trên server của chúng tôi.\n"
    "📦 Bot có đầy đủ tính năng bán key, nạp tiền tự động (giản lược)."
)
# Thông tin ngân hàng của bot chính. Không tự chèn QR/URL lạ.
# Nếu đã có trong data_ff.json thì dữ liệu trong DATA sẽ được ưu tiên.
BANK_QR_URL = "https://ibb.co/tTwBkTmK"
BANK_ACCOUNT = os.getenv("BANK_ACCOUNT", "").strip()
BANK_ACCOUNT_NAME = "DUONG THI TU TRINH"
BANK_NAME = "MoMo"
CHANNEL_IDS = [-1003894247079]
SUPPORT    = "@ZerestMods"

THE_CAO_PARTNER  = _THE_CAO_PID
THE_CAO_KEY      = _THE_CAO_KEY
THE_CAO_WALLET   = _THE_CAO_WALLET
THE_CAO_URL      = "https://api.thesieure.com/chargingws/v2"

THE_CAO_PRICES = {
    10000:   9000,
    20000:   18000,
    30000:   27000,
    50000:   45000,
    100000:  90000,
    200000:  180000,
    300000:  270000,
    500000:  450000,
    1000000: 900000,
}

# SẢN PHẨM API FAKE LAG
FAKELAG_API_PRODUCTS = [
    {"id":"FAKELAG_1D","name":"FakeLag 1 Ngày","desc":"Key FakeLag 1 ngày","price":5000,"days":1,"api_url":"https://www.ptavqamod.x10.mx/admin.php?d=1","api_product":True},
    {"id":"FAKELAG_7D","name":"FakeLag 7 Ngày","desc":"Key FakeLag 7 ngày","price":15000,"days":7,"api_url":"https://www.ptavqamod.x10.mx/admin.php?d=7","api_product":True},
    {"id":"FAKELAG_30D","name":"FakeLag 30 Ngày","desc":"Key FakeLag 30 ngày","price":25000,"days":30,"api_url":"https://www.ptavqamod.x10.mx/admin.php?d=30","api_product":True},
]
DEFAULT_PRODUCTS = [dict(x, stock=["API_AUTO"] * 9999) for x in FAKELAG_API_PRODUCTS]

_lock = threading.Lock()

# DỮ LIỆU
def load():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            d.setdefault("users", {})
            # QUAN TRỌNG: không được reset products mỗi lần load().
            # Nếu reset ở đây thì thêm/xóa kho sẽ mất ngay sau lần đọc data tiếp theo.
            if not isinstance(d.get("products"), list):
                d["products"] = DEFAULT_PRODUCTS[:]
            elif not d["products"]:
                d["products"] = DEFAULT_PRODUCTS[:]
            d.setdefault("orders", [])
            d.setdefault("deposits", [])
            d.setdefault("the_cao_orders", [])
            d.setdefault("rental_orders", [])
            d.setdefault("rent_counter", 0)
            d.setdefault("dep_counter", 0)
            d.setdefault("ord_counter", 0)
            d.setdefault("the_counter", 0)
            d.setdefault("states", {})
            d.setdefault("admins", ADMIN_IDS[:])
            d.setdefault("banned_admins", [])
            d.setdefault("banned_users", [])      # user bị ban hẳn (không thể /start)
            d.setdefault("blocked_users", [])     # user bị cấm dùng bot (vẫn /start được nhưng không thao tác)
            d.setdefault("banned_ips", [])        # danh sách IP bị chặn (thủ công, không tự phát hiện vì Telegram không lộ IP)
            d.setdefault("bank_config", {
                "qr_url": BANK_QR_URL,
                "account": BANK_ACCOUNT,
                "account_name": BANK_ACCOUNT_NAME,
                "bank_name": BANK_NAME,
            })
            if not isinstance(d.get("bank_config"), dict):
                d["bank_config"] = {}
            d["bank_config"].setdefault("qr_url", BANK_QR_URL)
            d["bank_config"].setdefault("account", BANK_ACCOUNT)
            d["bank_config"].setdefault("account_name", BANK_ACCOUNT_NAME)
            d["bank_config"].setdefault("bank_name", BANK_NAME)
            return d
        except Exception:
            pass
    return {
        "users": {}, "products": DEFAULT_PRODUCTS[:],
        "orders": [], "deposits": [], "the_cao_orders": [], "rental_orders": [],
        "rent_counter": 0, "dep_counter": 0, "ord_counter": 0, "the_counter": 0,
        "states": {}, "admins": ADMIN_IDS[:], "banned_admins": [],
        "banned_users": [], "blocked_users": [], "banned_ips": [],
        "bank_config": {
            "qr_url": BANK_QR_URL,
            "account": BANK_ACCOUNT,
            "account_name": BANK_ACCOUNT_NAME,
            "bank_name": BANK_NAME,
        }
    }

def save(d):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

def get_user(d, uid):
    k = str(uid)
    if k not in d["users"]:
        d["users"][k] = {
            "balance": 0, "name": "", "username": "",
            "join_date": now(), "orders": []
        }
    return d["users"][k]

def get_bank_config(d=None):
    """Lấy thông tin ngân hàng từ DATA.
    Bot mẹ: fallback về constants cố định.
    Bot thuê (RENTAL_CHILD=1): fallback về ENV vars do bot mẹ truyền vào.
    """
    if d is None:
        d = load()
    cfg = d.get("bank_config", {})
    if not isinstance(cfg, dict):
        cfg = {}
    if os.getenv("RENTAL_CHILD") == "1":
        fb_qr   = os.getenv("BANK_QR_URL", "").strip()
        fb_acc  = os.getenv("BANK_ACCOUNT", "").strip()
        fb_name = os.getenv("BANK_ACCOUNT_NAME", "").strip()
        fb_bank = os.getenv("BANK_NAME", "").strip()
    else:
        fb_qr   = BANK_QR_URL
        fb_acc  = BANK_ACCOUNT
        fb_name = BANK_ACCOUNT_NAME
        fb_bank = BANK_NAME
    return {
        "qr_url":       str(cfg.get("qr_url")       or fb_qr   or "").strip(),
        "account":      str(cfg.get("account")       or fb_acc  or "").strip(),
        "account_name": str(cfg.get("account_name")  or fb_name or "").strip(),
        "bank_name":    str(cfg.get("bank_name")     or fb_bank or "").strip(),
    }


def set_bank_config(d, qr_url=None, account=None, account_name=None, bank_name=None):
    cfg = d.setdefault("bank_config", {})
    if qr_url is not None: cfg["qr_url"] = str(qr_url).strip()
    if account is not None: cfg["account"] = str(account).strip()
    if account_name is not None: cfg["account_name"] = str(account_name).strip()
    if bank_name is not None: cfg["bank_name"] = str(bank_name).strip()
    return cfg


def find_product(d, pid):
    return next((p for p in d["products"] if p["id"] == pid), None)

def fmt(n):
    return f"{int(n):,}đ".replace(",", ".")

def now():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def rand_code(n=6):
    return "".join(random.choices(string.digits, k=n))

def mixed_id(d, prefix, field="id", length=7):
    """Tạo mã đơn gồm cả chữ và số, không trùng mã cũ."""
    existing = {str(x.get(field, "")).upper() for x in (d.get("orders", []) + d.get("deposits", []) + d.get("the_cao_orders", []) + d.get("rental_orders", [])) if isinstance(x, dict)}
    alphabet = string.ascii_uppercase + string.digits
    while True:
        # Luôn có ít nhất 1 chữ và 1 số sau prefix, tránh mã kiểu toàn số.
        tail = [random.choice(string.ascii_uppercase), random.choice(string.digits)]
        tail += [random.choice(alphabet) for _ in range(max(0, length - 2))]
        random.shuffle(tail)
        code = prefix.upper() + "".join(tail)
        if code not in existing:
            return code

def is_admin(uid):
    uid = int(uid)
    if uid == SUPER_ADMIN:
        return True
    d = load()
    return uid in d.get("admins", ADMIN_IDS) and uid not in d.get("banned_admins", [])

def is_super(uid):
    return int(uid) == SUPER_ADMIN

def get_admin_list():
    d = load()
    admins = set(d.get("admins", ADMIN_IDS))
    banned = set(d.get("banned_admins", []))
    admins -= banned
    admins.add(SUPER_ADMIN)
    return list(admins)

def is_user_banned(uid):
    d = load()
    return str(uid) in d.get("banned_users", [])

def is_user_blocked(uid):
    d = load()
    return str(uid) in d.get("blocked_users", [])

def guard(msg):
    uid = msg.from_user.id
    if is_user_banned(uid):
        try:
            bot.send_message(uid, f"🚫 *Tài khoản của bạn đã bị BAN vĩnh viễn khỏi bot!*\n\nLiên hệ {SUPPORT} nếu có thắc mắc.", parse_mode="Markdown")
        except Exception:
            pass
        return True
    if is_user_blocked(uid):
        try:
            bot.send_message(uid, f"⛔ *Tài khoản của bạn đang bị TẠM CẤM sử dụng bot!*\n\nLiên hệ {SUPPORT} để được hỗ trợ gỡ cấm.", parse_mode="Markdown")
        except Exception:
            pass
        return True
    return False

def post_new_stock_to_channel(product, added_qty, total_qty):
    if not CHANNEL_IDS:
        return
    icon = "🟢" if total_qty > 0 else "🔴"
    # Escape ký tự đặc biệt Markdown (_ * [ ] ( ) ~ ` > # + - = | { } . !)
    # để tránh lỗi "can't find end of entity" khi tên sản phẩm/bot có dấu _ hoặc *
    def esc(s):
        for ch in ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]:
            s = str(s).replace(ch, "\\" + ch)
        return s

    text = (
        f"🆕 *THÔNG BÁO CÓ HÀNG MỚI*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎮 Sản phẩm: *{esc(product['name'])}*\n"
        f"➕ Đã thêm: *{added_qty}*\n"
        f"{icon} Kho hiện tại: *{total_qty}*\n"
        f"💰 Giá: *{esc(fmt(product['price']))}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👉 Bấm Để Mua Acc: [*Click*](https://t.me/HikaNewBot_Bot)"
    )

    for cid in CHANNEL_IDS:
        try:
            bot.send_message(cid, text, parse_mode="MarkdownV2", disable_web_page_preview=True)
        except Exception as e:
            for aid in get_admin_list():
                try:
                    bot.send_message(aid, f"⚠️ Lỗi gửi thông báo lên kênh {cid}: {e}")
                except Exception:
                    pass

# Chống spam tin nhắn / ảnh
_msg_rate = {}      # {uid: [timestamps]}
_photo_rate = {}     # {uid: [timestamps]}

def is_msg_spam(uid, limit=6, window=8):
    now_ts = time.time()
    hist = _msg_rate.setdefault(uid, [])
    hist[:] = [t for t in hist if now_ts - t < window]
    hist.append(now_ts)
    return len(hist) > limit

def is_photo_spam(uid, limit=4, window=15):
    now_ts = time.time()
    hist = _photo_rate.setdefault(uid, [])
    hist[:] = [t for t in hist if now_ts - t < window]
    hist.append(now_ts)
    return len(hist) > limit

# Kiểm tra ảnh có khả năng là bill MoMo hay không (OCR nhẹ, có fallback an toàn)
try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except Exception:
    _OCR_AVAILABLE = False

BILL_KEYWORDS = [
    "momo", "chuyển tiền", "chuyen tien", "giao dịch", "giao dich",
    "số tiền", "so tien", "nội dung", "noi dung", "thành công", "thanh cong",
    "ck", "napas", "vietqr", "ngân hàng", "ngan hang", "biên lai", "bien lai",
]

def looks_like_bill(file_path):
    try:
        if _OCR_AVAILABLE:
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img, lang="vie+eng").lower()
            text = text.replace(" ", "")
            hit = any(kw.replace(" ", "") in text for kw in BILL_KEYWORDS)
            if hit:
                return True, "ocr_match"
            return False, "ocr_no_match"
        else:
            # Fallback: chỉ kiểm tra hình dạng ảnh (screenshot MoMo thường là ảnh dọc, cao > rộng)
            from PIL import Image as _Image
            img = _Image.open(file_path)
            w, h = img.size
            if h > w * 1.15:  # ảnh dọc rõ ràng, giống screenshot điện thoại
                return True, "shape_ok"
            return False, "shape_suspicious"
    except Exception:
        # Không đọc được ảnh (lỗi thư viện, file hỏng...) — không chặn oan, để admin tự xem xét
        return True, "check_skipped"

def expires_at_days(days):
    return (datetime.datetime.now() + datetime.timedelta(days=int(days))).isoformat(timespec="seconds")

def key_expired(order):
    try:
        return datetime.datetime.now() >= datetime.datetime.fromisoformat(order["expires_at"])
    except Exception:
        return True

def remaining_text(order):
    try:
        sec = int((datetime.datetime.fromisoformat(order["expires_at"]) - datetime.datetime.now()).total_seconds())
        if sec <= 0: return "Expired"
        days, rem = divmod(sec, 86400); hours, rem = divmod(rem, 3600); mins = rem // 60
        return f"{days}d {hours}h {mins}m"
    except Exception:
        return "N/A"

# BOT
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None, threaded=False)

# KEYBOARDS
def create_fakelag_key(product):
    """Call the FakeLag server. The API response body is the real key."""
    url = str(product.get("api_url", "")).strip()
    if not url:
        raise RuntimeError("API URL chưa được cấu hình / API URL is not configured")
    try:
        response = requests.get(
            url, timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (TelegramBot)"}
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"API connection failed: {exc}")
    key = response.text.strip()
    if not key:
        raise RuntimeError("Server API returned no key")
    return key

def kb_main(uid=None):
    # MENU CHÍNH CHỈ TIẾNG VIỆT.
    # Bot thuê không được có nút "Thuê Bot" của bot mẹ.
    k = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    k.add("💰 Nạp tiền", "👜 Số dư")
    k.add("🛒 Mua hàng", "📦 Đơn của tôi")
    if os.getenv("RENTAL_CHILD") != "1":
        k.add("🤖 Thuê Bot", "❓ Hướng dẫn")
    else:
        k.add("❓ Hướng dẫn")
    return k

def kb_admin():
    k = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    k.add("➕ Thêm hàng", "📋 Quản lý hàng",
          "⏳ Lệnh nạp chờ", "📊 Thống kê",
          "📢 Thông báo", "👥 Danh sách user",
          "👑 Quản lý admin", "🚫 Ban / Chặn User",
          "🏠 Main")
    return k

def kb_huy(uid=None):
    # Chỉ dùng tiếng Việt; không còn chức năng chuyển ngôn ngữ trong menu.
    k = types.ReplyKeyboardMarkup(resize_keyboard=True)
    k.add("❌ Hủy")
    return k


def kb_rent_bot():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton(
        "📅 1 Tuần - 25.000đ", callback_data="RENT|1W"
    ))
    kb.add(types.InlineKeyboardButton("❌ Hủy", callback_data="RENT_CANCEL"))
    return kb


def validate_telegram_bot_token(token):
    try:
        r=requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=15)
        data=r.json()
        return bool(data.get("ok")), data.get("result", {})
    except Exception:
        return False, {}

def launch_rental_bot(token, admin_id, rent_id, days=7, expires_at=None, bank=None):
    # Dùng hạn thuê đã lưu trong DATA, không tính lại 7 ngày khi restart.
    end_at = expires_at or (datetime.datetime.now()+datetime.timedelta(days=days)).isoformat(timespec="seconds")
    bank = bank or {}
    env=os.environ.copy()
    env.update({
        "BOT_TOKEN": token,
        "SUPER_ADMIN": str(admin_id),
        "ADMIN_IDS": str(admin_id),
        "DATA_FILE": f"rental_{rent_id}.json",
        "RENTAL_END_AT": end_at,
        "RENTAL_CHILD": "1",
        "BANK_QR_URL": str(bank.get("qr_url", "")).strip(),
        "BANK_ACCOUNT": str(bank.get("account", "")).strip(),
        "BANK_ACCOUNT_NAME": str(bank.get("account_name", "")).strip(),
        "BANK_NAME": str(bank.get("bank_name", "")).strip(),
    })
    return subprocess.Popen([sys.executable, os.path.abspath(__file__)], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def process_alive(pid):
    try:
        pid = int(pid)
        if pid <= 0: return False
        os.kill(pid, 0)
        return True
    except Exception:
        return False

def rental_text(uid=None):
    return (
        "*🤖 DỊCH VỤ THUÊ BOT*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🤖 *Bạn sẽ được cấp một bot riêng chạy trên server của chúng tôi.*\n"
        "📦 *Bot có đầy đủ tính năng bán key, nạp tiền tự động (giản lược).*\n"
        "💰 *Giá thuê theo tuần: 25.000đ*\n"
        "📌 *Sau khi thanh toán, vui lòng cung cấp:*\n"
        "   • *Token Bot của bạn*\n"
        "   • *ID Admin của bạn*\n"
        "   • *QR Url*\n"
        "   • *Số tài khoản*\n"
        "   • *Tên Tài Khoản*\n"
        "   • *Tên Ngân Hàng*\n"
        "   • *Bot sẽ được tự động cài đặt và chạy.*\n"
        "\n"
        "*Chọn gói thuê bên dưới:*"
    )

def kb_shop(products, balance):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for p in products:
        if p.get("api_product"):
            kb.add(types.InlineKeyboardButton(f" {p['name']} • {fmt(p['price'])}", callback_data=f"VIEW|{p['id']}"))
        else:
            qty = len(p.get("stock", []))
            icon = "✅" if qty > 0 else "❌"
            kb.add(types.InlineKeyboardButton(f"{icon}  {p['name']}  •  {fmt(p['price'])}  •  Còn {qty}", callback_data=f"VIEW|{p['id']}"))
    kb.add(types.InlineKeyboardButton("🏠 Quay lại Menu", callback_data="MAIN"))
    return kb

def kb_confirm_buy(pid):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ Xác nhận mua", callback_data=f"BUY|{pid}"),
        types.InlineKeyboardButton("↩️ Quay lại", callback_data="SHOP")
    )
    return kb

def kb_the_cao():
    kb = types.InlineKeyboardMarkup(row_width=2)
    for nha_mang in ["VIETTEL", "VINAPHONE", "MOBIFONE", "ZING", "GARENA"]:
        kb.add(types.InlineKeyboardButton(
            f"📱 {nha_mang}", callback_data=f"THE|{nha_mang}"
        ))
    kb.add(types.InlineKeyboardButton("🏠 Quay lại", callback_data="MAIN"))
    return kb

def kb_menh_gia(nha_mang):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for mg, gia_thu in THE_CAO_PRICES.items():
        kb.add(types.InlineKeyboardButton(
            f"{fmt(mg)} → Nạp {fmt(gia_thu)}",
            callback_data=f"MG|{nha_mang}|{mg}"
        ))
    kb.add(types.InlineKeyboardButton("↩️ Quay lại", callback_data="THE_MENU"))
    return kb

def main_shop_text(uid, name=None, balance=None):
    if name is None:
        name = ""
    if balance is None:
        with _lock:
            d = load()
            u = get_user(d, uid)
            balance = u.get("balance", 0)
    return (
        f"*🏪 SHOP HACK FREEFIRE*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👋 Xin chào *{name}*\n"
        f"👜 Số dư: *{fmt(balance)}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔰 *Bảo mật - Chất lượng - An toàn*\n"
        f"⚡ *Giao hàng tự động 24/7*\n\n"
        f"✨ Chọn chức năng bên dưới 👇"
    )



# 🤖 THUÊ BOT
@bot.message_handler(func=lambda m: m.text == "🤖 Thuê Bot")
def thue_bot(msg

try:
    _THE_CAO_PID, _THE_CAO_KEY, _THE_CAO_WALLET = get_the_cao_secrets()
except Exception:
    _THE_CAO_PID, _THE_CAO_KEY, _THE_CAO_WALLET = "", "", ""

BOT_TOKEN  = os.getenv("BOT_TOKEN", "8637746220:AAGDcwEVyhZDHn2vcWqhmw134MEUjqXP2yY")
SUPER_ADMIN = int(os.getenv("SUPER_ADMIN", "7655649084"))
ADMIN_IDS  = [int(x) for x in os.getenv("ADMIN_IDS", "7655649084").split(",") if x.strip().isdigit()]
DATA_FILE  = os.getenv("DATA_FILE", "data_ff.json")
RENTAL_END_AT = os.getenv("RENTAL_END_AT", "")

# GÓI THUÊ BOT
RENT_BOT_PRICE = 25000
RENT_BOT_DURATION = "1 Tuần"
RENT_BOT_DESCRIPTION = (
    "🤖 Bạn sẽ được cấp một bot riêng chạy trên server của chúng tôi.\n"
    "📦 Bot có đầy đủ tính năng bán key, nạp tiền tự động (giản lược)."
)
# Thông tin ngân hàng của bot chính. Không tự chèn QR/URL lạ.
# Nếu đã có trong data_ff.json thì dữ liệu trong DATA sẽ được ưu tiên.
BANK_QR_URL = "https://ibb.co/tTwBkTmK"
BANK_ACCOUNT = os.getenv("BANK_ACCOUNT", "").strip()
BANK_ACCOUNT_NAME = "DUONG THI TU TRINH"
BANK_NAME = "MoMo"
CHANNEL_IDS = [-1003894247079]
SUPPORT    = "@ZerestMods"

THE_CAO_PARTNER  = _THE_CAO_PID
THE_CAO_KEY      = _THE_CAO_KEY
THE_CAO_WALLET   = _THE_CAO_WALLET
THE_CAO_URL      = "https://api.thesieure.com/chargingws/v2"

THE_CAO_PRICES = {
    10000:   9000,
    20000:   18000,
    30000:   27000,
    50000:   45000,
    100000:  90000,
    200000:  180000,
    300000:  270000,
    500000:  450000,
    1000000: 900000,
}

# SẢN PHẨM API FAKE LAG
FAKELAG_API_PRODUCTS = [
    {"id":"FAKELAG_1D","name":"FakeLag 1 Ngày","desc":"Key FakeLag 1 ngày","price":15000,"days":1,"api_url":"https://www.ptavqamod.x10.mx/admin.php?d=1","api_product":True},
    {"id":"FAKELAG_7D","name":"FakeLag 7 Ngày","desc":"Key FakeLag 7 ngày","price":25000,"days":7,"api_url":"https://www.ptavqamod.x10.mx/admin.php?d=7","api_product":True},
    {"id":"FAKELAG_30D","name":"FakeLag 30 Ngày","desc":"Key FakeLag 30 ngày","price":50000,"days":30,"api_url":"https://www.ptavqamod.x10.mx/admin.php?d=30","api_product":True},
]
DEFAULT_PRODUCTS = [dict(x, stock=["API_AUTO"] * 9999) for x in FAKELAG_API_PRODUCTS]

_lock = threading.Lock()

# DỮ LIỆU
def load():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            d.setdefault("users", {})
            # QUAN TRỌNG: không được reset products mỗi lần load().
            # Nếu reset ở đây thì thêm/xóa kho sẽ mất ngay sau lần đọc data tiếp theo.
            if not isinstance(d.get("products"), list):
                d["products"] = DEFAULT_PRODUCTS[:]
            elif not d["products"]:
                d["products"] = DEFAULT_PRODUCTS[:]
            d.setdefault("orders", [])
            d.setdefault("deposits", [])
            d.setdefault("the_cao_orders", [])
            d.setdefault("rental_orders", [])
            d.setdefault("rent_counter", 0)
            d.setdefault("dep_counter", 0)
            d.setdefault("ord_counter", 0)
            d.setdefault("the_counter", 0)
            d.setdefault("states", {})
            d.setdefault("admins", ADMIN_IDS[:])
            d.setdefault("banned_admins", [])
            d.setdefault("banned_users", [])      # user bị ban hẳn (không thể /start)
            d.setdefault("blocked_users", [])     # user bị cấm dùng bot (vẫn /start được nhưng không thao tác)
            d.setdefault("banned_ips", [])        # danh sách IP bị chặn (thủ công, không tự phát hiện vì Telegram không lộ IP)
            d.setdefault("bank_config", {
                "qr_url": BANK_QR_URL,
                "account": BANK_ACCOUNT,
                "account_name": BANK_ACCOUNT_NAME,
                "bank_name": BANK_NAME,
            })
            if not isinstance(d.get("bank_config"), dict):
                d["bank_config"] = {}
            d["bank_config"].setdefault("qr_url", BANK_QR_URL)
            d["bank_config"].setdefault("account", BANK_ACCOUNT)
            d["bank_config"].setdefault("account_name", BANK_ACCOUNT_NAME)
            d["bank_config"].setdefault("bank_name", BANK_NAME)
            return d
        except Exception:
            pass
    return {
        "users": {}, "products": DEFAULT_PRODUCTS[:],
        "orders": [], "deposits": [], "the_cao_orders": [], "rental_orders": [],
        "rent_counter": 0, "dep_counter": 0, "ord_counter": 0, "the_counter": 0,
        "states": {}, "admins": ADMIN_IDS[:], "banned_admins": [],
        "banned_users": [], "blocked_users": [], "banned_ips": [],
        "bank_config": {
            "qr_url": BANK_QR_URL,
            "account": BANK_ACCOUNT,
            "account_name": BANK_ACCOUNT_NAME,
            "bank_name": BANK_NAME,
        }
    }

def save(d):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

def get_user(d, uid):
    k = str(uid)
    if k not in d["users"]:
        d["users"][k] = {
            "balance": 0, "name": "", "username": "",
            "join_date": now(), "orders": []
        }
    return d["users"][k]

def get_bank_config(d=None):
    """Lấy thông tin ngân hàng từ DATA.
    Bot mẹ: fallback về constants cố định.
    Bot thuê (RENTAL_CHILD=1): fallback về ENV vars do bot mẹ truyền vào.
    """
    if d is None:
        d = load()
    cfg = d.get("bank_config", {})
    if not isinstance(cfg, dict):
        cfg = {}
    if os.getenv("RENTAL_CHILD") == "1":
        fb_qr   = os.getenv("BANK_QR_URL", "").strip()
        fb_acc  = os.getenv("BANK_ACCOUNT", "").strip()
        fb_name = os.getenv("BANK_ACCOUNT_NAME", "").strip()
        fb_bank = os.getenv("BANK_NAME", "").strip()
    else:
        fb_qr   = BANK_QR_URL
        fb_acc  = BANK_ACCOUNT
        fb_name = BANK_ACCOUNT_NAME
        fb_bank = BANK_NAME
    return {
        "qr_url":       str(cfg.get("qr_url")       or fb_qr   or "").strip(),
        "account":      str(cfg.get("account")       or fb_acc  or "").strip(),
        "account_name": str(cfg.get("account_name")  or fb_name or "").strip(),
        "bank_name":    str(cfg.get("bank_name")     or fb_bank or "").strip(),
    }


def set_bank_config(d, qr_url=None, account=None, account_name=None, bank_name=None):
    cfg = d.setdefault("bank_config", {})
    if qr_url is not None: cfg["qr_url"] = str(qr_url).strip()
    if account is not None: cfg["account"] = str(account).strip()
    if account_name is not None: cfg["account_name"] = str(account_name).strip()
    if bank_name is not None: cfg["bank_name"] = str(bank_name).strip()
    return cfg


def find_product(d, pid):
    return next((p for p in d["products"] if p["id"] == pid), None)

def fmt(n):
    return f"{int(n):,}đ".replace(",", ".")

def now():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def rand_code(n=6):
    return "".join(random.choices(string.digits, k=n))

def mixed_id(d, prefix, field="id", length=7):
    """Tạo mã đơn gồm cả chữ và số, không trùng mã cũ."""
    existing = {str(x.get(field, "")).upper() for x in (d.get("orders", []) + d.get("deposits", []) + d.get("the_cao_orders", []) + d.get("rental_orders", [])) if isinstance(x, dict)}
    alphabet = string.ascii_uppercase + string.digits
    while True:
        # Luôn có ít nhất 1 chữ và 1 số sau prefix, tránh mã kiểu toàn số.
        tail = [random.choice(string.ascii_uppercase), random.choice(string.digits)]
        tail += [random.choice(alphabet) for _ in range(max(0, length - 2))]
        random.shuffle(tail)
        code = prefix.upper() + "".join(tail)
        if code not in existing:
            return code

def is_admin(uid):
    uid = int(uid)
    if uid == SUPER_ADMIN:
        return True
    d = load()
    return uid in d.get("admins", ADMIN_IDS) and uid not in d.get("banned_admins", [])

def is_super(uid):
    return int(uid) == SUPER_ADMIN

def get_admin_list():
    d = load()
    admins = set(d.get("admins", ADMIN_IDS))
    banned = set(d.get("banned_admins", []))
    admins -= banned
    admins.add(SUPER_ADMIN)
    return list(admins)

def is_user_banned(uid):
    d = load()
    return str(uid) in d.get("banned_users", [])

def is_user_blocked(uid):
    d = load()
    return str(uid) in d.get("blocked_users", [])

def guard(msg):
    uid = msg.from_user.id
    if is_user_banned(uid):
        try:
            bot.send_message(uid, f"🚫 *Tài khoản của bạn đã bị BAN vĩnh viễn khỏi bot!*\n\nLiên hệ {SUPPORT} nếu có thắc mắc.", parse_mode="Markdown")
        except Exception:
            pass
        return True
    if is_user_blocked(uid):
        try:
            bot.send_message(uid, f"⛔ *Tài khoản của bạn đang bị TẠM CẤM sử dụng bot!*\n\nLiên hệ {SUPPORT} để được hỗ trợ gỡ cấm.", parse_mode="Markdown")
        except Exception:
            pass
        return True
    return False

def post_new_stock_to_channel(product, added_qty, total_qty):
    if not CHANNEL_IDS:
        return
    icon = "🟢" if total_qty > 0 else "🔴"
    # Escape ký tự đặc biệt Markdown (_ * [ ] ( ) ~ ` > # + - = | { } . !)
    # để tránh lỗi "can't find end of entity" khi tên sản phẩm/bot có dấu _ hoặc *
    def esc(s):
        for ch in ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]:
            s = str(s).replace(ch, "\\" + ch)
        return s

    text = (
        f"🆕 *THÔNG BÁO CÓ HÀNG MỚI*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎮 Sản phẩm: *{esc(product['name'])}*\n"
        f"➕ Đã thêm: *{added_qty}*\n"
        f"{icon} Kho hiện tại: *{total_qty}*\n"
        f"💰 Giá: *{esc(fmt(product['price']))}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👉 Bấm Để Mua Acc: [*Click*](https://t.me/HikaNewBot_Bot)"
    )

    for cid in CHANNEL_IDS:
        try:
            bot.send_message(cid, text, parse_mode="MarkdownV2", disable_web_page_preview=True)
        except Exception as e:
            for aid in get_admin_list():
                try:
                    bot.send_message(aid, f"⚠️ Lỗi gửi thông báo lên kênh {cid}: {e}")
                except Exception:
                    pass

# Chống spam tin nhắn / ảnh
_msg_rate = {}      # {uid: [timestamps]}
_photo_rate = {}     # {uid: [timestamps]}

def is_msg_spam(uid, limit=6, window=8):
    now_ts = time.time()
    hist = _msg_rate.setdefault(uid, [])
    hist[:] = [t for t in hist if now_ts - t < window]
    hist.append(now_ts)
    return len(hist) > limit

def is_photo_spam(uid, limit=4, window=15):
    now_ts = time.time()
    hist = _photo_rate.setdefault(uid, [])
    hist[:] = [t for t in hist if now_ts - t < window]
    hist.append(now_ts)
    return len(hist) > limit

# Kiểm tra ảnh có khả năng là bill MoMo hay không (OCR nhẹ, có fallback an toàn)
try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except Exception:
    _OCR_AVAILABLE = False

BILL_KEYWORDS = [
    "momo", "chuyển tiền", "chuyen tien", "giao dịch", "giao dich",
    "số tiền", "so tien", "nội dung", "noi dung", "thành công", "thanh cong",
    "ck", "napas", "vietqr", "ngân hàng", "ngan hang", "biên lai", "bien lai",
]

def looks_like_bill(file_path):
    try:
        if _OCR_AVAILABLE:
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img, lang="vie+eng").lower()
            text = text.replace(" ", "")
            hit = any(kw.replace(" ", "") in text for kw in BILL_KEYWORDS)
            if hit:
                return True, "ocr_match"
            return False, "ocr_no_match"
        else:
            # Fallback: chỉ kiểm tra hình dạng ảnh (screenshot MoMo thường là ảnh dọc, cao > rộng)
            from PIL import Image as _Image
            img = _Image.open(file_path)
            w, h = img.size
            if h > w * 1.15:  # ảnh dọc rõ ràng, giống screenshot điện thoại
                return True, "shape_ok"
            return False, "shape_suspicious"
    except Exception:
        # Không đọc được ảnh (lỗi thư viện, file hỏng...) — không chặn oan, để admin tự xem xét
        return True, "check_skipped"

def expires_at_days(days):
    return (datetime.datetime.now() + datetime.timedelta(days=int(days))).isoformat(timespec="seconds")

def key_expired(order):
    try:
        return datetime.datetime.now() >= datetime.datetime.fromisoformat(order["expires_at"])
    except Exception:
        return True

def remaining_text(order):
    try:
        sec = int((datetime.datetime.fromisoformat(order["expires_at"]) - datetime.datetime.now()).total_seconds())
        if sec <= 0: return "Expired"
        days, rem = divmod(sec, 86400); hours, rem = divmod(rem, 3600); mins = rem // 60
        return f"{days}d {hours}h {mins}m"
    except Exception:
        return "N/A"

# BOT
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None, threaded=False)

# KEYBOARDS
def create_fakelag_key(product):
    """Call the FakeLag server. The API response body is the real key."""
    url = str(product.get("api_url", "")).strip()
    if not url:
        raise RuntimeError("API URL chưa được cấu hình / API URL is not configured")
    try:
        response = requests.get(
            url, timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (TelegramBot)"}
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"API connection failed: {exc}")
    key = response.text.strip()
    if not key:
        raise RuntimeError("Server API returned no key")
    return key

def kb_main(uid=None):
    # MENU CHÍNH CHỈ TIẾNG VIỆT.
    # Bot thuê không được có nút "Thuê Bot" của bot mẹ.
    k = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    k.add("💰 Nạp tiền", "👜 Số dư")
    k.add("🛒 Mua hàng", "📦 Đơn của tôi")
    if os.getenv("RENTAL_CHILD") != "1":
        k.add("🤖 Thuê Bot", "❓ Hướng dẫn")
    else:
        k.add("❓ Hướng dẫn")
    return k

def kb_admin():
    k = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    k.add("➕ Thêm hàng", "📋 Quản lý hàng",
          "⏳ Lệnh nạp chờ", "📊 Thống kê",
          "📢 Thông báo", "👥 Danh sách user",
          "👑 Quản lý admin", "🚫 Ban / Chặn User",
          "🏠 Main")
    return k

def kb_huy(uid=None):
    # Chỉ dùng tiếng Việt; không còn chức năng chuyển ngôn ngữ trong menu.
    k = types.ReplyKeyboardMarkup(resize_keyboard=True)
    k.add("❌ Hủy")
    return k


def kb_rent_bot():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton(
        "📅 1 Tuần - 25.000đ", callback_data="RENT|1W"
    ))
    kb.add(types.InlineKeyboardButton("❌ Hủy", callback_data="RENT_CANCEL"))
    return kb


def validate_telegram_bot_token(token):
    try:
        r=requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=15)
        data=r.json()
        return bool(data.get("ok")), data.get("result", {})
    except Exception:
        return False, {}

def launch_rental_bot(token, admin_id, rent_id, days=7, expires_at=None, bank=None):
    # Dùng hạn thuê đã lưu trong DATA, không tính lại 7 ngày khi restart.
    end_at = expires_at or (datetime.datetime.now()+datetime.timedelta(days=days)).isoformat(timespec="seconds")
    bank = bank or {}
    env=os.environ.copy()
    env.update({
        "BOT_TOKEN": token,
        "SUPER_ADMIN": str(admin_id),
        "ADMIN_IDS": str(admin_id),
        "DATA_FILE": f"rental_{rent_id}.json",
        "RENTAL_END_AT": end_at,
        "RENTAL_CHILD": "1",
        "BANK_QR_URL": str(bank.get("qr_url", "")).strip(),
        "BANK_ACCOUNT": str(bank.get("account", "")).strip(),
        "BANK_ACCOUNT_NAME": str(bank.get("account_name", "")).strip(),
        "BANK_NAME": str(bank.get("bank_name", "")).strip(),
    })
    return subprocess.Popen([sys.executable, os.path.abspath(__file__)], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def process_alive(pid):
    try:
        pid = int(pid)
        if pid <= 0: return False
        os.kill(pid, 0)
        return True
    except Exception:
        return False

def rental_text(uid=None):
    return (
        "*🤖 DỊCH VỤ THUÊ BOT*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🤖 *Bạn sẽ được cấp một bot riêng chạy trên server của chúng tôi.*\n"
        "📦 *Bot có đầy đủ tính năng bán key, nạp tiền tự động (giản lược).*\n"
        "💰 *Giá thuê theo tuần: 25.000đ*\n"
        "📌 *Sau khi thanh toán, vui lòng cung cấp:*\n"
        "   • *Token Bot của bạn*\n"
        "   • *ID Admin của bạn*\n"
        "   • *QR Url*\n"
        "   • *Số tài khoản*\n"
        "   • *Tên Tài Khoản*\n"
        "   • *Tên Ngân Hàng*\n"
        "   • *Bot sẽ được tự động cài đặt và chạy.*\n"
        "\n"
        "*Chọn gói thuê bên dưới:*"
    )

def kb_shop(products, balance):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for p in products:
        if p.get("api_product"):
            kb.add(types.InlineKeyboardButton(f" {p['name']} • {fmt(p['price'])}", callback_data=f"VIEW|{p['id']}"))
        else:
            qty = len(p.get("stock", []))
            icon = "✅" if qty > 0 else "❌"
            kb.add(types.InlineKeyboardButton(f"{icon}  {p['name']}  •  {fmt(p['price'])}  •  Còn {qty}", callback_data=f"VIEW|{p['id']}"))
    kb.add(types.InlineKeyboardButton("🏠 Quay lại Menu", callback_data="MAIN"))
    return kb

def kb_confirm_buy(pid):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ Xác nhận mua", callback_data=f"BUY|{pid}"),
        types.InlineKeyboardButton("↩️ Quay lại", callback_data="SHOP")
    )
    return kb

def kb_the_cao():
    kb = types.InlineKeyboardMarkup(row_width=2)
    for nha_mang in ["VIETTEL", "VINAPHONE", "MOBIFONE", "ZING", "GARENA"]:
        kb.add(types.InlineKeyboardButton(
            f"📱 {nha_mang}", callback_data=f"THE|{nha_mang}"
        ))
    kb.add(types.InlineKeyboardButton("🏠 Quay lại", callback_data="MAIN"))
    return kb

def kb_menh_gia(nha_mang):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for mg, gia_thu in THE_CAO_PRICES.items():
        kb.add(types.InlineKeyboardButton(
            f"{fmt(mg)} → Nạp {fmt(gia_thu)}",
            callback_data=f"MG|{nha_mang}|{mg}"
        ))
    kb.add(types.InlineKeyboardButton("↩️ Quay lại", callback_data="THE_MENU"))
    return kb

def main_shop_text(uid, name=None, balance=None):
    if name is None:
        name = ""
    if balance is None:
        with _lock:
            d = load()
            u = get_user(d, uid)
            balance = u.get("balance", 0)
    return (
        f"*🏪 SHOP HACK FREEFIRE*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👋 Xin chào *{name}*\n"
        f"👜 Số dư: *{fmt(balance)}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔰 *Bảo mật - Chất lượng - An toàn*\n"
        f"⚡ *Giao hàng tự động 24/7*\n\n"
        f"✨ Chọn chức năng bên dưới 👇"
    )



# 🤖 THUÊ BOT
@bot.message_handler(func=lambda m: m.text == "🤖 Thuê Bot")
def thue_bot(msg):
    if guard(msg):
        return
    with _lock:
        d = load()
        u = get_user(d, msg.from_user.id)
        balance = u["balance"]
    text = rental_text(msg.from_user.id) + f"\n\n👜 *Số dư hiện tại: {fmt(balance)}*"
    bot.send_message(
        msg.chat.id, text, parse_mode="Markdown", reply_markup=kb_rent_bot()
    )


@bot.callback_query_handler(func=lambda c: c.data == "RENT_CANCEL")
def cb_rent_cancel(call):
    with _lock:
        d = load()
        d["states"].pop(str(call.from_user.id), None)
        save(d)
    bot.answer_callback_query(call.id, "Đã hủy.")
    try:
        bot.edit_message_text(
            "❌ *Đã hủy thuê bot.*",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    except Exception:
        pass


@bot.callback_query_handler(func=lambda c: c.data == "RENT|1W")
def cb_rent_1w(call):
    uid = call.from_user.id
    if is_user_banned(uid) or is_user_blocked(uid):
        bot.answer_callback_query(call.id, "🚫 Tài khoản của bạn đang bị hạn chế!", show_alert=True)
        return

    with _lock:
        d = load()
        u = get_user(d, uid)
        if u["balance"] < RENT_BOT_PRICE:
            balance = u["balance"]
            bot.answer_callback_query(
                call.id,
                f"❌ Không đủ tiền! Cần {fmt(RENT_BOT_PRICE)}, có {fmt(balance)}.",
                show_alert=True
            )
            return
        u["balance"] -= RENT_BOT_PRICE
        d["states"][str(uid)] = {
            "action": "rent_waiting_qr_url",
            "plan": "1W",
            "price": RENT_BOT_PRICE,
        }
        save(d)
        new_balance = u["balance"]

    bot.answer_callback_query(call.id, "✅ Đã thanh toán gói 1 tuần.")
    bot.send_message(
        uid,
        "*✅ THANH TOÁN THUÊ BOT THÀNH CÔNG*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📅 Gói: *1 Tuần*\n"
        "💵 Đã trừ: *25.000đ*\n"
        f"👜 Số dư còn: *{fmt(new_balance)}*\n\n"
        "🔐 *Bước 1/6:* Vui lòng gửi *URL QR ngân hàng* của bạn.\n"
        "📌 Sau đó bot sẽ lần lượt yêu cầu 5 thông tin còn lại.\n\n"
        "❌ Bấm *Hủy* để dừng thao tác.",
        parse_mode="Markdown", reply_markup=kb_huy()
    )


# /start
@bot.message_handler(commands=["start"])
def cmd_start(msg):
    uid = msg.from_user.id

    # User bị BAN hẳn thì không cho /start được luôn
    if is_user_banned(uid):
        try:
            bot.send_message(uid,
                f"🚫 *Tài khoản của bạn đã bị BAN vĩnh viễn khỏi bot!*\n\n"
                f"Liên hệ {SUPPORT} nếu có thắc mắc.",
                parse_mode="Markdown")
        except Exception:
            pass
        return
    if is_user_blocked(uid):
        try:
            bot.send_message(uid,
                f"⛔ *Tài khoản của bạn đang bị TẠM CẤM sử dụng bot!*\n\n"
                f"Liên hệ {SUPPORT} để được hỗ trợ gỡ cấm.",
                parse_mode="Markdown")
        except Exception:
            pass
        return

    with _lock:
        d = load()
        u = get_user(d, uid)
        u["name"] = msg.from_user.full_name or ""
        u["username"] = msg.from_user.username or ""
        save(d)

    # Thông báo admin có user mới /start
    for aid in get_admin_list():
        try:
            bot.send_message(aid,
                f"👤 *User vào shop*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📛 Tên: *{msg.from_user.full_name}*\n"
                f"🔗 Username: @{msg.from_user.username or 'N/A'}\n"
                f"🆔 ID: `{uid}`\n"
                f"🕐 {now()}",
                parse_mode="Markdown")
        except Exception:
            pass

    text = (
        f"*🏪 SHOP HACK FREEFIRE*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👋 Xin chào *{msg.from_user.full_name}*\n"
        f"👜 Số dư: *{fmt(u['balance'])}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔰 *Bảo mật - Chất lượng - An toàn*\n"
        f"⚡ *Giao hàng tự động 24/7*\n\n"
        f"✨ Chọn chức năng bên dưới 👇"
    )
    bot.send_message(msg.chat.id, text, parse_mode="Markdown", reply_markup=kb_main(msg.from_user.id))

# /admin
@bot.message_handler(commands=["admin"])
def cmd_admin(msg):
    if not is_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Không có quyền!")
        return
    bot.send_message(msg.chat.id,
        "*👑 BẢNG ĐIỀU KHIỂN ADMIN*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Chọn chức năng bên dưới:",
        parse_mode="Markdown", reply_markup=kb_admin())

# ❓ HƯỚNG DẪN
@bot.message_handler(func=lambda m: m.text == "❓ Hướng dẫn")
def huong_dan(msg):
    if guard(msg):
        return
    bot.send_message(msg.chat.id,
        "*📖 HƯỚNG DẪN SỬ DỤNG BOT*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "*Bước 1 — Nạp tiền:*\n"
        "Bấm 💰 *Nạp tiền* → chuyển khoản đúng nội dung → gửi *ảnh chụp màn hình bill* thật vào bot.\n\n"
        "*Bước 2 — Chờ duyệt:*\n"
        "Admin sẽ kiểm tra và duyệt trong thời gian sớm nhất. Sau khi duyệt, số dư tự động cộng vào ví.\n\n"
        "*Bước 3 — Mua hàng:*\n"
        "Bấm 🛒 *Mua hàng* → chọn sản phẩm → nhận acc ngay lập tức, tự động 24/7.\n\n"
        "*Bước 4 — Nạp thẻ cào:*\n"
        "Bấm 💳 *Nạp thẻ cào* → chọn nhà mạng, mệnh giá → nhập số seri và mã thẻ.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⚠️ *Lưu ý quan trọng:*\n"
        "• Chỉ gửi *ảnh bill thật* — ảnh không liên quan sẽ bị *tự động từ chối*.\n"
        "• Không gửi tin nhắn/ảnh spam liên tục — bot sẽ tự động cảnh báo hoặc hạn chế.\n"
        "• Mọi thắc mắc liên hệ: " + SUPPORT + "\n"
        "━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown")

# LỆNH SLASH — gọi lại đúng hàm của từng nút
@bot.message_handler(commands=["nap"])
def cmd_nap(msg):
    nap_tien(msg)

@bot.message_handler(commands=["napthecao"])
def cmd_napthecao(msg):
    nap_the_cao(msg)

@bot.message_handler(commands=["sodu"])
def cmd_sodu(msg):
    so_du(msg)

@bot.message_handler(commands=["muahang"])
def cmd_muahang(msg):
    mua_hang(msg)

@bot.message_handler(commands=["don"])
def cmd_don(msg):
    don_toi(msg)

@bot.message_handler(commands=["huongdan"])
def cmd_huongdan(msg):
    huong_dan(msg)

# 💰 NẠP TIỀN
def _resolve_qr_image_url(url):
    """Resolve common image-host page URLs (e.g. ibb.co) to a direct image URL."""
    url = str(url or "").strip()
    if not url:
        return ""
    if "ibb.co/" not in url.lower():
        return url
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if not r.ok:
            return url
        html = r.text
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html, re.I)
        if not m:
            m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image', html, re.I)
        return m.group(1).strip() if m else url
    except Exception:
        return url

# 💰 NẠP TIỀN
@bot.message_handler(func=lambda m: m.text == "💰 Nạp tiền")
def nap_tien(msg):
    if guard(msg):
        return
    uid = msg.from_user.id
    rand = rand_code(6)
    noi_dung = f"NAP {uid} {rand}"

    with _lock:
        d = load()
        cfg = get_bank_config(d)
        d["states"][str(uid)] = {"action": "waiting_bill", "noi_dung": noi_dung}
        save(d)

    text = (
        "*💳 THÔNG TIN NẠP TIỀN*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏦 *Ngân hàng:* *{cfg['bank_name'] or 'MoMo'}*\n"
        f"👤 *Chủ TK:* *{cfg['account_name'] or 'DUONG THI TU TRINH'}*\n"
        f"📝 *Nội dung CK:*\n      `{noi_dung}`\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📸 *Chuyển xong nhắn admin gửi bill để duyệt!*"
    )

    # QR chỉ được gửi nếu người quản trị đã cấu hình QR thật.
    # Không bao giờ tự chèn URL QR mặc định.
    if cfg["qr_url"]:
        try:
            qr_image = _resolve_qr_image_url(cfg["qr_url"])
            bot.send_photo(msg.chat.id, qr_image, caption=text,
                           parse_mode="Markdown", reply_markup=kb_huy())
            return
        except Exception:
            # Không để lỗi QR làm hỏng luồng nạp tiền.
            pass

    bot.send_message(msg.chat.id, text, parse_mode="Markdown", reply_markup=kb_huy())

# /duyet - Admin duyệt nạp
@bot.message_handler(commands=["duyet"])
def cmd_duyet(msg):
    if not is_super(msg.from_user.id):
        bot.send_message(msg.chat.id, "🚫 Lệnh này chỉ dành cho *Admin tối cao*!", parse_mode="Markdown")
        return
    parts = msg.text.split()
    if len(parts) < 3:
        bot.send_message(msg.chat.id, "❌ Cú pháp: /duyet <MÃ> <số tiền>")
        return
    dep_id = parts[1].upper()
    try:
        amount = int(parts[2])
        if amount <= 0: raise ValueError
    except ValueError:
        bot.send_message(msg.chat.id, "❌ Số tiền không hợp lệ!")
        return

    with _lock:
        d = load()
        dep = next((x for x in d["deposits"] if x["id"] == dep_id), None)
        if not dep:
            bot.send_message(msg.chat.id, f"❌ Không tìm thấy `{dep_id}`!", parse_mode="Markdown")
            return
        if dep["status"] == "approved":
            bot.send_message(msg.chat.id, f"⚠️ `{dep_id}` đã duyệt rồi!", parse_mode="Markdown")
            return
        dep["status"] = "approved"
        dep["amount"] = amount
        u = get_user(d, int(dep["uid"]))
        u["balance"] += amount
        save(d)

    bot.send_message(msg.chat.id,
        f"╭━━━━━━━━━━━━━━━━━━╮\n"
        f"┃ ✅ DUYỆT THÀNH CÔNG\n"
        f"┣━━━━━━━━━━━━━━━━━━\n"
        f"┃ 🆔 Mã: `{dep_id}`\n"
        f"┃ 👤 KH: {dep['name']}\n"
        f"┃ 💵 Cộng: +{fmt(amount)}\n"
        f"┃ 👜 Số dư mới: {fmt(u['balance'])}\n"
        f"╰━━━━━━━━━━━━━━━━━━╯")

    try:
        bot.send_message(int(dep["uid"]),
            f"*🎉 NẠP TIỀN THÀNH CÔNG!*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Mã: `{dep_id}`\n"
            f"💵 Cộng: *+{fmt(amount)}*\n"
            f"👜 Số dư hiện tại: *{fmt(u['balance'])}*\n\n"
            f"🛒 Bấm *Mua hàng* để mua acc ngay!",
            parse_mode="Markdown", reply_markup=kb_main(msg.from_user.id))
    except Exception:
        pass

# /tuchoi - Admin từ chối nạp
@bot.message_handler(commands=["tuchoi"])
def cmd_tuchoi(msg):
    if not is_super(msg.from_user.id):
        bot.send_message(msg.chat.id, "🚫 Lệnh này chỉ dành cho *Admin tối cao*!", parse_mode="Markdown")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(msg.chat.id, "❌ Cú pháp: /tuchoi <MÃ>")
        return
    dep_id = parts[1].upper()
    ly_do = " ".join(parts[2:]) if len(parts) > 2 else "Không hợp lệ"

    with _lock:
        d = load()
        dep = next((x for x in d["deposits"] if x["id"] == dep_id), None)
        if not dep:
            bot.send_message(msg.chat.id, f"❌ Không tìm thấy `{dep_id}`!", parse_mode="Markdown")
            return
        if dep["status"] != "pending":
            bot.send_message(msg.chat.id, f"⚠️ Lệnh này đã xử lý rồi!")
            return
        dep["status"] = "rejected"
        save(d)

    bot.send_message(msg.chat.id,
        f"✅ Đã từ chối lệnh `{dep_id}`", parse_mode="Markdown")

    try:
        bot.send_message(int(dep["uid"]),
            f"*❌ NẠP TIỀN BỊ TỪ CHỐI*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Mã: `{dep_id}`\n"
            f"⚠️ Lý do: *{ly_do}*\n\n"
            f"Vui lòng liên hệ admin nếu có thắc mắc!",
            parse_mode="Markdown", reply_markup=kb_main(msg.from_user.id))
    except Exception:
        pass

# 👜 SỐ DƯ
@bot.message_handler(func=lambda m: m.text == "👜 Số dư")
def so_du(msg):
    if guard(msg):
        return
    with _lock:
        d = load()
        u = get_user(d, msg.from_user.id)
    bot.send_message(msg.chat.id,
        f"*👜 VÍ CỦA BẠN*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 Số dư: *{fmt(u['balance'])}*\n"
        f"🕐 Cập nhật: {now()}",
        parse_mode="Markdown")

# 🛒 MUA HÀNG
@bot.message_handler(func=lambda m: m.text == "🛒 Mua hàng")
def mua_hang(msg):
    if guard(msg):
        return
    with _lock:
        d = load()
        u = get_user(d, msg.from_user.id)

    bot.send_message(msg.chat.id,
        f"*🛒 CỬA HÀNG HACK FREEFIRE*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👜 Số dư: *{fmt(u['balance'])}*\n"
        f"🛍 Sản phẩm có sẵn 👇\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚡ Giao hàng tự động sau khi mua",
        parse_mode="Markdown",
        reply_markup=kb_shop(d["products"], u["balance"]))

# Xem chi tiết sản phẩm
@bot.callback_query_handler(func=lambda c: c.data.startswith("VIEW|"))
def cb_view(call):
    if is_user_banned(call.from_user.id) or is_user_blocked(call.from_user.id):
        bot.answer_callback_query(call.id, "🚫 Tài khoản của bạn đang bị hạn chế sử dụng bot!", show_alert=True)
        return
    pid = call.data.split("|")[1]
    with _lock:
        d = load()
        u = get_user(d, call.from_user.id)
        p = find_product(d, pid)
    if not p:
        bot.answer_callback_query(call.id, "❌ Không tìm thấy!")
        return

    qty = 9999 if p.get("api_product") else len(p.get("stock", []))
    status = "🟢 Sẵn Sàng" if p.get("api_product") else ("🟢 Còn hàng" if qty > 0 else "🔴 Hết hàng")
    du = u["balance"] >= p["price"]

    text = (
        f"*🧾 CHI TIẾT SẢN PHẨM*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎮 Sản phẩm: *{p['name']}*\n"
        f"📋 Mô tả: _{p['desc']}_\n"
        f"💰 Giá: *{fmt(p['price'])}*\n"
        f"📦 Tồn kho: *{qty if p.get('api_product') else qty}*\n"
        f"📊 Trạng thái: {status}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👜 Số dư của bạn: *{fmt(u['balance'])}*\n"
    )
    if not du:
        text += f"⚠️ _Thiếu {fmt(p['price'] - u['balance'])}_\n"
    text += "\n✅ Bấm *Xác nhận mua* để thanh toán bằng ví"

    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="Markdown",
                              reply_markup=(types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ Xác nhận mua", callback_data=f"API_BUY|{pid}"), types.InlineKeyboardButton("↩️ Quay lại", callback_data="SHOP")) if p.get("api_product") else kb_confirm_buy(pid)) if (p.get("api_product") or qty > 0) else
                              types.InlineKeyboardMarkup().add(
                                  types.InlineKeyboardButton("↩️ Quay lại", callback_data="SHOP")
                              ))
    except Exception:
        pass
    bot.answer_callback_query(call.id)

# Xác nhận mua → thanh toán
@bot.callback_query_handler(func=lambda c: c.data.startswith("API_BUY|"))
def cb_api_buy(call):
    uid=call.from_user.id
    if is_user_banned(uid) or is_user_blocked(uid):
        bot.answer_callback_query(call.id,"🚫 Tài khoản bị hạn chế!",show_alert=True); return
    pid=call.data.split("|",1)[1]
    with _lock:
        d=load(); u=get_user(d,uid); p=find_product(d,pid)
        if not p or not p.get("api_product"):
            bot.answer_callback_query(call.id,"❌ Gói API không tồn tại!",show_alert=True); return
        if u["balance"]<p["price"]:
            bot.answer_callback_query(call.id,f"❌ Cần {fmt(p['price'])}, bạn có {fmt(u['balance'])}.",show_alert=True); return
    bot.answer_callback_query(call.id,"⏳ Đang tạo key tự động...")
    try: key=create_fakelag_key(p)
    except Exception as e:
        bot.send_message(uid, f"❌ *Không tạo được key.*\n`{str(e)[:300]}`", parse_mode="Markdown"); return
    exp=expires_at_days(p["days"])
    with _lock:
        d=load(); u=get_user(d,uid)
        if u["balance"]<p["price"]:
            bot.send_message(uid,"❌ Số dư vừa thay đổi, không thể hoàn tất đơn."); return
        u["balance"]-=p["price"]; d["ord_counter"]+=1; oid=mixed_id(d, "API", length=7)
        order={"id":oid,"uid":str(uid),"name":call.from_user.full_name,"username":call.from_user.username or "",
               "pid":pid,"product":p["name"],"price":p["price"],"key":key,"days":p["days"],
               "created_at":now(),"expires_at":exp,"status":"active"}
        d["orders"].append(order); u.setdefault("orders",[]).append(oid); save(d); balance=u["balance"]
    bot.edit_message_text(
        f"*✅ TẠO KEY THÀNH CÔNG*\n━━━━━━━━━━━━━━━━━━\n🔑 Gói: *{p['name']}*\n🧾 Mã đơn: `{oid}`\n🔐 Key: `{key}`\n📅 Hạn: *{exp.replace('T',' ')}*\n⏳ Còn lại: *{remaining_text(order)}*\n💵 Giá: *{fmt(p['price'])}*\n👜 Số dư: *{fmt(balance)}*",
        call.message.chat.id,call.message.message_id,parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🏠 Menu",callback_data="MAIN")))

@bot.callback_query_handler(func=lambda c: c.data.startswith("BUY|"))
def cb_buy(call):
    if is_user_banned(call.from_user.id) or is_user_blocked(call.from_user.id):
        bot.answer_callback_query(call.id, "🚫 Tài khoản của bạn đang bị hạn chế sử dụng bot!", show_alert=True)
        return
    pid = call.data.split("|")[1]
    uid = call.from_user.id

    with _lock:
        d = load()
        u = get_user(d, uid)
        p = find_product(d, pid)

        if not p:
            bot.answer_callback_query(call.id, "❌ Sản phẩm không tồn tại!")
            return
        if p.get("api_product"):
            bot.answer_callback_query(call.id, "❌ Dùng nút Mua & Tạo Key.", show_alert=True)
            return
        if len(p.get("stock", [])) == 0:
            bot.answer_callback_query(call.id, "❌ Hết hàng rồi!")
            return
        if u["balance"] < p["price"]:
            bot.answer_callback_query(call.id,
                f"❌ Không đủ tiền!\nCần: {fmt(p['price'])}\nCó: {fmt(u['balance'])}")
            try:
                bot.edit_message_text(
                    f"*❌ Không đủ tiền!*\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"💰 Cần: *{fmt(p['price'])}*\n"
                    f"👜 Số dư: *{fmt(u['balance'])}*\n"
                    f"⚠️ Thiếu: *{fmt(p['price'] - u['balance'])}*\n\n"
                    f"Vui lòng bấm *💰 Nạp tiền* để nạp thêm!",
                    call.message.chat.id, call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("↩️ Quay lại", callback_data="SHOP")
                    ))
            except Exception:
                pass
            return

        # Giao dịch
        u["balance"] -= p["price"]
        item = p["stock"].pop(0)
        d["ord_counter"] += 1
        oid = mixed_id(d, "ORD", length=7)

        # Parse gmail|password
        parts_item = item.split("|") if "|" in item else [item, "N/A"]
        gmail = parts_item[0].strip()
        password = parts_item[1].strip() if len(parts_item) > 1 else "N/A"

        order = {
            "id": oid, "uid": str(uid),
            "name": call.from_user.full_name,
            "username": call.from_user.username or "",
            "pid": pid,
            "product": p["name"],
            "price": p["price"],
            "gmail": gmail,
            "password": password,
            "time": now(),
        }
        d["orders"].append(order)
        # Lưu vào lịch sử user
        u.setdefault("orders", []).append(oid)
        save(d)

    bot.answer_callback_query(call.id, "✅ Mua thành công!")
    try:
        bot.edit_message_text(
            f"*✅ MUA HÀNG THÀNH CÔNG!*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎮 *{p['name']}*\n"
            f"🧾 Mã đơn: `{oid}`\n"
            f"💵 Đã trừ: *{fmt(p['price'])}*\n"
            f"👜 Số dư còn: *{fmt(u['balance'])}*\n"
            f"🕐 {now()}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ _Lưu lại thông tin, bấm 📦 Đơn của tôi để xem lại_",
            call.message.chat.id, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🛒 Mua thêm", callback_data="SHOP"),
                types.InlineKeyboardButton("🏠 Menu", callback_data="MAIN")
            ))
    except Exception:
        pass

    # Báo admin
    for aid in get_admin_list():
        try:
            bot.send_message(aid,
                f"╭━━━━━━━━━━━━━━━━━━╮\n"
                f"┃ 🛒 ĐƠN MUA ACC MỚI\n"
                f"┣━━━━━━━━━━━━━━━━━━\n"
                f"┃ 👤 Người mua: {call.from_user.full_name}\n"
                f"┃ 🔗 @{call.from_user.username or 'N/A'}\n"
                f"┃ 🆔 ID: {uid}\n"
                f"┃ 🛍 Sản phẩm: {p['name']}\n"
                f"┃ 🧾 Mã đơn: `{oid}`\n"
                f"┃ 💵 Giá: {fmt(p['price'])}\n"
                f"┃ 📦 Acc còn lại: {len(p['stock'])}\n"
                f"┃ 🕐 {now()}\n"
                f"╰━━━━━━━━━━━━━━━━━━╯")
        except Exception:
            pass

# Callback: Quay lại shop
@bot.callback_query_handler(func=lambda c: c.data == "SHOP")
def cb_shop(call):
    with _lock:
        d = load()
        u = get_user(d, call.from_user.id)
    try:
        bot.edit_message_text(
            f"*🛒 CỬA HÀNG HACK FREEFIRE*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👜 Số dư: *{fmt(u['balance'])}*\n"
            f"🛍 Chọn sản phẩm 👇",
            call.message.chat.id, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=kb_shop(d["products"], u["balance"]))
    except Exception:
        pass
    bot.answer_callback_query(call.id)

# Callback: Về menu chính
@bot.callback_query_handler(func=lambda c: c.data == "MAIN")
def cb_main(call):
    with _lock:
        d = load()
        u = get_user(d, call.from_user.id)
    try:
        bot.edit_message_text(
            f"*🏪 SHOP HACK FREEFIRE*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👋 Xin chào *{call.from_user.full_name}*\n"
            f"👜 Số dư: *{fmt(u['balance'])}*\n\n"
            f"✨ Chọn chức năng bên dưới 👇",
            call.message.chat.id, call.message.message_id,
            parse_mode="Markdown")
    except Exception:
        pass
    bot.answer_callback_query(call.id)

# 📦 ĐƠN CỦA TÔI (có lưu lại kể cả xóa bot)
@bot.message_handler(func=lambda m: m.text == "📦 Đơn của tôi")
def don_toi(msg):
    if guard(msg):
        return
    uid = str(msg.from_user.id)
    with _lock:
        d = load()
    my = [o for o in d["orders"] if o["uid"] == uid]

    if not my:
        bot.send_message(msg.chat.id,
            "*📦 ĐƠN HÀNG*\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🚫 Bạn chưa có đơn hàng nào!",
            parse_mode="Markdown")
        return

    text = "*📦 LỊCH SỬ MUA HÀNG*\n━━━━━━━━━━━━━━━━━━\n"
    for o in my[-5:]:
        # API key order (có trường "key")
        if o.get("key"):
            status_label = {"active": "🟢 Còn hạn", "expired": "🔴 Hết hạn"}.get(o.get("status", ""), o.get("status", "N/A"))
            text += (
                f"\n🔑 Key: `{o['key']}`\n"
                f"🧾 Mã đơn: `{o['id']}`\n"
                f"📅 Hạn: *{str(o.get('expires_at', 'N/A')).replace('T', ' ')}*\n"
                f"⏳ Thời gian còn lại: *{remaining_text(o)}*\n"
                f"📊 Trạng thái: {status_label}\n"
                f"💵 Giá: *{fmt(o['price'])}*\n"
                f"🕐 Thời gian mua: {o.get('created_at', o.get('time', 'N/A'))}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
            )
        else:
            # Gmail/password order (cũ)
            text += (
                f"\n🧾 Mã: `{o['id']}`\n"
                f"🎮 {o['product']}\n"
                f"📧 Gmail: `{o.get('gmail', 'N/A')}`\n"
                f"🔑 Mật khẩu: `{o.get('password', 'N/A')}`\n"
                f"💵 {fmt(o['price'])} | 🕐 {o.get('time', 'N/A')}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
            )
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")

# 💳 NẠP THẺ CÀO
@bot.message_handler(func=lambda m: m.text == "💳 Nạp thẻ cào")
def nap_the_cao(msg):
    if guard(msg):
        return
    bot.send_message(msg.chat.id,
        f"*💳 NẠP THẺ CÀO*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 Phí đổi thẻ: *20%*\n"
        f"✅ Nhận về: *80% mệnh giá*\n"
        f"⚠️ Sai mệnh giá bị trừ *60%*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📱 Chọn nhà mạng:",
        parse_mode="Markdown",
        reply_markup=kb_the_cao())

@bot.callback_query_handler(func=lambda c: c.data == "THE_MENU")
def cb_the_menu(call):
    try:
        bot.edit_message_text(
            f"*💳 NẠP THẺ CÀO*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 Phí: *20%* | Nhận: *80%*\n"
            f"⚠️ Sai mệnh giá bị trừ *60%*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📱 Chọn nhà mạng:",
            call.message.chat.id, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=kb_the_cao())
    except Exception:
        pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("THE|"))
def cb_chon_nha_mang(call):
    nha_mang = call.data.split("|")[1]
    try:
        bot.edit_message_text(
            f"*📱 {nha_mang}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Chọn mệnh giá thẻ:",
            call.message.chat.id, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=kb_menh_gia(nha_mang))
    except Exception:
        pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("MG|"))
def cb_chon_menh_gia(call):
    _, nha_mang, mg_str = call.data.split("|")
    mg = int(mg_str)
    uid = str(call.from_user.id)

    with _lock:
        d = load()
        d["states"][uid] = {
            "action": "waiting_the_cao",
            "nha_mang": nha_mang,
            "menh_gia": mg
        }
        save(d)

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id,
        f"*💳 NẠP THẺ {nha_mang}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 Mệnh giá: *{fmt(mg)}*\n"
        f"✅ Nhận: *{fmt(mg * 80 // 100)}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📝 Gửi thông tin thẻ theo định dạng:\n"
        f"`SỐ_SERI|MÃ_THẺ`\n\n"
        f"Ví dụ:\n`1234567890|ABCD1234EFGH`\n\n"
        f"❌ Bấm Hủy để thoát",
        parse_mode="Markdown", reply_markup=kb_huy())

def _get_state(uid):
    d = load()
    return d.get("states", {}).get(str(uid), {})

# ❌ HỦY
@bot.message_handler(func=lambda m: m.text == "❌ Hủy")
def huy(msg):
    uid = str(msg.from_user.id)
    with _lock:
        d = load()
        state = d["states"].pop(uid, None)
        save(d)
    if state and state.get("action") in {"rent_waiting_qr_url", "rent_waiting_bank_account", "rent_waiting_bank_name", "rent_waiting_bank", "rent_waiting_token", "rent_waiting_admin_id"}:
        bot.send_message(
            msg.chat.id,
            "❌ *Đã hủy bước nhập thông tin thuê bot.*\n\n"
            "⚠️ Gói thuê đã thanh toán không tự hoàn tiền bằng nút Hủy.",
            parse_mode="Markdown", reply_markup=kb_main()
        )
    else:
        bot.send_message(msg.chat.id, "❌ Đã hủy thao tác.", reply_markup=kb_main(msg.from_user.id))

# ADMIN: ➕ THÊM HÀNG
@bot.message_handler(func=lambda m: m.text == "➕ Thêm hàng" and is_admin(m.from_user.id))
def them_hang(msg):
    with _lock:
        d = load()
    kb = types.InlineKeyboardMarkup(row_width=1)
    for p in d["products"]:
        qty = len(p.get("stock", []))
        kb.add(types.InlineKeyboardButton(
            f"📦 {p['name']} • {fmt(p['price'])} • còn {qty}",
            callback_data=f"ADDST|{p['id']}"
        ))
    kb.add(types.InlineKeyboardButton("➕ Thêm sản phẩm mới", callback_data="NEW_PRODUCT"))
    bot.send_message(msg.chat.id, "*📦 Chọn để thêm kho:*",
                     parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ADDST|"))
def cb_addst(call):
    if not is_admin(call.from_user.id): return
    pid = call.data.split("|")[1]
    uid = str(call.from_user.id)
    with _lock:
        d = load()
        d["states"][uid] = {"action": "adding_stock", "pid": pid}
        save(d)
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id,
        "*📝 Gửi danh sách acc (mỗi dòng 1 acc):*\n"
        "Định dạng: `gmail|password`\n\n"
        "Ví dụ:\n`abc@gmail.com|Pass123`\n`xyz@gmail.com|Pass456`",
        parse_mode="Markdown", reply_markup=kb_huy())

@bot.callback_query_handler(func=lambda c: c.data == "NEW_PRODUCT")
def cb_new_product(call):
    if not is_admin(call.from_user.id): return
    uid = str(call.from_user.id)
    with _lock:
        d = load()
        d["states"][uid] = {"action": "new_product_name"}
        save(d)
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id,
        "*➕ TẠO SẢN PHẨM MỚI*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Gửi tên sản phẩm:",
        parse_mode="Markdown", reply_markup=kb_huy())

# ADMIN: 📋 QUẢN LÝ HÀNG
@bot.message_handler(func=lambda m: m.text == "📋 Quản lý hàng" and is_admin(m.from_user.id))
def quan_ly(msg):
    with _lock:
        d = load()
    kb = types.InlineKeyboardMarkup(row_width=1)
    text = "╭━━━━━━━━━━━━━━━━━━╮\n┃ 📋 *DANH SÁCH SẢN PHẨM*\n┣━━━━━━━━━━━━━━━━━━\n"
    for p in d["products"]:
        qty = len(p.get("stock", []))
        icon = "🟢" if qty > 0 else "🔴"
        text += f"┃ {icon} *{p['name']}* │ {fmt(p['price'])} │ còn *{qty}*\n"
        kb.add(types.InlineKeyboardButton(
            f"🗑 Xóa: {p['name']}",
            callback_data=f"DEL_PROD|{p['id']}"))
    text += "╰━━━━━━━━━━━━━━━━━━╯\n\n💡 Bấm ➕ *Thêm hàng* để nạp thêm kho.\n🗑 Bấm nút bên dưới để xóa sản phẩm."
    bot.send_message(msg.chat.id, text, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("DEL_PROD|"))
def cb_del_prod_confirm(call):
    if not is_admin(call.from_user.id):
        return
    pid = call.data.split("|")[1]
    with _lock:
        d = load()
        p = find_product(d, pid)
    if not p:
        bot.answer_callback_query(call.id, "❌ Không tìm thấy!")
        return
    bot.answer_callback_query(call.id)
    qty = len(p.get("stock", []))
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ Xác nhận xóa", callback_data=f"DEL_YES|{pid}"),
        types.InlineKeyboardButton("↩️ Hủy", callback_data="DEL_NO"),
    )
    bot.send_message(call.message.chat.id,
        f"⚠️ *XÁC NHẬN XÓA SẢN PHẨM*\n\n"
        f"🛍 {p['name']}\n"
        f"💰 {fmt(p['price'])}\n"
        f"📦 Kho: {qty} acc\n\n"
        f"_Xóa sẽ mất luôn toàn bộ acc còn trong kho, không thể hoàn tác!_",
        parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("DEL_YES|"))
def cb_del_prod_yes(call):
    if not is_admin(call.from_user.id):
        return
    pid = call.data.split("|")[1]
    with _lock:
        d = load()
        p = find_product(d, pid)
        if not p:
            bot.answer_callback_query(call.id, "❌ Không tìm thấy!")
            return
        d["products"] = [x for x in d["products"] if x["id"] != pid]
        save(d)
    bot.answer_callback_query(call.id, "✅ Đã xóa!")
    try:
        bot.edit_message_text(
            f"✅ *ĐÃ XÓA SẢN PHẨM*\n\n🛍 {p['name']} đã bị xóa khỏi cửa hàng.",
            call.message.chat.id, call.message.message_id,
            parse_mode="Markdown")
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data == "DEL_NO")
def cb_del_prod_no(call):
    bot.answer_callback_query(call.id, "Đã hủy!")
    try:
        bot.edit_message_text("↩️ Đã hủy xóa sản phẩm.",
            call.message.chat.id, call.message.message_id)
    except Exception:
        pass

# ADMIN: ⏳ LỆNH NẠP CHỜ
@bot.message_handler(func=lambda m: m.text == "⏳ Lệnh nạp chờ" and is_admin(m.from_user.id))
def lenh_cho(msg):
    with _lock:
        d = load()
    pending = [x for x in d["deposits"] if x["status"] == "pending"]
    if not pending:
        bot.send_message(msg.chat.id, "✅ Không có lệnh nạp nào đang chờ!")
        return
    bot.send_message(msg.chat.id, f"⏳ Có *{len(pending)}* lệnh chờ duyệt:", parse_mode="Markdown")
    for dep in pending:
        try:
            cap = (
                f"╭━━━━━━━━━━━━━━━━━━╮\n"
                f"┃ 🔔 *LỆNH NẠP `{dep['id']}`*\n"
                f"┣━━━━━━━━━━━━━━━━━━\n"
                f"┃ 👤 {dep['name']}\n"
                f"┃ 🔗 @{dep.get('username', 'N/A')}\n"
                f"┃ 🆔 {dep['uid']}\n"
                f"┃ 📝 {dep.get('noi_dung','N/A')}\n"
                f"┃ 🕐 {dep['time']}\n"
                f"╰━━━━━━━━━━━━━━━━━━╯\n\n"
                f"✅ /duyet `{dep['id']}` <số tiền>\n"
                f"❌ /tuchoi `{dep['id']}`"
            )
            bot.send_photo(msg.chat.id, dep["photo"], caption=cap, parse_mode="Markdown")
        except Exception:
            bot.send_message(msg.chat.id,
                f"⚠️ `{dep['id']}` - ảnh hết hạn\n"
                f"✅ /duyet `{dep['id']}` <số tiền>\n"
                f"❌ /tuchoi `{dep['id']}`")

# ADMIN: 📊 THỐNG KÊ
@bot.message_handler(func=lambda m: m.text == "📊 Thống kê" and is_admin(m.from_user.id))
def thong_ke(msg):
    with _lock:
        d = load()
    rev   = sum(o["price"] for o in d.get("orders", []))
    dep   = sum(x["amount"] for x in d.get("deposits", []) if x["status"] == "approved")
    pend  = len([x for x in d.get("deposits", []) if x["status"] == "pending"])
    users = len(d.get("users", {}))
    ords  = len(d.get("orders", []))

    bot.send_message(msg.chat.id,
        f"*📊 THỐNG KÊ SHOP*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👥 Tổng users: *{users}*\n"
        f"🛒 Tổng đơn: *{ords}*\n"
        f"💵 Tổng nạp: *{fmt(dep)}*\n"
        f"💰 Doanh thu: *{fmt(rev)}*\n"
        f"⏳ Chờ duyệt: *{pend} lệnh*\n"
        f"🕐 {now()}",
        parse_mode="Markdown")

# ADMIN: 👥 DANH SÁCH USER
@bot.message_handler(func=lambda m: m.text == "👥 Danh sách user" and is_admin(m.from_user.id))
def ds_user(msg):
    with _lock:
        d = load()
    users = d.get("users", {})
    if not users:
        bot.send_message(msg.chat.id, "👥 Chưa có user nào!")
        return
    text = f"*👥 DANH SÁCH USER ({len(users)})*\n━━━━━━━━━━━━━━━━━━\n"
    for uid, u in list(users.items())[-20:]:
        uname = f"@{u['username']}" if u.get("username") else "N/A"
        text += (
            f"👤 *{u.get('name','?')}*\n"
            f"   🔗 {uname} | 🆔 `{uid}`\n"
            f"   💰 {fmt(u['balance'])} | 🛒 {len(u.get('orders',[]))} đơn\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")

# ADMIN: 📢 THÔNG BÁO BROADCAST
@bot.message_handler(func=lambda m: m.text == "📢 Thông báo" and is_admin(m.from_user.id))
def admin_broadcast(msg):
    uid = str(msg.from_user.id)
    with _lock:
        d = load()
        d["states"][uid] = {"action": "broadcasting"}
        save(d)
    bot.send_message(msg.chat.id,
        "*📢 GỬI THÔNG BÁO*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Nhập nội dung thông báo muốn gửi đến tất cả users:\n\n"
        "_Hỗ trợ: text, ảnh_\nBấm ❌ Hủy để thoát.",
        parse_mode="Markdown", reply_markup=kb_huy())

# ADMIN: 👑 QUẢN LÝ ADMIN
@bot.message_handler(func=lambda m: m.text == "👑 Quản lý admin" and is_admin(m.from_user.id))
def ql_admin_menu(msg):
    with _lock:
        d = load()
    admins = d.get("admins", ADMIN_IDS[:])
    banned = d.get("banned_admins", [])
    users  = d.get("users", {})

    text = (
        "╭━━━━━━━━━━━━━━━━━━╮\n"
        "┃ 👑 QUẢN LÝ ADMIN\n"
        "┣━━━━━━━━━━━━━━━━━━\n"
        f"┃ Tổng admin: *{len(set(admins) | {SUPER_ADMIN}) - len(banned)}*\n"
        f"┃ Đang bị ban: *{len(banned)}*\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        "*👑 ADMIN TỐI CAO:*\n"
    )
    su_name = users.get(str(SUPER_ADMIN), {}).get("name", "Chưa rõ tên")
    text += f"👑 `{SUPER_ADMIN}` — {su_name}\n\n*🛡 ADMIN:*\n"

    normal_admins = [a for a in set(admins) if a != SUPER_ADMIN]
    if not normal_admins:
        text += "_Chưa có admin nào_\n"
    else:
        for aid in normal_admins:
            uname = users.get(str(aid), {}).get("name", "Chưa rõ tên")
            status = "🚫 (đã ban)" if aid in banned else "✅"
            text += f"{status} `{aid}` — {uname}\n"

    text += (
        "\n━━━━━━━━━━━━━━━━━━\n"
        "*📌 Lệnh quản lý:*\n"
        "`/themadmin <ID>` — Thêm admin mới\n"
        "`/xoaadmin <ID>` — Xóa admin\n"
        "`/banadmin <ID>` — Khóa quyền admin\n"
        "`/unbanadmin <ID>` — Mở khóa lại\n"
        "`/dsadmin` — Xem danh sách nhanh\n"
    )
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=["themadmin"])
def cmd_them_admin(msg):
    if not is_super(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Chỉ *Admin tối cao* mới thêm được admin!", parse_mode="Markdown")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(msg.chat.id, "❌ Cú pháp: `/themadmin <ID>`", parse_mode="Markdown")
        return
    try:
        new_id = int(parts[1])
    except ValueError:
        bot.send_message(msg.chat.id, "❌ ID phải là số!")
        return
    with _lock:
        d = load()
        admins = d.get("admins", ADMIN_IDS[:])
        if new_id == SUPER_ADMIN:
            bot.send_message(msg.chat.id, "⚠️ ID này đã là Admin tối cao rồi!")
            return
        if new_id in admins:
            bot.send_message(msg.chat.id, f"⚠️ `{new_id}` đã là admin rồi!", parse_mode="Markdown")
            return
        admins.append(new_id)
        d["admins"] = admins
        if new_id in d.get("banned_admins", []):
            d["banned_admins"].remove(new_id)
        save(d)
    bot.send_message(msg.chat.id,
        f"╭━━━━━━━━━━━━━━━━━━╮\n"
        f"┃ ✅ THÊM ADMIN THÀNH CÔNG\n"
        f"┣━━━━━━━━━━━━━━━━━━\n"
        f"┃ 🆔 ID: {new_id}\n"
        f"╰━━━━━━━━━━━━━━━━━━╯",
        parse_mode="Markdown")
    try:
        bot.send_message(new_id,
            "🎉 *Bạn vừa được cấp quyền Admin!*\n\n"
            "Gõ /admin để mở bảng điều khiển.",
            parse_mode="Markdown")
    except Exception:
        pass

@bot.message_handler(commands=["xoaadmin"])
def cmd_xoa_admin(msg):
    if not is_super(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Chỉ *Admin tối cao* mới xóa được admin!", parse_mode="Markdown")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(msg.chat.id, "❌ Cú pháp: `/xoaadmin <ID>`", parse_mode="Markdown")
        return
    try:
        rm_id = int(parts[1])
    except ValueError:
        bot.send_message(msg.chat.id, "❌ ID phải là số!")
        return
    if rm_id == SUPER_ADMIN:
        bot.send_message(msg.chat.id, "🚫 Không thể xóa Admin tối cao!")
        return
    with _lock:
        d = load()
        admins = d.get("admins", ADMIN_IDS[:])
        if rm_id not in admins:
            bot.send_message(msg.chat.id, f"⚠️ `{rm_id}` không phải admin!", parse_mode="Markdown")
            return
        admins.remove(rm_id)
        d["admins"] = admins
        if rm_id in d.get("banned_admins", []):
            d["banned_admins"].remove(rm_id)
        save(d)
    bot.send_message(msg.chat.id,
        f"✅ Đã xóa quyền admin của `{rm_id}`", parse_mode="Markdown")
    try:
        bot.send_message(rm_id, "⚠️ Bạn đã bị *thu hồi quyền Admin*.", parse_mode="Markdown")
    except Exception:
        pass

@bot.message_handler(commands=["banadmin"])
def cmd_ban_admin(msg):
    if not is_super(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Chỉ *Admin tối cao* mới ban được admin!", parse_mode="Markdown")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(msg.chat.id, "❌ Cú pháp: `/banadmin <ID>`", parse_mode="Markdown")
        return
    try:
        ban_id = int(parts[1])
    except ValueError:
        bot.send_message(msg.chat.id, "❌ ID phải là số!")
        return
    if ban_id == SUPER_ADMIN:
        bot.send_message(msg.chat.id, "🚫 Không thể ban Admin tối cao!")
        return
    with _lock:
        d = load()
        if ban_id not in d.get("admins", ADMIN_IDS[:]):
            bot.send_message(msg.chat.id, f"⚠️ `{ban_id}` không phải admin!", parse_mode="Markdown")
            return
        banned = d.get("banned_admins", [])
        if ban_id not in banned:
            banned.append(ban_id)
        d["banned_admins"] = banned
        save(d)
    bot.send_message(msg.chat.id,
        f"🚫 Đã *khóa quyền admin* của `{ban_id}`\n"
        f"_Vẫn giữ trong danh sách, dùng /unbanadmin để mở lại_",
        parse_mode="Markdown")
    try:
        bot.send_message(ban_id, "🚫 Quyền admin của bạn đã *tạm bị khóa*.", parse_mode="Markdown")
    except Exception:
        pass

@bot.message_handler(commands=["unbanadmin"])
def cmd_unban_admin(msg):
    if not is_super(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Chỉ *Admin tối cao* mới mở khóa được admin!", parse_mode="Markdown")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(msg.chat.id, "❌ Cú pháp: `/unbanadmin <ID>`", parse_mode="Markdown")
        return
    try:
        unban_id = int(parts[1])
    except ValueError:
        bot.send_message(msg.chat.id, "❌ ID phải là số!")
        return
    with _lock:
        d = load()
        banned = d.get("banned_admins", [])
        if unban_id not in banned:
            bot.send_message(msg.chat.id, f"⚠️ `{unban_id}` không bị khóa!", parse_mode="Markdown")
            return
        banned.remove(unban_id)
        d["banned_admins"] = banned
        save(d)
    bot.send_message(msg.chat.id, f"✅ Đã *mở khóa quyền admin* cho `{unban_id}`", parse_mode="Markdown")
    try:
        bot.send_message(unban_id, "✅ Quyền admin của bạn đã được *mở khóa lại*.", parse_mode="Markdown")
    except Exception:
        pass

@bot.message_handler(commands=["dsadmin"])
def cmd_ds_admin(msg):
    if not is_admin(msg.from_user.id):
        return
    with _lock:
        d = load()
    admins = set(d.get("admins", ADMIN_IDS[:])) | {SUPER_ADMIN}
    banned = d.get("banned_admins", [])
    text = f"👑 *DANH SÁCH ADMIN ({len(admins)})*\n\n"
    for aid in admins:
        tag = "👑 Tối cao" if aid == SUPER_ADMIN else ("🚫 Bị ban" if aid in banned else "🛡 Admin")
        text += f"{tag} — `{aid}`\n"
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")


# ADMIN: 🚫 BAN / CHẶN USER & BAN IP
@bot.message_handler(func=lambda m: m.text == "🚫 Ban / Chặn User" and is_admin(m.from_user.id))
def ql_ban_menu(msg):
    with _lock:
        d = load()
    banned_u  = d.get("banned_users", [])
    blocked_u = d.get("blocked_users", [])
    banned_ip = d.get("banned_ips", [])

    text = (
        "╭━━━━━━━━━━━━━━━━━━╮\n"
        "┃ 🚫 BAN / CHẶN USER\n"
        "┣━━━━━━━━━━━━━━━━━━\n"
        f"┃ 🔴 Đang BAN vĩnh viễn: *{len(banned_u)}*\n"
        f"┃ 🟠 Đang bị CHẶN: *{len(blocked_u)}*\n"
        f"┃ 🌐 IP bị chặn: *{len(banned_ip)}*\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        "*📌 Phân biệt BAN vs CHẶN:*\n"
        "🔴 *Ban* — Vĩnh viễn, không /start được nữa.\n"
        "🟠 *Chặn* — Vẫn /start được, nhưng mọi nút đều bị khóa. Nhẹ hơn, dễ gỡ.\n\n"
        "*📌 Lệnh quản lý:*\n"
        "`/banuser <ID> [lý do]` — Ban vĩnh viễn\n"
        "`/unbanuser <ID>` — Gỡ ban\n"
        "`/chanuser <ID> [lý do]` — Tạm chặn\n"
        "`/gochanuser <ID>` — Gỡ chặn\n"
        "`/banip <IP> [lý do]` — Ghi nhận IP xấu (thủ công)\n"
        "`/unbanip <IP>` — Gỡ IP\n"
        "`/dsban` — Xem nhanh danh sách ban/chặn\n\n"
        "⚠️ _Lưu ý: Telegram không cung cấp IP người dùng cho bot, nên `/banip` chỉ dùng để "
        "ghi chú thủ công (VD: khi có nguồn khác xác định được IP kẻ gian), không tự động chặn theo IP thật._"
    )
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=["banuser"])
def cmd_ban_user(msg):
    if not is_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Không có quyền!")
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 2:
        bot.send_message(msg.chat.id, "❌ Cú pháp: `/banuser <ID> [lý do]`", parse_mode="Markdown")
        return
    try:
        target = int(parts[1])
    except ValueError:
        bot.send_message(msg.chat.id, "❌ ID phải là số!")
        return
    if target == SUPER_ADMIN or target in ADMIN_IDS:
        bot.send_message(msg.chat.id, "🚫 Không thể ban admin qua lệnh này!")
        return
    ly_do = parts[2] if len(parts) > 2 else "Không rõ lý do"
    with _lock:
        d = load()
        bl = d.get("banned_users", [])
        if str(target) not in bl:
            bl.append(str(target))
        d["banned_users"] = bl
        save(d)
    bot.send_message(msg.chat.id,
        f"🔴 Đã *BAN vĩnh viễn* `{target}`\n📝 Lý do: _{ly_do}_",
        parse_mode="Markdown")
    try:
        bot.send_message(target,
            f"🚫 *Tài khoản của bạn đã bị BAN vĩnh viễn!*\n\n📝 Lý do: {ly_do}\n\nLiên hệ {SUPPORT} nếu có thắc mắc.",
            parse_mode="Markdown")
    except Exception:
        pass

@bot.message_handler(commands=["unbanuser"])
def cmd_unban_user(msg):
    if not is_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Không có quyền!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(msg.chat.id, "❌ Cú pháp: `/unbanuser <ID>`", parse_mode="Markdown")
        return
    try:
        target = int(parts[1])
    except ValueError:
        bot.send_message(msg.chat.id, "❌ ID phải là số!")
        return
    with _lock:
        d = load()
        bl = d.get("banned_users", [])
        if str(target) not in bl:
            bot.send_message(msg.chat.id, f"⚠️ `{target}` không bị ban!", parse_mode="Markdown")
            return
        bl.remove(str(target))
        d["banned_users"] = bl
        save(d)
    bot.send_message(msg.chat.id, f"✅ Đã *gỡ ban* `{target}`", parse_mode="Markdown")
    try:
        bot.send_message(target, "✅ *Tài khoản của bạn đã được gỡ ban!*\n\nBấm /start để tiếp tục sử dụng.", parse_mode="Markdown")
    except Exception:
        pass

@bot.message_handler(commands=["chanuser"])
def cmd_chan_user(msg):
    if not is_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Không có quyền!")
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 2:
        bot.send_message(msg.chat.id, "❌ Cú pháp: `/chanuser <ID> [lý do]`", parse_mode="Markdown")
        return
    try:
        target = int(parts[1])
    except ValueError:
        bot.send_message(msg.chat.id, "❌ ID phải là số!")
        return
    if target == SUPER_ADMIN or target in ADMIN_IDS:
        bot.send_message(msg.chat.id, "🚫 Không thể chặn admin qua lệnh này!")
        return
    ly_do = parts[2] if len(parts) > 2 else "Không rõ lý do"
    with _lock:
        d = load()
        bl = d.get("blocked_users", [])
        if str(target) not in bl:
            bl.append(str(target))
        d["blocked_users"] = bl
        save(d)
    bot.send_message(msg.chat.id,
        f"🟠 Đã *CHẶN tạm thời* `{target}`\n📝 Lý do: _{ly_do}_",
        parse_mode="Markdown")
    try:
        bot.send_message(target,
            f"⛔ *Tài khoản của bạn đang bị TẠM CẤM sử dụng bot!*\n\n📝 Lý do: {ly_do}\n\nLiên hệ {SUPPORT} để được hỗ trợ gỡ cấm.",
            parse_mode="Markdown")
    except Exception:
        pass

@bot.message_handler(commands=["gochanuser"])
def cmd_go_chan_user(msg):
    if not is_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Không có quyền!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(msg.chat.id, "❌ Cú pháp: `/gochanuser <ID>`", parse_mode="Markdown")
        return
    try:
        target = int(parts[1])
    except ValueError:
        bot.send_message(msg.chat.id, "❌ ID phải là số!")
        return
    with _lock:
        d = load()
        bl = d.get("blocked_users", [])
        if str(target) not in bl:
            bot.send_message(msg.chat.id, f"⚠️ `{target}` không bị chặn!", parse_mode="Markdown")
            return
        bl.remove(str(target))
        d["blocked_users"] = bl
        save(d)
    bot.send_message(msg.chat.id, f"✅ Đã *gỡ chặn* `{target}`", parse_mode="Markdown")
    try:
        bot.send_message(target, "✅ *Tài khoản của bạn đã được gỡ cấm!*\n\nBạn có thể tiếp tục sử dụng bot bình thường.", parse_mode="Markdown")
    except Exception:
        pass

@bot.message_handler(commands=["banip"])
def cmd_ban_ip(msg):
    if not is_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Không có quyền!")
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 2:
        bot.send_message(msg.chat.id, "❌ Cú pháp: `/banip <IP> [lý do]`", parse_mode="Markdown")
        return
    ip = parts[1].strip()
    ly_do = parts[2] if len(parts) > 2 else "Không rõ lý do"
    with _lock:
        d = load()
        bl = d.get("banned_ips", [])
        if ip not in [x["ip"] for x in bl]:
            bl.append({"ip": ip, "reason": ly_do, "time": now(), "by": str(msg.from_user.id)})
        d["banned_ips"] = bl
        save(d)
    bot.send_message(msg.chat.id,
        f"🌐 Đã ghi nhận chặn IP `{ip}`\n📝 Lý do: _{ly_do}_\n\n"
        f"⚠️ _Lưu ý: đây là ghi chú thủ công, Telegram không cho bot biết IP thật của user._",
        parse_mode="Markdown")

@bot.message_handler(commands=["unbanip"])
def cmd_unban_ip(msg):
    if not is_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Không có quyền!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(msg.chat.id, "❌ Cú pháp: `/unbanip <IP>`", parse_mode="Markdown")
        return
    ip = parts[1].strip()
    with _lock:
        d = load()
        bl = d.get("banned_ips", [])
        new_bl = [x for x in bl if x["ip"] != ip]
        if len(new_bl) == len(bl):
            bot.send_message(msg.chat.id, f"⚠️ IP `{ip}` không có trong danh sách!", parse_mode="Markdown")
            return
        d["banned_ips"] = new_bl
        save(d)
    bot.send_message(msg.chat.id, f"✅ Đã gỡ IP `{ip}` khỏi danh sách chặn", parse_mode="Markdown")

@bot.message_handler(commands=["dsban"])
def cmd_ds_ban(msg):
    if not is_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Không có quyền!")
        return
    with _lock:
        d = load()
    banned_u  = d.get("banned_users", [])
    blocked_u = d.get("blocked_users", [])
    banned_ip = d.get("banned_ips", [])

    text = "🚫 *DANH SÁCH BAN / CHẶN*\n\n"
    text += f"🔴 *Ban vĩnh viễn ({len(banned_u)}):*\n"
    text += "\n".join(f"  • `{u}`" for u in banned_u[-15:]) if banned_u else "  _Trống_"
    text += f"\n\n🟠 *Đang chặn ({len(blocked_u)}):*\n"
    text += "\n".join(f"  • `{u}`" for u in blocked_u[-15:]) if blocked_u else "  _Trống_"
    text += f"\n\n🌐 *IP bị chặn ({len(banned_ip)}):*\n"
    text += "\n".join(f"  • `{x['ip']}` — {x.get('reason','')}" for x in banned_ip[-10:]) if banned_ip else "  _Trống_"
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "🏠 Main" and is_admin(m.from_user.id))
def admin_main(msg):
    bot.send_message(msg.chat.id, "🏠 Về trang chính!", reply_markup=kb_main(msg.from_user.id))

# ADMIN: /duyethe - Duyệt thẻ cào thủ công
@bot.message_handler(commands=["duyethe"])
def cmd_duyet_the(msg):
    if not is_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Không có quyền!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(msg.chat.id, "❌ Cú pháp: /duyethe <MÃ>\nVí dụ: /duyethe THE0001")
        return
    the_id = parts[1].upper()

    with _lock:
        d = load()
        tc = next((x for x in d["the_cao_orders"] if x["id"] == the_id), None)
        if not tc:
            bot.send_message(msg.chat.id, f"❌ Không tìm thấy `{the_id}`!", parse_mode="Markdown")
            return
        if tc["status"] != "pending":
            bot.send_message(msg.chat.id, f"⚠️ Thẻ `{the_id}` đã xử lý rồi!", parse_mode="Markdown")
            return
        tc["status"] = "approved"
        nhan_ve = tc.get("nhan_ve", tc["menh_gia"] * 80 // 100)
        u = get_user(d, int(tc["uid"]))
        u["balance"] += nhan_ve
        save(d)

    bot.send_message(msg.chat.id,
        f"╭━━━━━━━━━━━━━━━━━━╮\n"
        f"┃ ✅ *DUYỆT THẺ THÀNH CÔNG*\n"
        f"┣━━━━━━━━━━━━━━━━━━\n"
        f"┃ 🆔 `{the_id}`\n"
        f"┃ 👤 {tc['name']}\n"
        f"┃ 📱 {tc['nha_mang']} | {fmt(tc['menh_gia'])}\n"
        f"┃ 💵 Cộng: +{fmt(nhan_ve)}\n"
        f"┃ 👜 Số dư mới: {fmt(u['balance'])}\n"
        f"╰━━━━━━━━━━━━━━━━━━╯",
        parse_mode="Markdown")
    try:
        bot.send_message(int(tc["uid"]),
            f"*✅ THẺ CÀO ĐƯỢC DUYỆT!*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Mã: `{the_id}`\n"
            f"📱 {tc['nha_mang']} | {fmt(tc['menh_gia'])}\n"
            f"💵 Cộng vào ví: *+{fmt(nhan_ve)}*\n"
            f"👜 Số dư: *{fmt(u['balance'])}*",
            parse_mode="Markdown", reply_markup=kb_main(msg.from_user.id))
    except Exception:
        pass

@bot.message_handler(commands=["tuchoithe"])
def cmd_tuchoi_the(msg):
    if not is_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Không có quyền!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(msg.chat.id, "❌ Cú pháp: /tuchoithe <MÃ>")
        return
    the_id = parts[1].upper()
    ly_do = " ".join(parts[2:]) if len(parts) > 2 else "Thẻ không hợp lệ"

    with _lock:
        d = load()
        tc = next((x for x in d["the_cao_orders"] if x["id"] == the_id), None)
        if not tc:
            bot.send_message(msg.chat.id, f"❌ Không tìm thấy `{the_id}`!", parse_mode="Markdown")
            return
        tc["status"] = "rejected"
        save(d)

    bot.send_message(msg.chat.id, f"✅ Đã từ chối thẻ `{the_id}`", parse_mode="Markdown")
    try:
        bot.send_message(int(tc["uid"]),
            f"*❌ THẺ CÀO BỊ TỪ CHỐI*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Mã: `{the_id}`\n"
            f"📱 {tc['nha_mang']} | {fmt(tc['menh_gia'])}\n"
            f"⚠️ Lý do: _{ly_do}_\n\n"
            f"Liên hệ admin nếu cần hỗ trợ!",
            parse_mode="Markdown", reply_markup=kb_main(msg.from_user.id))
    except Exception:
        pass

# XỬ LÝ TIN NHẮN VĂN BẢN
@bot.message_handler(content_types=["text"])
def handle_text(msg):
    uid_int = msg.from_user.id
    uid = str(uid_int)

    # Chặn user bị ban/block thao tác bất kỳ text nào (kể cả đang ở giữa 1 luồng dở dang)
    if not is_admin(uid_int) and (is_user_banned(uid_int) or is_user_blocked(uid_int)):
        guard(msg)
        return

    # Chống spam tin nhắn liên tục (không áp dụng cho admin — admin cần thao tác nhanh)
    if not is_admin(uid_int) and is_msg_spam(uid_int):
        try:
            bot.send_message(uid_int,
                "⚠️ *Bạn đang gửi tin nhắn quá nhanh!*\n\nVui lòng chậm lại một chút.",
                parse_mode="Markdown")
        except Exception:
            pass
        return

    with _lock:
        d = load()
        state = d.get("states", {}).get(uid, {})
    action = state.get("action", "")

    # THUÊ BOT — 6 bước, lưu trạng thái ngay sau từng bước để restart không mất dữ liệu.
    if action == "rent_waiting_qr_url":
        value = msg.text.strip()
        if not re.match(r"^https?://\S+$", value, re.I):
            bot.send_message(msg.chat.id, "❌ URL QR không hợp lệ. Vui lòng gửi URL bắt đầu bằng http:// hoặc https://", reply_markup=kb_huy())
            return
        with _lock:
            d = load(); st = d["states"].get(uid, {})
            st.update({"action":"rent_waiting_bank_account", "bank_qr_url":value}); d["states"][uid]=st; save(d)
        bot.send_message(msg.chat.id, "✅ Đã nhận URL QR.\n\n🔐 *Bước 2/6:* Gửi *Số tài khoản ngân hàng*.", parse_mode="Markdown", reply_markup=kb_huy())
        return

    if action == "rent_waiting_bank_account":
        value = msg.text.strip().replace(" ", "")
        if not re.match(r"^[A-Za-z0-9._-]{4,40}$", value):
            bot.send_message(msg.chat.id, "❌ Số tài khoản không hợp lệ. Vui lòng gửi lại.", reply_markup=kb_huy())
            return
        with _lock:
            d = load(); st=d["states"].get(uid, {})
            st.update({"action":"rent_waiting_bank_name", "bank_account":value}); d["states"][uid]=st; save(d)
        bot.send_message(msg.chat.id, "✅ Đã nhận số tài khoản.\n\n🔐 *Bước 3/6:* Gửi *Tên tài khoản/chủ tài khoản*.", parse_mode="Markdown", reply_markup=kb_huy())
        return

    if action == "rent_waiting_bank_name":
        value = msg.text.strip()
        if len(value) < 2 or len(value) > 120:
            bot.send_message(msg.chat.id, "❌ Tên tài khoản không hợp lệ. Vui lòng gửi lại.", reply_markup=kb_huy())
            return
        with _lock:
            d=load(); st=d["states"].get(uid, {})
            st.update({"action":"rent_waiting_bank", "bank_account_name":value}); d["states"][uid]=st; save(d)
        bot.send_message(msg.chat.id, "✅ Đã nhận tên tài khoản.\n\n🔐 *Bước 4/6:* Gửi *Tên ngân hàng*.", parse_mode="Markdown", reply_markup=kb_huy())
        return

    if action == "rent_waiting_bank":
        value = msg.text.strip()
        if len(value) < 2 or len(value) > 100:
            bot.send_message(msg.chat.id, "❌ Tên ngân hàng không hợp lệ. Vui lòng gửi lại.", reply_markup=kb_huy())
            return
        with _lock:
            d=load(); st=d["states"].get(uid, {})
            st.update({"action":"rent_waiting_token", "bank_name":value}); d["states"][uid]=st; save(d)
        bot.send_message(msg.chat.id, "✅ Đã nhận tên ngân hàng.\n\n🔐 *Bước 5/6:* Vui lòng gửi *Token Bot* của bạn.", parse_mode="Markdown", reply_markup=kb_huy())
        return

    # Thuê bot — bước 5: nhận token bot
    if action == "rent_waiting_token":
        token = msg.text.strip()
        if len(token) < 20 or ":" not in token:
            bot.send_message(msg.chat.id, "❌ *Token Bot không hợp lệ.*\n\nVui lòng gửi đúng token BotFather cấp cho bot của bạn.", parse_mode="Markdown", reply_markup=kb_huy())
            return
        with _lock:
            d=load(); st=d["states"].get(uid, {})
            st.update({"action":"rent_waiting_admin_id", "bot_token":token}); d["states"][uid]=st; save(d)
        bot.send_message(msg.chat.id, "✅ Đã nhận Token Bot.\n\n🔐 *Bước 6/6:* Vui lòng gửi *ID Admin* của bạn (chỉ gồm số).", parse_mode="Markdown", reply_markup=kb_huy())
        return

    # Thuê bot — bước 6: nhận ID admin, xác thực và tạo đơn
    if action == "rent_waiting_admin_id":
        admin_id_text = msg.text.strip()
        try:
            rental_admin_id = int(admin_id_text)
            if rental_admin_id <= 0: raise ValueError
        except ValueError:
            bot.send_message(msg.chat.id, "❌ *ID Admin không hợp lệ.*\n\nVui lòng gửi ID Telegram dạng số.", parse_mode="Markdown", reply_markup=kb_huy())
            return

        with _lock:
            d=load(); state_now=d["states"].get(uid, {}); rental_token=state_now.get("bot_token", "")
        ok, bot_info = validate_telegram_bot_token(rental_token)
        if not ok:
            bot.send_message(msg.chat.id, "❌ *Token Bot không hoạt động hoặc không hợp lệ.*\n\nHãy tạo bot bằng @BotFather rồi gửi lại Token.", parse_mode="Markdown", reply_markup=kb_huy())
            return

        with _lock:
            d=load(); state_now=d["states"].get(uid, {})
            rent_id=mixed_id(d, "RENT", length=7)
            expires_at=(datetime.datetime.now()+datetime.timedelta(days=7)).isoformat(timespec="seconds")
            rental={
                "id":rent_id, "uid":uid, "name":msg.from_user.full_name, "username":msg.from_user.username or "",
                "plan":state_now.get("plan","1W"), "duration":RENT_BOT_DURATION, "price":int(state_now.get("price",RENT_BOT_PRICE)),
                "bot_token":rental_token, "admin_id":rental_admin_id,
                "bank_qr_url":state_now.get("bank_qr_url",""), "bank_account":state_now.get("bank_account",""),
                "bank_account_name":state_now.get("bank_account_name",""), "bank_name":state_now.get("bank_name",""),
                "time":now(), "status":"starting", "enabled":True, "expires_at":expires_at, "pid":None
            }
            d["rental_orders"].append(rental); d["states"].pop(uid,None); save(d)

        try:
            proc=launch_rental_bot(rental["bot_token"], rental_admin_id, rent_id, 7, expires_at, {
                "qr_url":rental["bank_qr_url"], "account":rental["bank_account"],
                "account_name":rental["bank_account_name"], "bank_name":rental["bank_name"]})
            with _lock:
                d=load()
                for ro in d.get("rental_orders", []):
                    if ro.get("id")==rent_id:
                        ro["status"]="success"; ro["pid"]=proc.pid; ro["enabled"]=True
                        break
                save(d)
        except Exception as e:
            with _lock:
                d=load()
                for ro in d.get("rental_orders", []):
                    if ro.get("id")==rent_id: ro["status"]="error"; ro["last_error"]=str(e)[:300]
                save(d)
            bot.send_message(msg.chat.id, "❌ *Không thể khởi động bot thuê.* Dữ liệu đơn vẫn được lưu để hệ thống tự khôi phục khi khởi động lại.", parse_mode="Markdown", reply_markup=kb_main(msg.from_user.id))
            return

        bot.send_message(msg.chat.id,
            "*✅ ĐÃ TẠO ĐƠN THUÊ BOT*\n━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Mã đơn: `{rent_id}`\n📅 Gói: *1 Tuần*\n💵 Giá: *25.000đ*\n"
            "🤖 Trạng thái: *ĐANG HOẠT ĐỘNG*\n\n"
            "💾 6 thông tin thuê bot đã được lưu vào data.\n"
            "🔄 Khi bot chính khởi động lại, bot thuê sẽ tự động được khôi phục nếu còn hạn.",
            parse_mode="Markdown", reply_markup=kb_main(msg.from_user.id))

        for aid in get_admin_list():
            try:
                bot.send_message(aid,
                    "*🤖 ĐƠN THUÊ BOT MỚI*\n━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 Mã: `{rent_id}`\n👤 Khách: *{msg.from_user.full_name}*\n"
                    f"🆔 User ID: `{uid}`\n💵 Giá: *{fmt(rental['price'])}*\n"
                    f"👑 Admin ID: `{rental_admin_id}`\n🤖 Bot: @{bot_info.get('username','N/A')}\n"
                    f"🏦 Ngân hàng: *{rental['bank_name']}*\n💳 STK: `{rental['bank_account']}`\n👤 Tên TK: *{rental['bank_account_name']}*\n"
                    f"🔗 QR: {rental['bank_qr_url']}\n━━━━━━━━━━━━━━━━━━\n✅ *ĐANG HOẠT ĐỘNG*",
                    parse_mode="Markdown")
            except Exception:
                pass
        return

    # Thêm kho acc
    if action == "adding_stock" and is_admin(msg.from_user.id):
        pid = state.get("pid")
        items = [l.strip() for l in msg.text.strip().splitlines() if l.strip()]
        with _lock:
            d = load()
            p = find_product(d, pid)
            if p:
                p["stock"].extend(items)
                d["states"].pop(uid, None)
                save(d)
                bot.send_message(msg.chat.id,
                    f"╭━━━━━━━━━━━━━━━━━━╮\n"
                    f"┃ ✅ *THÊM HÀNG THÀNH CÔNG*\n"
                    f"┣━━━━━━━━━━━━━━━━━━\n"
                    f"┃ 🛍 *{p['name']}*\n"
                    f"┃ 💰 {fmt(p['price'])}\n"
                    f"┃ 📦 Số lượng: *{len(items)} acc*\n"
                    f"┃ 📦 Tổng kho: *{len(p['stock'])} acc*\n"
                    f"╰━━━━━━━━━━━━━━━━━━╯",
                    parse_mode="Markdown", reply_markup=kb_admin())
                post_new_stock_to_channel(p, len(items), len(p["stock"]))
        return

    # Tạo sản phẩm mới - bước 1: tên
    if action == "new_product_name" and is_admin(msg.from_user.id):
        with _lock:
            d = load()
            d["states"][uid] = {"action": "new_product_price", "name": msg.text.strip()}
            save(d)
        bot.send_message(msg.chat.id,
            f"✅ Tên: *{msg.text.strip()}*\nGửi *giá* (VD: 2000):",
            parse_mode="Markdown")
        return

    # Tạo sản phẩm mới - bước 2: giá
    if action == "new_product_price" and is_admin(msg.from_user.id):
        try:
            price = int(msg.text.strip())
        except ValueError:
            bot.send_message(msg.chat.id, "❌ Giá phải là số! Gửi lại:")
            return
        with _lock:
            d = load()
            name = d["states"][uid].get("name", "Sản phẩm")
            new_id = f"PROD_{rand_code(4)}"
            d["products"].append({
                "id": new_id, "name": name,
                "desc": "Hack FreeFire",
                "price": price, "stock": []
            })
            d["states"].pop(uid, None)
            save(d)
        bot.send_message(msg.chat.id,
            f"✅ *Đã tạo sản phẩm:*\n"
            f"🛍 *{name}* | {fmt(price)}\n"
            f"ID: `{new_id}`",
            parse_mode="Markdown", reply_markup=kb_admin())
        return

    # Thẻ cào: nhận số seri|mã thẻ
    if action == "waiting_the_cao":
        nha_mang = state.get("nha_mang")
        menh_gia = state.get("menh_gia")
        parts_tc = msg.text.strip().split("|")
        if len(parts_tc) < 2:
            bot.send_message(msg.chat.id,
                "❌ Sai định dạng! Gửi: `SỐ_SERI|MÃ_THẺ`",
                parse_mode="Markdown")
            return

        so_seri = parts_tc[0].strip()
        ma_the  = parts_tc[1].strip()
        nhan_ve = menh_gia * 80 // 100

        with _lock:
            d = load()
            d["states"].pop(uid, None)
            d["the_counter"] += 1
            the_id = mixed_id(d, "THE", length=7)
            d["the_cao_orders"].append({
                "id": the_id, "uid": uid,
                "name": msg.from_user.full_name,
                "username": msg.from_user.username or "",
                "nha_mang": nha_mang, "menh_gia": menh_gia,
                "so_seri": so_seri, "ma_the": ma_the,
                "nhan_ve": nhan_ve,
                "time": now(), "status": "pending"
            })
            save(d)

        gia_thu = THE_CAO_PRICES.get(int(menh_gia), int(menh_gia * 0.9))

        # Báo khách đang xử lý
        bot.send_message(msg.chat.id,
            f"*⏳ ĐANG XỬ LÝ THẺ CÀO...*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Mã: `{the_id}`\n"
            f"📱 {nha_mang} | {fmt(menh_gia)}\n"
            f"✅ Sẽ nhận: *{fmt(gia_thu)}*\n"
            f"⚡ Bot tự động xử lý, vui lòng chờ...",
            parse_mode="Markdown", reply_markup=kb_main(msg.from_user.id))

        # Auto gọi API xử lý thẻ
        threading.Thread(target=_doi_the,
            args=(the_id, uid, nha_mang, menh_gia, so_seri, ma_the)).start()
        return

    # Broadcast
    if action == "broadcasting" and is_admin(msg.from_user.id):
        with _lock:
            d = load()
            d["states"].pop(uid, None)
            users = list(d.get("users", {}).keys())
            save(d)
        bot.send_message(msg.chat.id,
            f"📤 _Đang gửi đến {len(users)} users..._",
            parse_mode="Markdown", reply_markup=kb_admin())
        ok = fail = 0
        for user_id in users:
            try:
                bot.send_message(int(user_id),
                    f"*📢 THÔNG BÁO TỪ SHOP*\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{msg.text}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"🕐 {now()}",
                    parse_mode="Markdown")
                ok += 1
                time.sleep(0.05)
            except Exception:
                fail += 1
        bot.send_message(msg.chat.id,
            f"✅ Gửi xong!\n👥 Thành công: *{ok}* | ❌ Thất bại: *{fail}*",
            parse_mode="Markdown")
        return

# Xử lý ảnh (bill nạp tiền / broadcast admin)
@bot.message_handler(content_types=["photo"])
def handle_photo(msg):
    uid_int = msg.from_user.id
    uid = str(uid_int)

    if guard(msg):
        return

    state = _get_state(uid)

    if state.get("action") == "waiting_bill":
        # Chống spam ảnh liên tục vào ô nạp tiền
        if is_photo_spam(uid_int):
            try:
                bot.send_message(uid_int,
                    "⚠️ *Bạn đang gửi ảnh quá nhanh!*\n\nVui lòng chờ vài giây rồi thử lại.",
                    parse_mode="Markdown")
            except Exception:
                pass
            return
        nhan_bill_internal(msg, uid, state)
    elif state.get("action") == "broadcasting" and is_admin(uid_int):
        with _lock:
            d = load()
            d["states"].pop(uid, None)
            users = list(d.get("users", {}).keys())
            save(d)
        cap = msg.caption or "📢 Thông báo từ Shop"
        ok = fail = 0
        for user_id in users:
            try:
                bot.send_photo(int(user_id), msg.photo[-1].file_id,
                               caption=f"*📢 THÔNG BÁO TỪ SHOP*\n━━━━━━━━━━━━━━━━━━\n{cap}",
                               parse_mode="Markdown")
                ok += 1
                time.sleep(0.05)
            except Exception:
                fail += 1
        bot.send_message(msg.chat.id,
            f"✅ Gửi xong!\n👥 Thành công: *{ok}* | ❌ Thất bại: *{fail}*",
            parse_mode="Markdown")
    # Nếu không ở trạng thái nào cả — ảnh gửi lung tung, im lặng bỏ qua (không spam phản hồi)

def nhan_bill_internal(msg, uid, state):
    noi_dung = state.get("noi_dung", f"NAP {uid}")

    # Tải ảnh về để kiểm tra có giống bill hay không
    is_valid_bill = True
    check_reason = "check_skipped"
    tmp_path = None
    try:
        file_info = bot.get_file(msg.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        tmp_path = f"/tmp/bill_{uid}_{int(time.time())}.jpg"
        with open(tmp_path, "wb") as f:
            f.write(downloaded)
        is_valid_bill, check_reason = looks_like_bill(tmp_path)
    except Exception:
        # Không tải/kiểm tra được — không chặn oan người dùng
        is_valid_bill, check_reason = True, "download_failed"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    if not is_valid_bill:
        try:
            bot.send_message(int(uid),
                f"❌ *ẢNH KHÔNG HỢP LỆ — TỰ ĐỘNG TỪ CHỐI*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Ảnh bạn gửi không giống hóa đơn/biên lai chuyển khoản.\n\n"
                f"📸 Vui lòng gửi *ảnh chụp màn hình bill MoMo* thật sau khi chuyển khoản.\n"
                f"⚠️ Gửi ảnh không liên quan nhiều lần có thể bị *hạn chế sử dụng bot*.",
                parse_mode="Markdown", reply_markup=kb_main(msg.from_user.id))
        except Exception:
            pass
        # Giữ nguyên state chờ bill để user gửi lại ảnh đúng, không mất lượt
        return

    with _lock:
        d = load()
        d["dep_counter"] += 1
        dep_id = mixed_id(d, "DEP", length=7)
        dep = {
            "id": dep_id, "uid": uid,
            "name": msg.from_user.full_name,
            "username": msg.from_user.username or "",
            "photo": msg.photo[-1].file_id,
            "noi_dung": noi_dung,
            "time": now(), "status": "pending", "amount": 0,
            "bill_check": check_reason,
        }
        d["deposits"].append(dep)
        d["states"].pop(uid, None)
        save(d)

    bot.send_message(msg.chat.id,
        f"*✅ ĐÃ NHẬN BILL*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Mã: `{dep_id}`\n"
        f"📝 ND: `{noi_dung}`\n"
        f"⏳ Chờ admin duyệt...",
        parse_mode="Markdown", reply_markup=kb_main(msg.from_user.id))

    for aid in get_admin_list():
        try:
            cap = (
                f"╭━━━━━━━━━━━━━━━━━━╮\n"
                f"┃ 🔔 *LỆNH NẠP `{dep_id}`*\n"
                f"┣━━━━━━━━━━━━━━━━━━\n"
                f"┃ 👤 {msg.from_user.full_name}\n"
                f"┃ 🔗 @{msg.from_user.username or 'N/A'}\n"
                f"┃ 🆔 {uid}\n"
                f"┃ 📝 {noi_dung}\n"
                f"┃ 🕐 {now()}\n"
                f"╰━━━━━━━━━━━━━━━━━━╯\n\n"
                f"✅ /duyet `{dep_id}` <số tiền>\n"
                f"❌ /tuchoi `{dep_id}`"
            )
            bot.send_photo(aid, msg.photo[-1].file_id, caption=cap, parse_mode="Markdown")
        except Exception:
            pass

# ĐỔI THẺ CÀO QUA API
def _doi_the(the_id, uid, nha_mang, menh_gia, so_seri, ma_the):
    import hashlib

    # An toàn: nếu chưa cấu hình bí mật (thiếu secret_config.py hoặc lỗi giải mã) thì báo rõ, không âm thầm lỗi
    if not THE_CAO_PARTNER or not THE_CAO_KEY:
        bot.send_message(int(uid),
            "⚠️ *Hệ thống nạp thẻ đang bảo trì!*\n\nLiên hệ admin để được hỗ trợ.",
            parse_mode="Markdown")
        for aid in get_admin_list():
            try:
                bot.send_message(aid,
                    "🚨 *LỖI CẤU HÌNH THẺ CÀO!*\n\n"
                    "Không đọc được Partner ID/Key từ secret_config.py.\n"
                    "Kiểm tra file secret_config.py có tồn tại đúng vị trí không.",
                    parse_mode="Markdown")
            except Exception:
                pass
        return

    def _call_api(url, partner_id, partner_key, wallet_id=None):
        sign = hashlib.md5(
            f"{partner_key}{partner_id}{ma_the}{so_seri}".encode()
        ).hexdigest()
        params = {
            "telco":      nha_mang,
            "code":       ma_the,
            "serial":     so_seri,
            "amount":     menh_gia,
            "request_id": the_id,
            "partner_id": partner_id,
            "sign":       sign,
            "command":    "charging",
        }
        if wallet_id:
            params["wallet_id"] = wallet_id
        resp = requests.get(url, params=params, timeout=30)
        return resp.json()

    try:
        r = _call_api(THE_CAO_URL, THE_CAO_PARTNER, THE_CAO_KEY, THE_CAO_WALLET)

        status  = r.get("status", -1)
        # Số tiền thực nhận theo bảng giá của mình
        gia_thu = THE_CAO_PRICES.get(int(menh_gia), int(menh_gia * 0.9))

        with _lock:
            d  = load()
            tc = next((x for x in d["the_cao_orders"] if x["id"] == the_id), None)
            u2 = get_user(d, int(uid))

            if status == 1:  # ✅ Thành công
                u2["balance"] += gia_thu
                if tc:
                    tc["status"]  = "success"
                    tc["nhan_ve"] = gia_thu
                save(d)
                bot.send_message(int(uid),
                    f"*✅ NẠP THẺ THÀNH CÔNG!*\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📱 {nha_mang} | {fmt(menh_gia)}\n"
                    f"💵 Cộng vào ví: *+{fmt(gia_thu)}*\n"
                    f"👜 Số dư: *{fmt(u2['balance'])}*",
                    parse_mode="Markdown", reply_markup=kb_main(msg.from_user.id))
                # Thông báo admin
                for aid in get_admin_list():
                    try:
                        bot.send_message(aid,
                            f"💳 *THẺ DUYỆT TỰ ĐỘNG*\n"
                            f"┃ `{the_id}` | {nha_mang} {fmt(menh_gia)}\n"
                            f"┃ 👤 {tc['name'] if tc else uid}\n"
                            f"┃ 💵 +{fmt(gia_thu)}",
                            parse_mode="Markdown")
                    except Exception:
                        pass

            elif status == 2:  # ⏳ Đang xử lý
                if tc: tc["status"] = "processing"
                save(d)
                bot.send_message(int(uid),
                    f"⏳ *Thẻ đang xử lý...*\n"
                    f"🆔 Mã: `{the_id}`\n"
                    f"Bot sẽ tự cộng tiền khi xong!",
                    parse_mode="Markdown")

            else:  # ❌ Thất bại
                msg_err = r.get("message", "Thẻ không hợp lệ")
                if tc: tc["status"] = "failed"
                save(d)
                bot.send_message(int(uid),
                    f"*❌ NẠP THẺ THẤT BẠI*\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📱 {nha_mang} | {fmt(menh_gia)}\n"
                    f"⚠️ Lý do: _{msg_err}_\n\n"
                    f"Liên hệ admin nếu cần hỗ trợ!",
                    parse_mode="Markdown", reply_markup=kb_main(msg.from_user.id))
                for aid in get_admin_list():
                    try:
                        bot.send_message(aid,
                            f"❌ *THẺ THẤT BẠI*\n"
                            f"┃ `{the_id}` | {nha_mang} {fmt(menh_gia)}\n"
                            f"┃ 👤 {tc['name'] if tc else uid}\n"
                            f"┃ ⚠️ {msg_err}",
                            parse_mode="Markdown")
                    except Exception:
                        pass

    except Exception as e:
        bot.send_message(int(uid),
            f"⚠️ *Lỗi xử lý thẻ!*\n🆔 Mã: `{the_id}`\nLiên hệ admin!",
            parse_mode="Markdown")

# CHẠY BOT
_C_RESET  = "\033[0m"
_C_GREEN  = "\033[92m"
_C_CYAN   = "\033[96m"
_C_YELLOW = "\033[93m"
_C_RED    = "\033[91m"
_C_DIM    = "\033[2m"
_C_BOLD   = "\033[1m"

def _type_out(text, delay=0.012):
    for ch in text:
        print(ch, end="", flush=True)
        time.sleep(delay)
    print()

def _progress_bar(label, duration=0.45, width=28):
    steps = 20
    for i in range(steps + 1):
        filled = int(width * i / steps)
        bar = "█" * filled + "░" * (width - filled)
        pct = int(100 * i / steps)
        print(f"\r  {_C_CYAN}{label:<26}{_C_RESET} [{_C_GREEN}{bar}{_C_RESET}] {pct:>3}%", end="", flush=True)
        time.sleep(duration / steps)
    print()

def _boot_sequence():
    banner = r"""
   ▄████████  ▄████████  ▄██████▄     ███      ▄████████
  ███    ███ ███    ███ ███    ███ ▀█████████▄ ███    ███
  ███    █▀  ███    █▀  ███    ███    ▀███▀▀██ ███    █▀
 ▄███▄▄▄     ███        ███    ███     ███   ▀ ███
▀▀███▀▀▀     ███        ███    ███     ███     ███
  ███    █▄  ███    █▄  ███    ███     ███     ███    █▄
  ███    ███ ███    ███ ███    ███     ███     ███    ███
  ██████████ ████████▀   ▀██████▀     ▄████▀   ████████▀
"""
    print(f"{_C_CYAN}{_C_BOLD}{banner}{_C_RESET}")
    time.sleep(0.2)

    _type_out(f"{_C_DIM}>> Đang xâm nhập hệ thống Telegram Bot Network...{_C_RESET}", delay=0.02)
    print()

    boot_lines = [
        ("SYS", "Đang khởi tạo hệ thống lõi"),
        ("NET", "Thiết lập kết nối Telegram API"),
        ("AUTH", "Xác thực token bot"),
        ("DATA", f"Nạp cơ sở dữ liệu từ {DATA_FILE}"),
        ("SEC", "Kích hoạt tường lửa chống spam"),
        ("OCR", "Nạp module kiểm tra ảnh bill"),
        ("PAY", "Kết nối cổng thanh toán thẻ cào"),
        ("ADMIN", f"Xác nhận quyền Super Admin: {SUPER_ADMIN}"),
    ]
    for tag, label in boot_lines:
        _progress_bar(f"[{tag}] {label}")

    print()
    print(f"  {_C_YELLOW}{'─' * 50}{_C_RESET}")
    print(f"  {_C_GREEN}{_C_BOLD}●  HỆ THỐNG SẴN SÀNG{_C_RESET}  {_C_DIM}{now()}{_C_RESET}")
    print(f"  {_C_YELLOW}{'─' * 50}{_C_RESET}")
    print()


def rental_supervisor():
    """Khôi phục bot thuê từ rental_orders sau khi bot chính/server restart."""
    if os.getenv("RENTAL_CHILD") == "1":
        return
    while True:
        try:
            with _lock:
                d=load(); changed=False
                for ro in d.get("rental_orders", []):
                    if not ro.get("enabled", True):
                        continue
                    exp=ro.get("expires_at")
                    if not exp:
                        # Đơn cũ chưa có hạn: giữ nguyên tương thích, tính từ time nếu có.
                        try:
                            exp=(datetime.datetime.fromisoformat(ro.get("time"))+datetime.timedelta(days=7)).isoformat(timespec="seconds")
                            ro["expires_at"]=exp; changed=True
                        except Exception:
                            continue
                    try:
                        if datetime.datetime.now() >= datetime.datetime.fromisoformat(exp):
                            if ro.get("status") != "expired": ro["status"]="expired"; changed=True
                            continue
                    except Exception:
                        continue
                    pid=ro.get("pid")
                    if not process_alive(pid):
                        try:
                            proc=launch_rental_bot(ro.get("bot_token",""), int(ro.get("admin_id",0)), ro.get("id","RENT"), 7, exp, {
                                "qr_url":ro.get("bank_qr_url",""), "account":ro.get("bank_account",""),
                                "account_name":ro.get("bank_account_name",""), "bank_name":ro.get("bank_name","")})
                            ro["pid"]=proc.pid; ro["status"]="success"; changed=True
                            print(f"[RENTAL] Restored {ro.get('id')} PID={proc.pid}")
                        except Exception as e:
                            ro["status"]="error"; ro["last_error"]=str(e)[:300]; changed=True
                if changed: save(d)
        except Exception as e:
            print(f"[RENTAL SUPERVISOR] {e}")
        time.sleep(10)

def expiry_checker():
    while True:
        try:
            with _lock:
                d=load(); changed=False
                for order in d.get("orders",[]):
                    if order.get("status")=="active" and key_expired(order):
                        order["status"]="expired"; changed=True
                        try:
                            bot.send_message(int(order["uid"]),f"*⏰ KEY ĐÃ HẾT HẠN*\n\n🔑 Gói: *{order.get('product','N/A')}*\n🧾 Mã: `{order.get('id','N/A')}`",parse_mode="Markdown")
                        except Exception: pass
                if changed: save(d)
        except Exception as e: print(f"[EXPIRY] {e}")
        time.sleep(60)

def rental_shutdown_checker():
    if not RENTAL_END_AT:
        return
    try:
        end=datetime.datetime.fromisoformat(RENTAL_END_AT)
    except Exception:
        return
    while datetime.datetime.now() < end:
        time.sleep(min(60, max(1, int((end-datetime.datetime.now()).total_seconds()))))
    print("[RENTAL] Gói thuê đã hết hạn, bot sẽ dừng.")
    os._exit(0)

if __name__ == "__main__":
    # Migration bank config:
    # - Bot MẸ: ghi đè bằng constants cố định (BANK_QR_URL, BANK_ACCOUNT_NAME, BANK_NAME).
    # - Bot THUÊ (RENTAL_CHILD=1): ghi bank config từ ENV vars do bot mẹ truyền vào,
    #   KHÔNG dùng constants của bot mẹ — tránh hiện QR/tên sai cho người thuê.
    try:
        with _lock:
            _d = load()
            _cfg = _d.setdefault("bank_config", {})
            changed = False
            if os.getenv("RENTAL_CHILD") == "1":
                # Bot thuê: ưu tiên ENV vars truyền từ launch_rental_bot
                _env_qr   = os.getenv("BANK_QR_URL", "").strip()
                _env_acc  = os.getenv("BANK_ACCOUNT", "").strip()
                _env_name = os.getenv("BANK_ACCOUNT_NAME", "").strip()
                _env_bank = os.getenv("BANK_NAME", "").strip()
                if _env_qr   and _cfg.get("qr_url")       != _env_qr:   _cfg["qr_url"]       = _env_qr;   changed = True
                if _env_acc  and _cfg.get("account")       != _env_acc:  _cfg["account"]       = _env_acc;  changed = True
                if _env_name and _cfg.get("account_name")  != _env_name: _cfg["account_name"]  = _env_name; changed = True
                if _env_bank and _cfg.get("bank_name")     != _env_bank: _cfg["bank_name"]     = _env_bank; changed = True
            else:
                # Bot mẹ: dùng constants cố định
                if _cfg.get("qr_url")      != BANK_QR_URL:       _cfg["qr_url"]      = BANK_QR_URL;       changed = True
                if _cfg.get("account_name")!= BANK_ACCOUNT_NAME: _cfg["account_name"]= BANK_ACCOUNT_NAME; changed = True
                if _cfg.get("bank_name")   != BANK_NAME:         _cfg["bank_name"]   = BANK_NAME;         changed = True
                if not _cfg.get("account") and BANK_ACCOUNT:     _cfg["account"]     = BANK_ACCOUNT;      changed = True
            if changed:
                save(_d)
    except Exception as _e:
        print(f"[BANK CONFIG] {_e}")

    if RENTAL_END_AT and datetime.datetime.now() >= datetime.datetime.fromisoformat(RENTAL_END_AT):
        raise SystemExit(0)
    _boot_sequence()
    threading.Thread(target=expiry_checker, daemon=True).start()
    threading.Thread(target=rental_supervisor, daemon=True).start()
    if RENTAL_END_AT:
        threading.Thread(target=rental_shutdown_checker, daemon=True).start()

    try:
        bot.set_my_commands([
            types.BotCommand("start", "🏠 Mở menu chính"),
            types.BotCommand("nap", "💰 Nạp tiền tự động"),
            types.BotCommand("napthecao", "💳 Nạp thẻ cào"),
            types.BotCommand("muahang", "🛒 Mua acc"),
            types.BotCommand("don", "📦 Đơn của tôi"),
            types.BotCommand("sodu", "👜 Xem số dư ví"),
            types.BotCommand("huongdan", "❓ Hướng dẫn sử dụng"),
        ])
        print("  [ CMD ]    Đã đăng ký menu lệnh Telegram")
    except Exception as e:
        print(f"  [ CMD ]    Lỗi đăng ký menu lệnh: {e}")

    print()
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)
        except Exception as e:
            print(f"[LỖI] {e} — Restart sau 5s...")
            time.sleep(5)
