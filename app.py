import os
from datetime import datetime
from functools import wraps
from abc import ABC, abstractmethod
from typing import Optional
 
from flask import (
    Flask, request, redirect, url_for, session, flash,
    render_template_string, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import escape
 
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-development-key-change-in-render")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
 
# ----------------------------- MODELS -----------------------------
class User(ABC):
    def __init__(self, user_id: int, username: str, password: str, name: str):
        self.__user_id = user_id
        self.__username = username
        self.__password_hash = generate_password_hash(password)
        self.__name = name
 
    @property
    def user_id(self): return self.__user_id
 
    @property
    def username(self): return self.__username
 
    @property
    def name(self): return self.__name
 
    @property
    def avatar_url(self):
        """Role-specific sample profile portrait."""
        return {
            "Administrator": "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=240&q=85",
            "Staff": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=240&q=85",
            "Customer": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=240&q=85",
        }.get(self.role, "")
 
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.__password_hash, password)
 
    @property
    @abstractmethod
    def role(self): ...
 
    @property
    @abstractmethod
    def dashboard_title(self): ...
 
 
class Administrator(User):
    @property
    def role(self): return "Administrator"
    @property
    def dashboard_title(self): return "Command Center"
 
 
class Staff(User):
    @property
    def role(self): return "Staff"
    @property
    def dashboard_title(self): return "Inventory Control"
 
 
class Customer(User):
    @property
    def role(self): return "Customer"
    @property
    def dashboard_title(self): return "Gadget Store"
 
 
class Gadget:
    def __init__(self, gadget_id, name, category, price, stock, icon="□", image_url=""):
        self.id = int(gadget_id)
        self.name = name
        self.category = category
        self.price = float(price)
        self.stock = int(stock)
        self.icon = icon
        self.image_url = image_url.strip()
 
    def update(self, name, category, price, stock, icon, image_url=""):
        if not name.strip() or not category.strip():
            raise ValueError("Name and category are required.")
        price, stock = float(price), int(stock)
        if price < 0 or stock < 0:
            raise ValueError("Price and stock cannot be negative.")
        self.name, self.category = name.strip(), category.strip()
        self.price, self.stock = price, stock
        self.icon = icon.strip() or "□"
        self.image_url = image_url.strip()
 
    def sell(self, quantity):
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        if quantity > self.stock:
            raise ValueError("Not enough stock available.")
        self.stock -= quantity
 
 
# Demo data is held in memory and resets when the app restarts.
users = [
    Administrator(1, "admin", "admin123", "System Administrator"),
    Staff(2, "staff", "staff123", "Gadget Staff"),
    Customer(3, "customer", "customer123", "Demo Customer"),
]
gadgets = [
    Gadget(1, "iPhone 15", "Smartphone", 42990, 8, "▣", "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=900&q=85"),
    Gadget(2, "MacBook Air M2", "Laptop", 54990, 5, "▱", "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=900&q=85"),
    Gadget(3, "Galaxy Watch 6", "Smartwatch", 14990, 10, "◷", "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=85"),
    Gadget(4, "AirPods Pro", "Audio", 13990, 12, "♫", "https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1?auto=format&fit=crop&w=900&q=85"),
    Gadget(5, "iPad Air", "Tablet", 36990, 7, "▤", "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=900&q=85"),
    Gadget(6, "Sony Camera", "Camera", 45990, 4, "◎", "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=900&q=85"),
]
orders = []
next_user_id, next_gadget_id, next_order_id = 4, 7, 1
 
 
def get_user_by_username(username):
    return next((u for u in users if u.username.lower() == username.lower()), None)
 
 
def get_user_by_id(user_id):
    return next((u for u in users if u.user_id == user_id), None)
 
 
def get_gadget(gadget_id):
    return next((g for g in gadgets if g.id == gadget_id), None)
 
 
def current_user():
    return get_user_by_id(session.get("user_id")) if session.get("user_id") else None
 
 
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped
 
 
def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if user.role not in roles:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator
 
 
def money(value):
    return f"₱{value:,.2f}"
 
 
app.jinja_env.filters["money"] = money
 
def image_markup(gadget):
    """Show the product photo, with its symbol as a fallback."""
    if not gadget.image_url:
        return escape(gadget.icon)
    return (f'<img class="gadget-photo" src="{escape(gadget.image_url)}" alt="{escape(gadget.name)}" '
            f'onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'grid\'">'
            f'<span class="gadget-photo-fallback">{escape(gadget.icon)}</span>')
 
# ----------------------------- DESIGN -----------------------------
BASE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }} | azsyl</title>
<style>
:root{--bg:#f5f5f5;--surface:#fff;--ink:#111;--muted:#686868;--line:#dedede;--dark:#111;--soft:#f0f0f0;--shadow:0 12px 35px rgba(0,0,0,.06)}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;line-height:1.55}
a{color:inherit;text-decoration:none}button,input,select{font:inherit}
.container{width:min(1180px,92%);margin:auto}
.nav{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.96);backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
.nav-inner{min-height:76px;display:flex;align-items:center;justify-content:space-between;gap:20px;padding:12px 0}
.brand{display:flex;align-items:center;gap:12px;font-weight:800;letter-spacing:-.5px;font-size:20px}
.brand-mark{height:40px;width:40px;display:grid;place-items:center;background:#111;color:#fff;border-radius:10px;font-size:20px}
.nav-links{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.nav-links a:not(.btn){padding:9px 12px;border-radius:8px;color:#444;font-size:14px}
.nav-links a:not(.btn):hover{background:var(--soft);color:#000}
.pill,.tag{display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:999px;padding:5px 10px;font-size:12px;font-weight:700;background:#fafafa}
main{padding:34px 0 64px;min-height:calc(100vh - 150px)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:24px;box-shadow:var(--shadow)}
.hero{display:grid;grid-template-columns:1.45fr .75fr;gap:18px}
.hero-card{padding:34px}
.kicker{font-size:11px;text-transform:uppercase;letter-spacing:2px;font-weight:800;color:#666}
h1{font-size:clamp(32px,5vw,52px);line-height:1.08;letter-spacing:-1.8px;margin:9px 0 14px}
h2{font-size:23px;letter-spacing:-.5px;margin:0 0 8px}h3{margin:0 0 8px;font-size:17px}
.muted{color:var(--muted)}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:20px 0}
.stat{background:#fff;border:1px solid var(--line);border-radius:14px;padding:19px}
.stat .number{font-size:27px;font-weight:800;letter-spacing:-.8px;margin-top:4px;overflow-wrap:anywhere}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.gadget{display:flex;flex-direction:column;justify-content:space-between;gap:18px;transition:transform .2s,border-color .2s}
.gadget:hover{transform:translateY(-3px);border-color:#999}
.gadget-visual{height:130px;border-radius:12px;background:#f1f1f1;border:1px solid #e7e7e7;display:grid;place-items:center;font-size:54px;margin-bottom:18px;color:#111}
.gadget-top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
.price{font-size:21px;font-weight:800;letter-spacing:-.4px}
.badge{display:inline-block;border-radius:6px;padding:5px 8px;font-size:11px;font-weight:800;text-transform:uppercase;background:#ededed;color:#222}
.badge.low{background:#f7f0df;color:#73520b}.badge.out{background:#f6e5e5;color:#8b2020}
.actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:14px}
.btn{display:inline-flex;justify-content:center;align-items:center;gap:7px;padding:10px 15px;border:1px solid #111;border-radius:8px;background:#111;color:#fff;font-weight:700;font-size:13px;cursor:pointer;transition:background .2s,transform .2s}
.btn:hover{background:#333;transform:translateY(-1px)}
.btn.secondary{background:#fff;color:#111;border-color:#d0d0d0;box-shadow:none}.btn.secondary:hover{background:#f3f3f3}
.btn.danger{background:#fff;color:#8b2020;border-color:#e2bcbc}.btn.danger:hover{background:#fbefef}
.btn:disabled{opacity:.5;cursor:not-allowed;transform:none}
.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
label{display:block;font-size:12px;font-weight:700;color:#444;margin:0 0 7px}
input,select{width:100%;padding:12px 13px;border-radius:8px;border:1px solid #d3d3d3;background:#fff;color:#111;outline:none}
input:focus,select:focus{border-color:#111;box-shadow:0 0 0 3px rgba(0,0,0,.08)}
.full{grid-column:1/-1}.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;min-width:650px}
th,td{text-align:left;padding:14px 12px;border-bottom:1px solid #e8e8e8;font-size:14px;vertical-align:middle}
th{font-size:11px;color:#666;text-transform:uppercase;letter-spacing:1px;background:#fafafa}
tr:last-child td{border-bottom:0}
.flash{padding:13px 16px;border-radius:9px;margin-bottom:15px;border:1px solid var(--line);background:#fff}
.flash.success{border-left:4px solid #222}.flash.warning{border-left:4px solid #888}.flash.danger{border-left:4px solid #a22}.flash.info{border-left:4px solid #555}
.section-head{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;margin:6px 0 18px}
.search{max-width:320px;width:100%}.login-page{min-height:calc(100vh - 100px);display:grid;place-items:center;padding:20px 0}
.login-card{width:min(450px,100%);text-align:left}.logo-orb{height:58px;width:58px;display:grid;place-items:center;border-radius:14px;background:#111;color:#fff;font-size:26px;margin-bottom:22px}
.empty{text-align:center;padding:44px 20px;color:var(--muted)}.footer{text-align:center;color:#777;padding:24px;border-top:1px solid var(--line);font-size:12px}
.progress{height:7px;background:#e9e9e9;border-radius:99px;overflow:hidden;margin-top:12px}.progress span{height:100%;display:block;background:#111}
.order-card{display:grid;grid-template-columns:1fr auto;gap:15px;align-items:center}
.role-card{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:20px}
.role{border:1px solid var(--line);padding:15px;border-radius:12px;background:#fafafa}
@media(max-width:850px){.hero{grid-template-columns:1fr}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.stats{grid-template-columns:repeat(2,1fr)}.nav-inner{align-items:flex-start;flex-direction:column}.nav-links{width:100%}}
@media(max-width:600px){.grid,.role-card,.form-grid{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.hero-card{padding:24px}.section-head{align-items:flex-start;flex-direction:column}.search{max-width:none}.order-card{grid-template-columns:1fr}.order-card>div:last-child{text-align:left!important}.stat .number{font-size:23px}}
 
/* AZSYL DARK THEME + RIGHT-SIDE SIDEBAR */
:root{--bg:#080808;--surface:#151515;--ink:#f5f5f5;--muted:#aaa;--line:#303030;--dark:#000;--soft:#242424;--shadow:0 14px 38px rgba(0,0,0,.24)}
body{background:var(--bg);color:var(--ink)}
.nav.sidebar{position:fixed;top:0;right:0;bottom:0;width:252px;height:100vh;z-index:50;background:#050505;border-left:1px solid #292929;padding:25px 18px;display:flex;flex-direction:column;justify-content:flex-start;gap:0;overflow-y:auto}
.sidebar-brand{padding:4px 8px 28px;border-bottom:1px solid #292929}
.brand{color:#fff}
.brand-mark{background:#fff;color:#050505;border-radius:12px;font-weight:900}
.sidebar-caption{font-size:9px;letter-spacing:1.7px;color:#777;margin:13px 0 0 2px;font-weight:800}
.sidebar-section{font-size:10px;letter-spacing:1.7px;color:#666;font-weight:800;padding:25px 10px 10px}
.nav-links{display:flex;flex-direction:column;align-items:stretch;gap:6px;width:100%}
.nav-links a:not(.btn){display:flex;align-items:center;gap:12px;width:100%;padding:13px 12px;border-radius:10px;color:#bdbdbd;font-size:14px;border:1px solid transparent;transition:background .18s,color .18s}
.nav-links a:not(.btn):hover{background:#202020;color:#fff;border-color:#303030}
.nav-icon{width:22px;display:inline-grid;place-items:center;font-size:18px;color:#999;flex:0 0 22px}
.sidebar-bottom{margin-top:auto;padding-top:22px;border-top:1px solid #292929}
.user-summary{display:flex;align-items:center;gap:10px;padding:8px 4px 18px;min-width:0}
.user-avatar{height:42px;width:42px;display:block;object-fit:cover;border-radius:50%;border:2px solid #3e9cff;box-shadow:0 0 16px #258bff33;flex:0 0 42px;background:#10213b}
.user-summary b{display:block;font-size:12px;color:#eee;overflow-wrap:anywhere}
.user-summary small{display:block;color:#888;font-size:11px;margin-top:3px}
.logout-link{display:flex;align-items:center;gap:12px;padding:12px;border-radius:10px;color:#bbb;font-size:13px}
.logout-link:hover{background:#202020;color:#fff}
main.container{width:auto;max-width:none;margin:0 280px 0 0;padding:34px 30px 64px;min-height:calc(100vh - 90px)}
.footer{margin-right:252px;border-top-color:#292929;color:#777}
.card,.stat,.role{background:#151515;border-color:#303030;box-shadow:0 12px 32px rgba(0,0,0,.18)}
.kicker,label,th{color:#aaa}
h1,h2,h3,strong,b{color:#f5f5f5}
.muted{color:#aaa}
.stat{background:#121212}
.gadget-visual{background:#202020;border-color:#333;color:#fff}
.tag,.pill{background:#202020;border-color:#393939;color:#ddd}
.btn{background:#f5f5f5;color:#090909;border-color:#f5f5f5}
.btn:hover{background:#dcdcdc;color:#000}
.btn.secondary{background:#1b1b1b;color:#eee;border-color:#414141}
.btn.secondary:hover{background:#292929}
.btn.danger{background:#211515;color:#ffbaba;border-color:#5a3434}
input,select{background:#202020;color:#f5f5f5;border-color:#3b3b3b}
input:focus,select:focus{border-color:#aaa;box-shadow:0 0 0 3px rgba(255,255,255,.08)}
th{background:#202020;color:#bbb}
th,td{border-bottom-color:#303030}
.flash{background:#171717;border-color:#333;color:#eee}
.flash.success{border-left-color:#aaa}.flash.warning{border-left-color:#777}.flash.danger{border-left-color:#d77}.flash.info{border-left-color:#888}
.badge{background:#303030;color:#eee}
.badge.low{background:#392f1b;color:#f0d38b}.badge.out{background:#3a2020;color:#ffbaba}
.progress{background:#303030}.progress span{background:#eee}
.role{background:#1b1b1b}
@media(max-width:850px){
  .nav.sidebar{width:215px;padding:22px 13px}
  main.container{margin-right:235px;padding:28px 18px 50px}
  .footer{margin-right:215px}
}
@media(max-width:600px){
  .nav.sidebar{width:168px;padding:18px 9px}
  .brand{font-size:17px;gap:8px}.brand-mark{width:34px;height:34px}
  .sidebar-caption{font-size:8px;letter-spacing:1px}
  .nav-links a:not(.btn){padding:12px 8px;gap:7px;font-size:12px}
  .nav-icon{width:18px;flex-basis:18px;font-size:15px}
  main.container{margin-right:180px;padding:22px 12px 42px;width:auto}
  .footer{margin-right:168px}
  .stats{grid-template-columns:1fr}
}
 
 
/* AZSYL BLUE-BLACK PREMIUM THEME + LEFT SIDEBAR + ANIMATIONS */
:root{--bg:#050914;--surface:#0b1425;--ink:#f3f7ff;--muted:#9cacc7;--line:#1d3150;--dark:#020611;--soft:#10213b;--shadow:0 18px 48px rgba(0,0,0,.32)}
body{background:radial-gradient(ellipse at 75% 0%,#10254a 0%,#050914 48%,#030610 100%);color:var(--ink);overflow-x:hidden}
body.guest main.container{margin:0 auto;max-width:1180px;padding:34px 4% 64px}
body.guest .footer{margin:0}
.logo-orb{background:linear-gradient(135deg,#39a5ff,#2357e8);box-shadow:0 0 24px #1764db55}
.nav.sidebar{left:0;right:auto;background:linear-gradient(180deg,#071225 0%,#030711 100%);border-left:0;border-right:1px solid #1b3760;box-shadow:12px 0 40px rgba(0,0,0,.2)}
.sidebar-brand{border-bottom-color:#1d3150}
.brand{color:#f4f8ff;letter-spacing:2px;text-transform:uppercase;font-size:22px}
.brand-mark{background:linear-gradient(135deg,#39a5ff,#2357e8);color:white;box-shadow:0 0 22px #1764db66}
.sidebar-caption{color:#4e9dff}
.sidebar-section{color:#6381ad}
.nav-links a:not(.btn){color:#b7c8e5}
.nav-links a:not(.btn):hover,.nav-links a:not(.btn):focus{background:#10264a;color:#fff;border-color:#245ca8;box-shadow:inset 3px 0 #3d9dff}
.nav-icon{color:#67aaff}
.sidebar-bottom{border-top-color:#1d3150}
.user-avatar{background:linear-gradient(135deg,#39a5ff,#2357e8);color:#fff}
main.container{margin:0 0 0 280px;padding:34px 30px 64px}
.footer{margin-left:252px;margin-right:0;border-top-color:#1d3150;color:#7186a8}
.card,.stat,.role{background:linear-gradient(145deg,rgba(13,27,49,.97),rgba(7,15,29,.98));border-color:#1b3152;box-shadow:0 14px 40px rgba(0,0,0,.2)}
.kicker,label,th{color:#78b4ff}
h1,h2,h3,strong,b{color:#f4f8ff}
.muted{color:#9cacc7}
.stat{background:#0a1426}
.btn{background:linear-gradient(135deg,#2f9bff,#2458e8);color:white;border-color:#348cff;box-shadow:0 6px 20px #145bd833}
.btn:hover{background:linear-gradient(135deg,#59b0ff,#3973ff);color:white}
.btn.secondary{background:#0d1a30;color:#dceaff;border-color:#28466e}
.btn.secondary:hover{background:#14294a}
.btn.danger{background:#291522;color:#ffc0d0;border-color:#71344f}
input,select{background:#071225;color:#f3f7ff;border-color:#29466c}
input:focus,select:focus{border-color:#3e9cff;box-shadow:0 0 0 3px #258bff26}
th{background:#0d1c33;color:#a9c9f5}th,td{border-bottom-color:#1d3150}
.flash{background:#0b172a;border-color:#1d3150;color:#e7f1ff}
.flash.success{border-left-color:#3eafff}.flash.warning{border-left-color:#e5bd62}.flash.danger{border-left-color:#ff728f}.flash.info{border-left-color:#579dff}
.badge{background:#183151;color:#dceaff}.badge.low{background:#3b321b;color:#f0d38b}.badge.out{background:#3a202c;color:#ffbaba}
.progress{background:#1a2b45}.progress span{background:linear-gradient(90deg,#2677ff,#49c5ff)}
.gadget-visual{background:#10213b;border-color:#25456d;color:#a5d2ff}
.gadget-photo{width:100%;height:100%;object-fit:cover;border-radius:inherit;display:block}.gadget-visual:has(.gadget-photo){padding:0;overflow:hidden}.gadget-photo-fallback{display:none;height:100%;place-items:center;font-size:54px}
.role{background:#0b1930}
/* Subtle entrance and hover motion */
@keyframes riseIn{from{opacity:0;transform:translateY(22px)}to{opacity:1;transform:translateY(0)}}
@keyframes glowPulse{0%,100%{box-shadow:0 0 0 rgba(43,142,255,0)}50%{box-shadow:0 0 30px rgba(43,142,255,.16)}}
main.container>*{animation:riseIn .65s cubic-bezier(.2,.7,.2,1) both}
main.container>*:nth-child(2){animation-delay:.08s}main.container>*:nth-child(3){animation-delay:.15s}main.container>*:nth-child(4){animation-delay:.22s}
.hero-card{position:relative;overflow:hidden;animation:riseIn .8s ease-out both,glowPulse 5s ease-in-out 1s infinite}
.hero-card:after{content:"";position:absolute;top:-40%;right:-15%;width:300px;height:300px;border-radius:50%;background:radial-gradient(circle,#1685ff24,transparent 68%);pointer-events:none}
.brand,.brand-mark,.btn,.nav-links a:not(.btn),.card,.stat{transition:all .25s ease}
.card:hover,.stat:hover{border-color:#2c5c93;transform:translateY(-2px)}
.intro-title{background:linear-gradient(100deg,#fff 15%,#82c6ff 48%,#397dff 75%,#fff);background-size:220% auto;color:transparent;-webkit-background-clip:text;background-clip:text;animation:titleShimmer 5s linear infinite}
@keyframes titleShimmer{to{background-position:220% center}}
@media(max-width:850px){.nav.sidebar{width:215px;padding:22px 13px}main.container{margin-left:235px;padding:28px 18px 50px}.footer{margin-left:215px}}
@media(max-width:600px){.nav.sidebar{width:168px;padding:18px 9px}.brand{font-size:17px;gap:8px}.brand-mark{width:34px;height:34px}.sidebar-caption{font-size:8px;letter-spacing:1px}.nav-links a:not(.btn){padding:12px 8px;gap:7px;font-size:12px}.nav-icon{width:18px;flex-basis:18px;font-size:15px}main.container{margin-left:180px;padding:22px 12px 42px;width:auto}.footer{margin-left:168px}.stats{grid-template-columns:1fr}}
/* Profile portraits and gadget showcase on the welcome page */
.profile-panel{display:flex;align-items:center;gap:18px;margin:0 0 20px;padding:18px 22px}
.profile-large{width:76px;height:76px;flex:0 0 76px;object-fit:cover;border-radius:50%;border:3px solid #3e9cff;box-shadow:0 0 28px #258bff33}
.profile-role{display:inline-flex;padding:5px 10px;border-radius:999px;background:#10294b;border:1px solid #245ca8;color:#9dceff;font-size:11px;font-weight:800;letter-spacing:1px;text-transform:uppercase}
.intro-layout{display:grid;grid-template-columns:1.05fr .95fr;gap:30px;align-items:center}
.intro-showcase{position:relative;min-height:310px;border:1px solid #24466f;border-radius:22px;padding:15px;background:linear-gradient(145deg,#10294b,#071225);overflow:hidden}
.intro-showcase:before{content:"";position:absolute;width:220px;height:220px;right:-60px;top:-80px;background:#319dff22;filter:blur(10px);border-radius:50%}
.showcase-grid{position:relative;display:grid;grid-template-columns:1fr 1fr;gap:12px}
.showcase-item{height:135px;border-radius:14px;overflow:hidden;border:1px solid #31557f;background:#071225;animation:riseIn .7s ease both}
.showcase-item:nth-child(2){animation-delay:.1s}.showcase-item:nth-child(3){animation-delay:.18s}.showcase-item:nth-child(4){animation-delay:.26s}
.showcase-item img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .4s ease}
.showcase-item:hover img{transform:scale(1.07)}
.intro-quote{margin-top:20px;padding:14px 16px;border-left:3px solid #42a5ff;background:#0b1d35;border-radius:0 12px 12px 0;color:#d9eaff;font-size:15px;font-weight:650}
@media(max-width:750px){.intro-layout{grid-template-columns:1fr}.intro-showcase{min-height:0}.showcase-item{height:115px}.profile-panel{align-items:flex-start}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;scroll-behavior:auto!important;transition:none!important}}
 
 
/* Minimal, card-free welcome screen */
body.guest{background:radial-gradient(ellipse at 75% 45%,#10294b 0%,#081426 35%,#050b16 72%);}
body.guest main.container{width:100%;max-width:none;margin:0;padding:0 5vw;min-height:100vh;display:flex;flex-direction:column;justify-content:center;}
body.guest main.container>.welcome-clean{animation:riseIn .7s ease both;}
.welcome-clean{width:100%;max-width:1240px;min-height:76vh;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;align-items:center;gap:5vw;position:relative;}
.welcome-copy{position:relative;z-index:2;padding:32px 0;}
.welcome-eyebrow{display:flex;align-items:center;gap:10px;color:#a9c9f5;font-size:11px;font-weight:800;letter-spacing:3px;margin-bottom:24px;}
.welcome-dot{width:7px;height:7px;border-radius:50%;background:#5db7ff;box-shadow:0 0 14px #5db7ff;}
.welcome-logo{margin:0;font-size:clamp(64px,10vw,118px);line-height:.98;letter-spacing:-5px;font-weight:900;color:#f6f9ff;}
.welcome-logo span{color:#4aa9ff;}
.welcome-heading{margin:24px 0 14px;font-size:clamp(30px,4vw,49px);line-height:1.12;letter-spacing:-1.6px;color:#f4f8ff;}
.welcome-heading span{color:#75bdff;}
.welcome-description{max-width:480px;font-size:16px;line-height:1.8;color:#aab8ce;margin:0;}
.welcome-quote{margin:22px 0 28px;color:#e0ebfb;font-size:15px;font-weight:650;}
.welcome-cta{display:inline-flex;align-items:center;gap:30px;padding:15px 23px;border-radius:999px;background:#f3f7ff;color:#071225;font-weight:800;text-decoration:none;box-shadow:0 8px 30px #0002;transition:transform .2s ease,background .2s ease;}
.welcome-cta:hover{transform:translateY(-3px);background:#78c2ff;color:#071225;}
.welcome-cta span{font-size:20px;line-height:1;}
.welcome-login-note{margin:17px 0 0;font-size:13px;color:#8292aa;}
.welcome-login-note a{color:#d8e9ff;text-decoration:underline;text-underline-offset:3px;}
.welcome-gadgets{min-height:390px;position:relative;display:flex;align-items:center;justify-content:center;isolation:isolate;}
.welcome-gadgets:before{content:"";position:absolute;width:min(35vw,420px);aspect-ratio:1;border-radius:50%;background:radial-gradient(circle,#2e82d84a 0%,#1c579322 45%,transparent 72%);z-index:-1;}
.welcome-gadgets img{display:block;object-fit:cover;box-shadow:0 24px 65px #0006;transition:transform .35s ease;}
.welcome-gadgets img:hover{transform:translateY(-8px) rotate(0deg);}
.welcome-phone{width:28%;height:260px;border-radius:22px;transform:rotate(-8deg);z-index:2;}
.welcome-laptop{width:66%;height:290px;border-radius:16px;transform:rotate(3deg);margin-left:-4%;z-index:1;}
.welcome-watch{position:absolute;width:23%;height:130px;object-position:center;border-radius:50%;right:1%;bottom:4%;transform:rotate(8deg);z-index:3;}
.welcome-footer{text-align:center;color:#63748d;font-size:11px;letter-spacing:.5px;margin:0 auto 20px;}
.welcome-footer span{color:#a9c9f5;margin-left:7px;font-weight:800;letter-spacing:2px;}
@media(max-width:760px){body.guest main.container{padding:0 24px;min-height:100vh}.welcome-clean{grid-template-columns:1fr;gap:0;min-height:auto;padding:54px 0 20px}.welcome-copy{padding:0;text-align:center}.welcome-eyebrow{justify-content:center;font-size:9px;letter-spacing:2px}.welcome-logo{font-size:clamp(64px,18vw,96px);letter-spacing:-3px}.welcome-heading{font-size:clamp(30px,8vw,42px)}.welcome-description{margin:0 auto;font-size:14px}.welcome-gadgets{min-height:260px;margin-top:18px}.welcome-phone{height:185px}.welcome-laptop{height:205px}.welcome-watch{height:90px}.welcome-footer{margin-top:8px;padding-bottom:10px}}
@media(prefers-reduced-motion:reduce){.welcome-cta,.welcome-gadgets img{transition:none}}
 
 
/* Blue cloud brand mark: replace the old letter A icon everywhere */
.brand-mark.cloud-mark,.logo-orb.cloud-orb{display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#39baff,#1457ee);border:1px solid #62c8ff;box-shadow:0 0 24px #168bff55,inset 0 1px 0 #ffffff55;}
.brand-mark.cloud-mark{width:44px;height:44px;min-width:44px;border-radius:14px;padding:5px;}
.logo-orb.cloud-orb{width:62px;height:62px;border-radius:18px;padding:9px;margin-bottom:22px;}
.cloud-logo{display:block;width:100%;height:100%;filter:drop-shadow(0 2px 5px #001b4c66);}
@media(max-width:600px){.brand-mark.cloud-mark{width:34px;height:34px;min-width:34px;padding:4px}.logo-orb.cloud-orb{width:56px;height:56px}}
 
</style>
</head>
<body class="{{ 'signed-in' if current_user else 'guest' }}">
{% if current_user %}
<aside class="nav sidebar">
  <div class="sidebar-brand">
    <a class="brand" href="{{ url_for('dashboard') }}"><span class="brand-mark cloud-mark"><svg class="cloud-logo" viewBox="0 0 64 48" aria-hidden="true" focusable="false"><defs><linearGradient id="cloudBlue" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#65d5ff"/><stop offset="55%" stop-color="#168bff"/><stop offset="100%" stop-color="#3154f4"/></linearGradient></defs><path fill="url(#cloudBlue)" d="M18 42C8 42 2 35 2 26S9 10 19 10C23 3 30 0 37 2c8 2 13 8 14 16 7 1 11 6 11 12 0 7-6 12-13 12H18Z"/><path d="M13 31 25 19c2-2 5-2 7 0l5 5 5-5" fill="none" stroke="#06152e" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/><path d="M22 35 32 25l7 7 8-9" fill="none" stroke="#06152e" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/></svg></span><span>AZSYL</span></a>
    
  </div>
  <div class="sidebar-section">WORKSPACE</div>
  <div class="nav-links">
    <a href="{{ url_for('dashboard') }}"><span class="nav-icon">▦</span><span>Dashboard</span></a>
    {% if current_user.role == 'Administrator' %}
    <a href="{{ url_for('manage_gadgets') }}"><span class="nav-icon">▣</span><span>Gadgets</span></a>
    <a href="{{ url_for('manage_users') }}"><span class="nav-icon">♙</span><span>Users</span></a>
    <a href="{{ url_for('manage_orders') }}"><span class="nav-icon">☷</span><span>Orders</span></a>
    {% elif current_user.role == 'Staff' %}
    <a href="{{ url_for('manage_gadgets') }}"><span class="nav-icon">▣</span><span>Inventory</span></a>
    <a href="{{ url_for('manage_orders') }}"><span class="nav-icon">☷</span><span>Orders</span></a>
    {% else %}
    <a href="{{ url_for('shop') }}"><span class="nav-icon">▤</span><span>Shop</span></a>
    <a href="{{ url_for('my_orders') }}"><span class="nav-icon">☷</span><span>My Orders</span></a>
    {% endif %}
  </div>
  <div class="sidebar-bottom">
    <div class="user-summary"><img class="user-avatar" src="{{ current_user.avatar_url }}" alt="{{ current_user.role }} profile photo" onerror="this.style.display='none'"><div><b>{{ current_user.name }}</b><small>{{ current_user.role }} · AZSYL</small></div></div>
    <a class="logout-link" href="{{ url_for('logout') }}"><span class="nav-icon">↪</span><span>Log out</span></a>
  </div>
</aside>
{% endif %}
<main class="container">
{% with messages = get_flashed_messages(with_categories=true) %}{% for category,message in messages %}
<div class="flash {{ category }}" role="status">{{ message }}</div>
{% endfor %}{% endwith %}
{{ content|safe }}
</main>
{% if current_user %}<footer class="footer">AZSYL · {{ now.year }}</footer>{% endif %}
</body></html>
"""
 
 
def page(content, title="azsyl"):
    return render_template_string(
        BASE, content=content, title=title, current_user=current_user(),
        now=datetime.now()
    )
 
 
@app.route("/")
def index():
    # Intro / welcome page shown before login.
    if current_user():
        return redirect(url_for("dashboard"))
    content = """
    <section class="welcome-clean">
      <div class="welcome-copy">
        <div class="welcome-eyebrow"><span class="welcome-dot"></span> YOUR EVERYDAY TECH STORE</div>
        <h1 class="welcome-logo">AZSYL<span>.</span></h1>
        <h2 class="welcome-heading">Tech that fits <span>your life.</span></h2>
        <p class="welcome-description">Discover the gadgets you love — from everyday essentials to your next big upgrade.</p>
        <p class="welcome-quote">“Make every day a little smarter.”</p>
        <a class="welcome-cta" href="/login">Get Started <span aria-hidden="true">→</span></a>
        <p class="welcome-login-note">Already have an account? <a href="/login">Log in</a></p>
      </div>
      <div class="welcome-gadgets" aria-label="Smartphone, laptop, smartwatch, and earbuds">
        <img class="welcome-phone" src="https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=650&q=85" alt="Smartphone" loading="lazy">
        <img class="welcome-laptop" src="https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=900&q=85" alt="Laptop" loading="lazy">
        <img class="welcome-watch" src="https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=500&q=85" alt="Smartwatch" loading="lazy">
      </div>
    </section>
    <p class="welcome-footer">Find what you need. Love what you choose. <span>AZSYL</span></p>
    """
    return page(content, "Welcome")
 
 
@app.route("/signup", methods=["GET", "POST"])
def signup():
    global next_user_id
    if current_user():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not name or not username or not password:
            flash("Please complete all required fields.", "danger")
        elif len(username) < 3:
            flash("Username must be at least 3 characters.", "danger")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        elif get_user_by_username(username):
            flash("Username already exists. Choose another username.", "danger")
        else:
            # Public registration creates customer accounts only.
            users.append(Customer(next_user_id, username, password, name))
            next_user_id += 1
            flash("Account created. You can now log in.", "success")
            return redirect(url_for("login"))
    content = """
    <div class="login-page"><section class="card login-card">
      <div class="logo-orb cloud-orb"><svg class="cloud-logo" viewBox="0 0 64 48" aria-hidden="true" focusable="false"><defs><linearGradient id="cloudBlue" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#65d5ff"/><stop offset="55%" stop-color="#168bff"/><stop offset="100%" stop-color="#3154f4"/></linearGradient></defs><path fill="url(#cloudBlue)" d="M18 42C8 42 2 35 2 26S9 10 19 10C23 3 30 0 37 2c8 2 13 8 14 16 7 1 11 6 11 12 0 7-6 12-13 12H18Z"/><path d="M13 31 25 19c2-2 5-2 7 0l5 5 5-5" fill="none" stroke="#06152e" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/><path d="M22 35 32 25l7 7 8-9" fill="none" stroke="#06152e" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div class="kicker">CREATE AN ACCOUNT</div>
      <h1 style="font-size:38px">Join azsyl</h1><p class="muted">Create a customer account to browse gadgets and track orders.</p>
      <form method="post" style="margin-top:24px">
        <label>Full name</label><input name="name" autocomplete="name" required>
        <label style="margin-top:14px">Username</label><input name="username" autocomplete="username" minlength="3" required>
        <label style="margin-top:14px">Password</label><input type="password" name="password" autocomplete="new-password" minlength="8" required>
        <label style="margin-top:14px">Confirm password</label><input type="password" name="confirm_password" autocomplete="new-password" minlength="8" required>
        <button class="btn" style="width:100%;margin-top:20px">Create account</button>
      </form><p class="muted" style="text-align:center;margin-top:18px">Already have an account? <a href="/login"><b>Log in</b></a></p>
    </section></div>"""
    return page(content, "Sign Up")
 
 
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_user_by_username(username)
        if user and user.check_password(password):
            session.clear()
            session["user_id"] = user.user_id
            flash(f"Welcome, {user.name}. You are signed in as {user.role}.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    content = """
    <div class="login-page"><section class="card login-card">
      <div class="logo-orb cloud-orb"><svg class="cloud-logo" viewBox="0 0 64 48" aria-hidden="true" focusable="false"><defs><linearGradient id="cloudBlue" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#65d5ff"/><stop offset="55%" stop-color="#168bff"/><stop offset="100%" stop-color="#3154f4"/></linearGradient></defs><path fill="url(#cloudBlue)" d="M18 42C8 42 2 35 2 26S9 10 19 10C23 3 30 0 37 2c8 2 13 8 14 16 7 1 11 6 11 12 0 7-6 12-13 12H18Z"/><path d="M13 31 25 19c2-2 5-2 7 0l5 5 5-5" fill="none" stroke="#06152e" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/><path d="M22 35 32 25l7 7 8-9" fill="none" stroke="#06152e" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div class="kicker">AZSYL</div>
      <h1 class="intro-title" style="font-size:48px;letter-spacing:3px">AZSYL</h1><p class="muted">Welcome back. Sign in to continue.</p>
      <form method="post" style="margin-top:24px">
        <label>Username</label><input name="username" autocomplete="username" required>
        <label style="margin-top:14px">Password</label><input type="password" name="password" autocomplete="current-password" required>
        <button class="btn" style="width:100%;margin-top:20px">Sign in</button>
      </form><p class="muted" style="text-align:center;margin-top:18px">New to azsyl? <a href="/signup"><b>Create an account</b></a></p>
    </section></div>"""
    return page(content, "Login")
 
 
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))
 
 
@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    pending = sum(o["status"] == "Pending" for o in orders)
    my_orders = [o for o in orders if o["buyer_id"] == user.user_id]
    my_pending = sum(o["status"] == "Pending" for o in my_orders)
 
    quick = {
        "Administrator": '<a class="btn" href="/gadgets">Manage gadgets</a><a class="btn secondary" href="/users">Manage users</a><a class="btn secondary" href="/orders">View orders</a>',
        "Staff": '<a class="btn" href="/gadgets">Manage inventory</a><a class="btn secondary" href="/orders">Process orders</a>',
        "Customer": '<a class="btn" href="/shop">Browse gadgets</a><a class="btn secondary" href="/my-orders">My orders</a>',
    }[user.role]
 
    content = f"""
    <section class="card profile-panel">
      <img class="profile-large" src="{escape(user.avatar_url)}" alt="{escape(user.role)} profile photo" onerror="this.style.display='none'">
      <div><span class="profile-role">{escape(user.role)} PROFILE</span>
      <h2 style="margin:8px 0 2px">{escape(user.name)}</h2>
      <p class="muted" style="margin:0">{'Your personal space to discover and track gadgets.' if user.role == 'Customer' else ('Your workspace for inventory, orders, and daily operations.' if user.role == 'Staff' else 'Your command center for managing the AZSYL system.')}</p></div>
    </section>
    <div class="hero"><section class="card hero-card"><div class="kicker">{escape(user.role)} / {escape(user.dashboard_title)}</div>
      <h1>Hello, {escape(user.name)}.</h1><p class="muted">{'Browse gadgets and keep track of your purchases.' if user.role == 'Customer' else 'Your workspace for gadget inventory, customer orders, and store activity.'}</p>
      <div class="actions">{quick}</div></section>
      <section class="card"><div class="kicker">OVERVIEW</div><h2 style="margin-top:10px">{'Your shopping activity' if user.role == 'Customer' else 'System status'}</h2>
      <p class="muted">{'Review your orders and explore available products.' if user.role == 'Customer' else 'azsyl is ready for your next task.'}</p><div class="progress"><span style="width:100%"></span></div><small class="muted">{'Customer account active' if user.role == 'Customer' else 'Application online'}</small></section></div>
    """
 
    if user.role == "Administrator":
        total_value = sum(g.price * g.stock for g in gadgets)
        content += f"""
        <div class="stats">
          <div class="stat"><div class="muted">Total gadgets</div><div class="number">{len(gadgets)}</div></div>
          <div class="stat"><div class="muted">Stock units</div><div class="number">{sum(g.stock for g in gadgets)}</div></div>
          <div class="stat"><div class="muted">Pending orders</div><div class="number">{pending}</div></div>
          <div class="stat"><div class="muted">Inventory value</div><div class="number" style="font-size:22px">{money(total_value)}</div></div>
        </div>"""
    elif user.role == "Staff":
        content += f"""
        <div class="stats">
          <div class="stat"><div class="muted">Total gadgets</div><div class="number">{len(gadgets)}</div></div>
          <div class="stat"><div class="muted">Stock units</div><div class="number">{sum(g.stock for g in gadgets)}</div></div>
          <div class="stat"><div class="muted">Pending orders</div><div class="number">{pending}</div></div>
        </div>"""
    else:
        content += f"""
        <div class="stats">
          <div class="stat"><div class="muted">Available gadgets</div><div class="number">{sum(g.stock > 0 for g in gadgets)}</div></div>
          <div class="stat"><div class="muted">My orders</div><div class="number">{len(my_orders)}</div></div>
          <div class="stat"><div class="muted">Pending orders</div><div class="number">{my_pending}</div></div>
        </div>"""
 
        recent_orders = sorted(my_orders, key=lambda o: o["id"], reverse=True)[:3]
        if recent_orders:
            order_rows = ""
            for order in recent_orders:
                order_class = {"Pending": "low", "Approved": "", "Rejected": "out"}.get(order["status"], "")
                order_rows += (
                    f'<tr><td>#{order["id"]}</td>'
                    f'<td>{escape(order["gadget_name"])} × {order["quantity"]}</td>'
                    f'<td>{money(order["total"])}</td>'
                    f'<td><span class="badge {order_class}">{order["status"]}</span></td></tr>'
                )
            content += f'<div class="section-head" style="margin-top:30px"><div><h2>Recent orders</h2><div class="muted">Latest updates on your purchases.</div></div><a class="btn secondary" href="/my-orders">All my orders</a></div><section class="card table-wrap"><table><thead><tr><th>Order</th><th>Item</th><th>Total</th><th>Status</th></tr></thead><tbody>{order_rows}</tbody></table></section>'
 
    return page(content, f"{user.dashboard_title}")
 
 
@app.route("/gadgets", methods=["GET", "POST"])
@role_required("Administrator", "Staff")
def manage_gadgets():
    global next_gadget_id
    if request.method == "POST":
        action = request.form.get("action", "")
        try:
            if action == "add":
                name = request.form.get("name", "").strip()
                category = request.form.get("category", "").strip()
                price = float(request.form.get("price", "0"))
                stock = int(request.form.get("stock", "0"))
                icon = request.form.get("icon", "□").strip() or "□"
                image_url = request.form.get("image_url", "").strip()
                if image_url and not image_url.startswith(("https://", "http://")):
                    raise ValueError("Image URL must start with http:// or https://.")
                if not name or not category or price < 0 or stock < 0:
                    raise ValueError("Enter a name, category, valid price, and valid stock.")
                gadgets.append(Gadget(next_gadget_id, name, category, price, stock, icon, image_url))
                next_gadget_id += 1
                flash("Gadget added successfully.", "success")
            elif action == "update":
                gadget = get_gadget(int(request.form.get("id", "")))
                if not gadget: raise ValueError("Gadget not found.")
                image_url = request.form.get("image_url", "").strip()
                if image_url and not image_url.startswith(("https://", "http://")):
                    raise ValueError("Image URL must start with http:// or https://.")
                gadget.update(request.form.get("name", ""), request.form.get("category", ""),
                              request.form.get("price", "0"), request.form.get("stock", "0"),
                              request.form.get("icon", "□"), image_url)
                flash("Gadget updated successfully.", "success")
            elif action == "delete":
                gadget = get_gadget(int(request.form.get("id", "")))
                if not gadget: raise ValueError("Gadget not found.")
                if any(o["gadget_id"] == gadget.id and o["status"] == "Pending" for o in orders):
                    raise ValueError("Cannot delete a gadget with a pending order.")
                gadgets.remove(gadget)
                flash("Gadget deleted successfully.", "success")
            else:
                raise ValueError("Invalid action.")
        except (ValueError, TypeError) as exc:
            flash(str(exc), "danger")
        return redirect(url_for("manage_gadgets"))
 
    editing = get_gadget(request.args.get("edit", type=int)) if request.args.get("edit") else None
    rows = ""
    for g in gadgets:
        status = "OUT OF STOCK" if g.stock == 0 else ("LOW STOCK" if g.stock <= 3 else "AVAILABLE")
        cls = "out" if g.stock == 0 else ("low" if g.stock <= 3 else "")
        rows += f"""<tr><td><div style="display:flex;align-items:center;gap:12px"><div class="gadget-visual" style="width:76px;height:60px;flex:0 0 76px;margin:0;font-size:24px">{image_markup(g)}</div><div><b>{escape(g.name)}</b><br><span class="muted">{escape(g.category)}</span></div></div></td>
        <td>{money(g.price)}</td><td>{g.stock}</td><td><span class="badge {cls}">{status}</span></td><td><div class="actions">
        <a class="btn secondary" href="/gadgets?edit={g.id}">Edit</a><form method="post" onsubmit="return confirm('Delete this gadget?')"><input type="hidden" name="action" value="delete"><input type="hidden" name="id" value="{g.id}"><button class="btn danger">Delete</button></form></div></td></tr>"""
    title = "Edit gadget" if editing else "Add a gadget"
    action = "update" if editing else "add"
    hidden_id = f'<input type="hidden" name="id" value="{editing.id}">' if editing else ""
    name = escape(editing.name) if editing else ""
    category = escape(editing.category) if editing else ""
    price = editing.price if editing else ""
    stock = editing.stock if editing else ""
    icon = escape(editing.icon) if editing else "□"
    image_url = escape(editing.image_url) if editing else ""
    content = f"""<div class="section-head"><div><div class="kicker">INVENTORY CONTROL</div><h1>Gadget manager</h1><p class="muted">Add, update, review, or remove product records.</p></div></div>
    <section class="card"><h2>{title}</h2><form method="post"><input type="hidden" name="action" value="{action}">{hidden_id}
    <div class="form-grid"><div><label>Gadget name</label><input name="name" value="{name}" required></div><div><label>Category</label><input name="category" value="{category}" required></div>
    <div><label>Price (₱)</label><input type="number" name="price" min="0" step="0.01" value="{price}" required></div><div><label>Stock quantity</label><input type="number" name="stock" min="0" step="1" value="{stock}" required></div>
    <div><label>Simple icon / symbol (fallback)</label><input name="icon" maxlength="8" value="{icon}"></div><div class="full"><label>Product image URL</label><input type="url" name="image_url" value="{image_url}" placeholder="https://example.com/product-photo.jpg"><small class="muted">Paste a direct image link. The photo appears in the buyer shop and gadget manager.</small></div></div><div class="actions"><button class="btn">{'Save changes' if editing else 'Add gadget'}</button>{'<a class="btn secondary" href="/gadgets">Cancel</a>' if editing else ''}</div></form></section>
    <div class="section-head"><div><h2>All gadgets</h2><div class="muted">{len(gadgets)} product records</div></div></div>
    <section class="card table-wrap"><table><thead><tr><th>Gadget</th><th>Price</th><th>Stock</th><th>Status</th><th>Actions</th></tr></thead><tbody>{rows or '<tr><td colspan="5" class="empty">No gadgets added yet.</td></tr>'}</tbody></table></section>"""
    return page(content, "Gadget Manager")
 
 
@app.route("/users", methods=["GET", "POST"])
@role_required("Administrator")
def manage_users():
    global next_user_id
    if request.method == "POST":
        try:
            action = request.form.get("action")
            if action == "add":
                username = request.form.get("username", "").strip()
                password = request.form.get("password", "")
                name = request.form.get("name", "").strip()
                role = request.form.get("role", "")
                if not username or not password or not name:
                    raise ValueError("All fields are required.")
                if len(username) < 3 or len(password) < 8:
                    raise ValueError("Username must be 3+ characters and password at least 8.")
                if get_user_by_username(username):
                    raise ValueError("Username already exists.")
                cls = {"Administrator": Administrator, "Staff": Staff, "Customer": Customer}.get(role)
                if cls is None: raise ValueError("Choose a valid role.")
                users.append(cls(next_user_id, username, password, name))
                next_user_id += 1
                flash("User account created successfully.", "success")
            elif action == "delete":
                uid = int(request.form.get("id", ""))
                if uid == current_user().user_id:
                    raise ValueError("You cannot remove your own account.")
                target = get_user_by_id(uid)
                if not target: raise ValueError("User not found.")
                users.remove(target)
                orders[:] = [o for o in orders if o["buyer_id"] != uid]
                flash("User removed successfully.", "success")
            else:
                raise ValueError("Invalid action.")
        except (ValueError, TypeError) as exc:
            flash(str(exc), "danger")
        return redirect(url_for("manage_users"))
    rows = ""
    for u in users:
        rows += f"""<tr><td><b>{escape(u.name)}</b></td><td>@{escape(u.username)}</td><td><span class="tag">{u.role}</span></td><td>
        <form method="post" onsubmit="return confirm('Remove this user?')"><input type="hidden" name="action" value="delete"><input type="hidden" name="id" value="{u.user_id}"><button class="btn danger">Remove</button></form></td></tr>"""
    content = f"""<div class="section-head"><div><div class="kicker">ADMINISTRATION</div><h1>User management</h1><p class="muted">Manage access to the azsyl system.</p></div></div>
    <section class="card"><h2>Create user</h2><form method="post"><input type="hidden" name="action" value="add"><div class="form-grid">
    <div><label>Full name</label><input name="name" required></div><div><label>Username</label><input name="username" minlength="3" required></div>
    <div><label>Temporary password</label><input type="password" name="password" minlength="8" required></div><div><label>Role</label><select name="role" required><option value="">Choose a role</option><option>Administrator</option><option>Staff</option><option>Customer</option></select></div></div>
    <button class="btn" style="margin-top:16px">Create user</button></form></section>
    <div class="section-head"><div><h2>Registered users</h2><div class="muted">{len(users)} accounts</div></div></div>
    <section class="card table-wrap"><table><thead><tr><th>Name</th><th>Username</th><th>Role</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table></section>"""
    return page(content, "User Management")
 
 
@app.route("/shop")
@role_required("Customer")
def shop():
    q = request.args.get("q", "").strip().lower()
    filtered = [g for g in gadgets if q in g.name.lower() or q in g.category.lower()]
    cards = ""
    for g in filtered:
        status = "Out of stock" if g.stock == 0 else f"{g.stock} available"
        cls = "out" if g.stock == 0 else ("low" if g.stock <= 3 else "")
        button = '<button class="btn secondary" disabled>Sold out</button>' if g.stock == 0 else f'<a class="btn" href="/buy/{g.id}">View item</a>'
        cards += f"""<article class="card gadget"><div><div class="gadget-visual">{image_markup(g)}</div><div class="gadget-top"><h3>{escape(g.name)}</h3><span class="tag">{escape(g.category)}</span></div><p class="muted"><span class="badge {cls}">{status}</span></p></div><div><div class="price">{money(g.price)}</div><div class="actions">{button}</div></div></article>"""
    content = f"""<div class="section-head"><div><div class="kicker">BUYER PORTAL</div><h1>Explore gadgets</h1><p class="muted">Find a device and place your order.</p></div>
    <form class="search" method="get"><label for="q">Search products</label><input id="q" name="q" value="{escape(q)}" placeholder="Search by name or category"></form></div>
    <div class="grid">{cards if cards else '<div class="card empty full">No gadgets match your search.</div>'}</div>"""
    return page(content, "Shop")
 
 
@app.route("/buy/<int:gadget_id>", methods=["GET", "POST"])
@role_required("Customer")
def buy(gadget_id):
    global next_order_id
    gadget = get_gadget(gadget_id)
    if not gadget:
        flash("Gadget not found.", "danger")
        return redirect(url_for("shop"))
    if request.method == "POST":
        try:
            quantity = int(request.form.get("quantity", "1"))
            address = request.form.get("address", "").strip()
            payment_method = request.form.get("payment_method", "").strip()
            allowed_payments = {"Cash on Delivery", "GCash", "Maya", "Bank Transfer"}
            if len(address) < 8:
                raise ValueError("Please enter your complete delivery address (at least 8 characters).")
            if payment_method not in allowed_payments:
                raise ValueError("Please choose a valid payment method.")
            gadget.sell(quantity)
            user = current_user()
            orders.append({
                "id": next_order_id, "buyer_id": user.user_id, "buyer_name": user.name,
                "gadget_id": gadget.id, "gadget_name": gadget.name, "quantity": quantity,
                "total": gadget.price * quantity, "status": "Pending",
                "address": address, "payment_method": payment_method,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            next_order_id += 1
            flash("Order placed. It is waiting for coordinator approval.", "success")
            return redirect(url_for("my_orders"))
        except (ValueError, TypeError) as exc:
            flash(str(exc), "danger")
    content = f"""<div style="max-width:680px;margin:10px auto"><section class="card"><div class="gadget-visual" style="height:240px;font-size:64px">{image_markup(gadget)}</div>
    <div class="kicker">{escape(gadget.category)}</div><h1 style="font-size:40px">{escape(gadget.name)}</h1><p class="muted">Available stock: {gadget.stock}</p><div class="price" style="font-size:28px">{money(gadget.price)}</div>
    <form method="post" style="margin-top:22px"><div class="form-grid"><div><label>Quantity</label><input type="number" name="quantity" min="1" max="{gadget.stock}" value="1" required {'disabled' if gadget.stock == 0 else ''}></div><div><label>Buyer name</label><input value="{escape(current_user().name)}" readonly></div><div class="full"><label>Complete delivery address</label><textarea name="address" required minlength="8" rows="3" placeholder="House/Unit, Street, Barangay, City/Municipality, Province, ZIP code" style="width:100%;padding:12px 13px;border-radius:8px;border:1px solid #29466c;background:#071225;color:#f3f7ff;resize:vertical"></textarea></div><div class="full"><label>Payment method</label><select name="payment_method" required><option value="">Choose payment method</option><option>Cash on Delivery</option><option>GCash</option><option>Maya</option><option>Bank Transfer</option></select><small class="muted">Demo only: selecting GCash, Maya, or Bank Transfer does not process an actual payment.</small></div></div>
    <button class="btn" style="width:100%;margin-top:14px" {'disabled' if gadget.stock == 0 else ''}>Place order</button></form><a class="btn secondary" style="margin-top:10px;width:100%" href="/shop">Back to shop</a></section></div>"""
    return page(content, f"Order {gadget.name}")
 
 
@app.route("/orders", methods=["GET", "POST"])
@role_required("Administrator", "Staff")
def manage_orders():
    if request.method == "POST":
        try:
            order_id = int(request.form.get("id", ""))
            action = request.form.get("action")
            order = next((o for o in orders if o["id"] == order_id), None)
            if not order: raise ValueError("Order not found.")
            if order["status"] != "Pending":
                raise ValueError("Only pending orders can be updated.")
            if action == "approve":
                order["status"] = "Approved"
                flash(f"Order #{order_id} approved.", "success")
            elif action == "reject":
                gadget = get_gadget(order["gadget_id"])
                if gadget: gadget.stock += order["quantity"]
                order["status"] = "Rejected"
                flash(f"Order #{order_id} rejected; stock restored.", "warning")
            else:
                raise ValueError("Invalid order action.")
        except (ValueError, TypeError) as exc:
            flash(str(exc), "danger")
        return redirect(url_for("manage_orders"))
    rows = ""
    for o in reversed(orders):
        cls = {"Pending": "low", "Approved": "", "Rejected": "out"}.get(o["status"], "")
        actions = ""
        if o["status"] == "Pending":
            actions = f"""<div class="actions"><form method="post"><input type="hidden" name="id" value="{o['id']}"><input type="hidden" name="action" value="approve"><button class="btn">Approve</button></form>
            <form method="post"><input type="hidden" name="id" value="{o['id']}"><input type="hidden" name="action" value="reject"><button class="btn danger">Reject</button></form></div>"""
        delivery_payment = f"<br><small class=\"muted\">Deliver to: {escape(o.get('address', 'Not provided'))}<br>Payment: {escape(o.get('payment_method', 'Not specified'))}</small>"
        rows += f"""<tr><td><b>#{o['id']}</b><br><span class="muted">{o['date']}</span></td><td>{escape(o['buyer_name'])}</td><td>{escape(o['gadget_name'])} × {o['quantity']}{delivery_payment}</td><td><b>{money(o['total'])}</b></td><td><span class="badge {cls}">{o['status']}</span></td><td>{actions or '<span class="muted">No action</span>'}</td></tr>"""
    counts = {status: sum(o["status"] == status for o in orders) for status in ("Pending", "Approved", "Rejected")}
    content = f"""<div class="section-head"><div><div class="kicker">ORDER CONTROL</div><h1>Orders</h1><p class="muted">Review purchases and update order status.</p></div></div>
    <div class="stats"><div class="stat"><div class="muted">All orders</div><div class="number">{len(orders)}</div></div><div class="stat"><div class="muted">Pending</div><div class="number">{counts['Pending']}</div></div><div class="stat"><div class="muted">Approved</div><div class="number">{counts['Approved']}</div></div><div class="stat"><div class="muted">Rejected</div><div class="number">{counts['Rejected']}</div></div></div>
    <section class="card table-wrap"><table><thead><tr><th>Order</th><th>Customer</th><th>Item / delivery / payment</th><th>Total</th><th>Status</th><th>Action</th></tr></thead><tbody>{rows if rows else '<tr><td colspan="6" class="empty">No orders have been placed yet.</td></tr>'}</tbody></table></section>"""
    return page(content, "Orders")
 
 
@app.route("/my-orders")
@role_required("Customer")
def my_orders():
    mine = [o for o in orders if o["buyer_id"] == current_user().user_id]
    cards = ""
    for o in reversed(mine):
        cls = {"Pending": "low", "Approved": "", "Rejected": "out"}.get(o["status"], "")
        cards += f"""<section class="card order-card"><div><span class="tag">ORDER #{o['id']}</span><h3 style="margin-top:10px">{escape(o['gadget_name'])} × {o['quantity']}</h3><div class="muted">{o['date']}</div><div class="muted" style="margin-top:8px">Deliver to: {escape(o.get("address", "Not provided"))}<br>Payment: {escape(o.get("payment_method", "Not specified"))}</div></div>
        <div style="text-align:right"><div class="price">{money(o['total'])}</div><span class="badge {cls}">{o['status']}</span></div></section>"""
    content = f"""<div class="section-head"><div><div class="kicker">BUYER PORTAL</div><h1>My orders</h1><p class="muted">Track the status of your purchases.</p></div></div>
    <div style="display:grid;gap:14px">{cards if cards else '<section class="card empty"><h2>No orders yet</h2><p>Browse the store to place your first order.</p><a class="btn" style="margin-top:12px" href="/shop">Browse gadgets</a></section>'}</div>"""
    return page(content, "My Orders")
 
 
@app.errorhandler(404)
def not_found(error):
    return page("""<section class="card empty" style="max-width:650px;margin:35px auto"><div class="kicker">ERROR 404</div><h1 style="font-size:42px">Page not found</h1><p>The page you requested does not exist.</p><a class="btn" href="/dashboard">Back to dashboard</a></section>""", "Page Not Found"), 404
 
 
@app.errorhandler(500)
def server_error(error):
    return page("""<section class="card empty" style="max-width:650px;margin:35px auto"><div class="kicker">ERROR 500</div><h1 style="font-size:42px">Something went wrong</h1><p>Please try again. If the issue continues, check the application logs.</p><a class="btn" href="/">Return home</a></section>""", "Server Error"), 500
 
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
