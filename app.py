import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, date, timedelta, timezone # Agregamos timezone aquí
import streamlit.components.v1 as components
import json, random, uuid
import base64
import pandas as pd
import altair as alt
import firebase_admin
from firebase_admin import credentials, firestore, storage


import urllib.parse


# ================================
# 🔁 CRUCE CHECADOR vs ASISTENCIA
# ================================
from zoneinfo import ZoneInfo
from datetime import datetime, date, timedelta

MEX_TZ = ZoneInfo("America/Mexico_City")

def load_users_map(db):
    user_to_emp = {}
    emp_to_user = {}
    user_to_name = {}

    for doc in db.collection("users").stream():
        d = doc.to_dict() or {}
        user_code = (d.get("user_code") or doc.id or "").strip().upper()
        employee_id = str(d.get("employee_id") or "").strip()
        full_name = (d.get("full_name") or "").strip()

        if user_code:
            user_to_name[user_code] = full_name
        if user_code and employee_id:
            user_to_emp[user_code] = employee_id
            emp_to_user[employee_id] = user_code

    return user_to_emp, emp_to_user, user_to_name


def get_day_bounds_utc(day_str_yyyy_mm_dd: str):
    y, m, d = map(int, day_str_yyyy_mm_dd.split("-"))
    start_local = datetime(y, m, d, 0, 0, 0, tzinfo=MEX_TZ)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(ZoneInfo("UTC")), end_local.astimezone(ZoneInfo("UTC"))


def fetch_zk_punches_for_day(db, day_str_yyyy_mm_dd: str):
    start_utc, end_utc = get_day_bounds_utc(day_str_yyyy_mm_dd)

    q = (
        db.collection("zk_attendance")
          .where("timestamp_utc", ">=", start_utc)
          .where("timestamp_utc", "<", end_utc)
    )

    emp_ids = set()
    for doc in q.stream():
        d = doc.to_dict() or {}
        zk_user_id = str(d.get("user_id") or "").strip()
        if zk_user_id:
            emp_ids.add(zk_user_id)

    return emp_ids

# ================================
# Definición de usuarios y áreas
# ================================
import re
import unicodedata

def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def make_user_code(full_name: str, existing_codes: set) -> str:
    """
    Login code = FIRST INITIAL + LASTNAME (uppercase, no accents), max 8 chars.
    Examples:
      Luis Zurita -> LZURITA
      Allan Zurita -> AZURITA
      Ivonne Luna -> ILUNA
    If duplicated, appends 2,3... keeping max length 8.
    """
    name = _strip_accents(full_name).strip()
    parts = re.split(r"\s+", name)

    if len(parts) < 2:
        # fallback: single token name
        base = re.sub(r"[^A-Za-z0-9]", "", parts[0].upper())[:8]
    else:
        first_initial = re.sub(r"[^A-Za-z0-9]", "", parts[0].upper())[:1]
        last_name = re.sub(r"[^A-Za-z0-9]", "", parts[-1].upper())
        base = (first_initial + last_name)[:8]

    code = base
    k = 2
    while code in existing_codes:
        suffix = str(k)
        code = (base[:8 - len(suffix)] + suffix)[:8]
        k += 1
    return code


# ================================
# USERS + TEAMS (RTR ONLY)
# ================================

# --- Solo estos 10 usuarios ---
valid_users = {
    "MGONZALEZ": "Marco Antonio Gonzalez",
    "GMAYORALM": "Guillermo Mayoral",
    "LAMEDINA": "Laura Medina",
    "ASANCHEZO": "Alejandra Sanchez",
    "IACORTEZ": "Itzumi Alejandra Cortez",
    "BNAVARRO": "Brenda Araceli Navarro",
    "EJUAREZE": "Elizabeth Juarez",
    "RIUMEGIDO": "Ricardo Rodrigo Umegido",
    "HEHERNANDEZ": "Heidy Hernandez",
    "RROJAS": "Rodrigo Alejandro Rojas",
}

# --- Equipo RTR ---
group_rtr = set(valid_users.keys())

# --- TL de RTR (Marco por defecto) ---
RTR_TL = "MGONZALEZ"   # cambia a "GMAYORALM" si Guillermo será TL

# TL users en la app (solo el TL)
TL_USERS = {RTR_TL}

# Mapa de TL por equipo
TEAM_TL_MAP = {
    "RTR": RTR_TL
}

# -----------------------------
# STUBS (para que no truene nada)
# Si luego vas a eliminar pantallas, esto ya no será necesario.
# -----------------------------
group_namer = set()
group_latam = set()
group_r2r_gral = set()
group_wor = set()
group_fa = set()
group_ic = set()
group_otc = set()

group_costmatch = set()
group_banking_latam = set()
group_banking_namer = set()
group_mdm = set()
group_office_mgmt_po = set()
group_it_local = set()
group_cash = set()
group_ap_te = set()
group_ap_one = set()
group_vqh = set()
group_project_mgmt = set()

# Menú restringido: en RTR normalmente NO restringimos
restricted_teams = set()
# =================================================
# CONFIG
# =================================================
st.set_page_config(
    page_title="Daily Huddle",
    page_icon="🔥",
    layout="wide"
)

# =================================================
# CORPORATE CSS (DSV) - AZUL MARINO & ELEGANCIA
# =================================================
DSV_NAVY = "#001E4E"
DSV_BLUE = "#002664"
DSV_BG   = "#EBF0F5"
DSV_LINE = "#E1E8F0"
DSV_BRD  = "#CFD8E3"
TXT_MUTED = "#6A7067"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');

/* Base */
html, body, [class*="css"] {{
  font-family: 'Inter', sans-serif;
}}
.stApp {{
  background-color: {DSV_BG};
}}

/* Sidebar */
[data-testid="stSidebar"] {{
  background-color: {DSV_NAVY};
}}
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stMarkdown *,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p {{
  color: #FFFFFF !important;
}}


/* inputs dentro del sidebar */
[data-testid="stSidebar"] input, 
[data-testid="stSidebar"] textarea {{
  color: #111 !important;
}}

/* Header bar (si la usas) */
.header-bar {{
  background: linear-gradient(135deg, {DSV_NAVY} 0%, {DSV_BLUE} 100%);
  padding: 18px 24px;
  border-radius: 15px;
  color: white;
  margin-bottom: 16px;
}}
.header-bar h1 {{
  margin: 0;
  font-size: 28px;
  font-weight: 800;
}}

/* Panel / Cards */
.panel {{
  background: #FFFFFF;
  border-radius: 12px;
  padding: 18px 20px;
  border: 1px solid {DSV_BRD};
  box-shadow: 0 4px 10px rgba(0,0,0,0.03);
  margin-bottom: 16px;
}}
.panel-tight {{ padding: 14px 16px; }}

.hr {{
  height: 1px;
  background: {DSV_LINE};
  margin: 14px 0;
  border: none;
}}

/* Titles */
.box-title {{
  font-size: 16px;
  font-weight: 800;
  color: {DSV_BLUE};
  margin: 0 0 8px 0;
}}
.small-muted {{
  color: {TXT_MUTED};
  font-size: 12px;
}}

/* Badges (chips) */
.badge {{
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  margin: 4px 6px 4px 0;
}}

/* Buttons */
.stButton > button {{
  background: {DSV_BLUE};
  color: white;
  border: 1px solid {DSV_BLUE};
  border-radius: 10px;
  padding: 0.55rem 0.9rem;
  font-weight: 800;
}}
.stButton > button:hover {{
  background: {DSV_NAVY};
  border-color: {DSV_NAVY};
  color: white;
}}

/* Inputs (text, select, date, etc.) */
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div {{
  border-radius: 10px !important;
  border-color: {DSV_BRD} !important;
}}
textarea {{
  border-radius: 10px !important;
  border-color: {DSV_BRD} !important;
}}

/* Dataframe container */
[data-testid="stDataFrame"] {{
  border: 1px solid {DSV_BRD};
  border-radius: 12px;
  overflow: hidden;
}}

/* Tags / multiselect chips */
span[data-baseweb="tag"] {{
  background-color: {DSV_BLUE} !important;
  color: white !important;
  border: none !important;
}}

/* Radios/checkbox accent feel */
input[type="checkbox"], input[type="radio"] {{
  accent-color: {DSV_BLUE};
}}
</style>
""", unsafe_allow_html=True)

# FIX selectbox sidebar (selected text + background + dropdown options)
st.markdown("""
<style>
/* Make the selectbox container white so text is visible */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background: #FFFFFF !important;
  border-radius: 10px !important;
}

/* Selected value text (combobox) */
[data-testid="stSidebar"] [data-baseweb="select"] div[role="combobox"] span {
  color: #111 !important;
}

/* Sometimes Streamlit renders the value via input */
[data-testid="stSidebar"] [data-baseweb="select"] div[role="combobox"] input {
  color: #111 !important;
  -webkit-text-fill-color: #111 !important;
}

/* Dropdown menu options (when opened) */
div[role="listbox"] span {
  color: #111 !important;
}
</style>
""", unsafe_allow_html=True)



# (Opcional) Header corporativo global para tu app
st.markdown(f"""
<div class="header-bar">
  <h1> | Daily Huddle</h1>
</div>
""", unsafe_allow_html=True)

# ================================
# Pantalla de Login
# ================================
if "user_code" not in st.session_state:
    st.session_state["user_code"] = None

def show_login():
    st.title("🔥 Daily Huddle - Login")
    st.write("Ingresa tu código de usuario")
    user_input = st.text_input("Código de usuario:", max_chars=20)
    if st.button("Ingresar"):
        user_input = user_input.strip().upper()
        if user_input in valid_users:
            st.session_state.user_code = user_input
            st.success(f"¡Bienvenido, {valid_users[user_input]}!")
        else:
            st.error("Código de usuario inválido. Intenta nuevamente.")

if st.session_state["user_code"] is None:
    show_login()
    st.stop()

# ================================
# Repositorio de actividades (simulado)
# ================================
activity_repo = [
    "Reunión de planificación corporativa",
    "Actualización de estrategia logística",
    "Análisis de desempeño trimestral",
    "Sesión de brainstorming para innovación"
]

# ================================
# Inicialización de Firebase usando secrets (TOML)
# ================================
def init_firebase():
    firebase_config = st.secrets["firebase"]
    if not isinstance(firebase_config, dict):
        firebase_config = firebase_config.to_dict()

    try:
        cred = credentials.Certificate(firebase_config)

        if not firebase_admin._apps:
            # 🔥 IMPORTANTE: añade storageBucket
            firebase_admin.initialize_app(cred, {
                "storageBucket": st.secrets["firebase_storage_bucket"]  # ej: "tu-proyecto.appspot.com"
            })

        db = firestore.client()
        bucket = storage.bucket()  # usa el bucket por default configurado arriba
        return db, bucket

    except Exception as e:
        st.error(f"Error al inicializar Firebase: {e}")
        st.stop()

db, bucket = init_firebase()

# ================================
# 🌴 DAYS OFF MODULE (Firestore)
# - Vacation accrues daily
# - Sick is annual bucket
# - Flex is EARNED by working holidays/bridges (approved)
# - Requests go to direct boss for approval
# ================================

from zoneinfo import ZoneInfo
from datetime import datetime, date, timedelta, timezone as dt_timezone

MEX_TZ = ZoneInfo("America/Mexico_City")
UTC = ZoneInfo("UTC")

# Firestore collections
COL_USERS = "users"  # ya la tienes, solo lo recordamos
COL_HOLIDAYS = "company_holidays"        # docs id: YYYY-MM-DD
COL_FLEX_EARNED = "flex_earned"          # docs id: f"{user_code}_{YYYY-MM-DD}"
COL_TIMEOFF_REQUESTS = "timeoff_requests" # requests vacation/flex/sick

# Policies
DEFAULT_VACATION_ANNUAL = 12
DEFAULT_SICK_ANNUAL = 4

# ✅ Config base: CNAPOLES hire date
DEFAULT_HIRE_DATES = {
    "CNAPOLES": "2024-07-08"
}

# (Opcional) override vacaciones anuales por usuario (tú dijiste CNAPOLES 10)
VACATION_ANNUAL_OVERRIDE = {
    "CNAPOLES": 10
}

def _today_local_date() -> date:
    return datetime.now(MEX_TZ).date()

def _now_utc():
    return datetime.now(dt_timezone.utc)

def _parse_yyyy_mm_dd(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()

def _safe_get_user_hire_date(user_code: str) -> date | None:
    """
    users/{user_code}.hire_date (YYYY-MM-DD) si existe
    si no, usa DEFAULT_HIRE_DATES
    """
    try:
        snap = db.collection(COL_USERS).document(user_code).get()
        if snap.exists:
            d = snap.to_dict() or {}
            hd = (d.get("hire_date") or "").strip()
            if hd:
                return _parse_yyyy_mm_dd(hd)
    except Exception:
        pass

    if user_code in DEFAULT_HIRE_DATES:
        return _parse_yyyy_mm_dd(DEFAULT_HIRE_DATES[user_code])

    return None

def _vacation_annual_days(user_code: str) -> float:
    return float(VACATION_ANNUAL_OVERRIDE.get(user_code, DEFAULT_VACATION_ANNUAL))

def _anniversary_year_bounds(hire_date: date, ref_day: date):
    """
    Regresa inicio y fin del 'año laboral' basado en aniversario.
    Ej: hire 2024-07-08
    para ref 2026-02-23 => periodo: 2025-07-08 a 2026-07-07
    """
    # construir aniversario del año actual
    ann_this_year = date(ref_day.year, hire_date.month, hire_date.day)
    if ref_day >= ann_this_year:
        start = ann_this_year
        end = date(ref_day.year + 1, hire_date.month, hire_date.day) - timedelta(days=1)
    else:
        start = date(ref_day.year - 1, hire_date.month, hire_date.day)
        end = ann_this_year - timedelta(days=1)
    return start, end

def _days_in_period(start: date, end: date) -> int:
    return (end - start).days + 1

def _get_timeoff_used(user_code: str, period_start: date, period_end: date):
    """
    Suma lo APROBADO en timeoff_requests dentro del periodo.
    VACATION: suma days_requested
    SICK: suma days_requested
    FLEX: suma days_requested (días flex usados)
    """
    used = {"VACATION": 0.0, "SICK": 0.0, "FLEX": 0.0}
    try:
        qs = (
            db.collection(COL_TIMEOFF_REQUESTS)
              .where("user_code", "==", user_code)
              .where("status", "==", "APPROVED")
              .stream()
        )
        for doc in qs:
            d = doc.to_dict() or {}
            t = (d.get("type") or "").upper().strip()
            days = float(d.get("days_requested") or 0)
            start_s = (d.get("start_date") or "").strip()
            if not start_s:
                continue
            sd = _parse_yyyy_mm_dd(start_s)
            if period_start <= sd <= period_end and t in used:
                used[t] += days
    except Exception:
        pass
    return used

def _get_flex_earned(user_code: str, period_start: date, period_end: date) -> float:
    """
    Cuenta flex earned APROBADOS en flex_earned dentro del periodo.
    Cada feriado trabajado = 1 flex day (ajustable).
    """
    earned = 0.0
    try:
        qs = (
            db.collection(COL_FLEX_EARNED)
              .where("user_code", "==", user_code)
              .where("status", "==", "APPROVED")
              .stream()
        )
        for doc in qs:
            d = doc.to_dict() or {}
            ds = (d.get("date") or "").strip()
            if not ds:
                continue
            dd = _parse_yyyy_mm_dd(ds)
            if period_start <= dd <= period_end:
                earned += float(d.get("credits") or 1.0)  # default 1
    except Exception:
        pass
    return earned

def compute_days_off_balance(user_code: str):
    """
    Retorna balances actuales (con decimales):
    - Vacation accrued daily within current anniversary year
    - Sick annual bucket minus used
    - Flex earned (approved holidays worked) minus flex used
    """
    today = _today_local_date()
    hire = _safe_get_user_hire_date(user_code)
    if not hire:
        return {
            "error": "NO_HIRE_DATE",
            "message": "No hire_date found for this user."
        }

    period_start, period_end = _anniversary_year_bounds(hire, today)

    # Vacation accrual
    annual_vac = _vacation_annual_days(user_code)
    total_days_period = _days_in_period(period_start, period_end)

    # accrual up to today (inclusive)
    elapsed_days = _days_in_period(period_start, min(today, period_end))
    vac_accrued = (annual_vac / total_days_period) * elapsed_days

    used = _get_timeoff_used(user_code, period_start, period_end)

    # Sick bucket
    sick_entitled = float(DEFAULT_SICK_ANNUAL)
    sick_used = float(used["SICK"])
    sick_balance = max(0.0, sick_entitled - sick_used)

    # Flex earned from holidays worked
    flex_earned = _get_flex_earned(user_code, period_start, period_end)
    flex_used = float(used["FLEX"])
    flex_balance = max(0.0, flex_earned - flex_used)

    # Vacation balance
    vac_used = float(used["VACATION"])
    vac_balance = vac_accrued - vac_used  # puede quedar decimal (si quieres clamp a 0, pon max(0,...))
    vac_balance = max(0.0, vac_balance)

    return {
        "hire_date": hire.strftime("%Y-%m-%d"),
        "period_start": period_start.strftime("%Y-%m-%d"),
        "period_end": period_end.strftime("%Y-%m-%d"),
        "vacation_annual": annual_vac,
        "vacation_accrued": round(vac_accrued, 2),
        "vacation_used": round(vac_used, 2),
        "vacation_balance": round(vac_balance, 2),
        "sick_entitled": sick_entitled,
        "sick_used": round(sick_used, 2),
        "sick_balance": round(sick_balance, 2),
        "flex_earned": round(flex_earned, 2),
        "flex_used": round(flex_used, 2),
        "flex_balance": round(flex_balance, 2),
    }

def list_holidays_between(start_d: date, end_d: date):
    """
    Lee company_holidays y devuelve lista ordenada.
    Doc ID sugerido: YYYY-MM-DD
    """
    items = []
    try:
        # Simple: traemos todo y filtramos (si son pocos feriados no pesa)
        # Si quieres optimizar: guarda un campo date y consulta por rango.
        for doc in db.collection(COL_HOLIDAYS).stream():
            d = doc.to_dict() or {}
            ds = (d.get("date") or doc.id or "").strip()
            if not ds:
                continue
            dd = _parse_yyyy_mm_dd(ds)
            if start_d <= dd <= end_d:
                items.append({
                    "date": ds,
                    "name": d.get("name", ""),
                    "type": d.get("type", "HOLIDAY"),
                    "country": d.get("country", "MX"),
                })
    except Exception:
        pass
    items.sort(key=lambda x: x["date"])
    return items

def has_zk_punch_for_day(db, user_employee_id: str, day_str: str) -> bool:
    """
    Usa tu colección zk_attendance con timestamp_utc
    y revisa si hubo punch ese día.
    """
    if not user_employee_id or user_employee_id == "N/A":
        return False
    start_utc, end_utc = get_day_bounds_utc(day_str)
    try:
        q = (
            db.collection("zk_attendance")
              .where("timestamp_utc", ">=", start_utc)
              .where("timestamp_utc", "<", end_utc)
              .where("user_id", "==", str(user_employee_id))
        )
        for _ in q.stream():
            return True
    except Exception:
        return False
    return False

def submit_flex_earned_request(user_code: str, holiday_date: str, holiday_name: str, source: str, boss_code: str):
    """
    Crea un registro PENDING de flex_earned para ese feriado trabajado.
    doc id = user_code + '_' + date
    """
    doc_id = f"{user_code}_{holiday_date}"
    ref = db.collection(COL_FLEX_EARNED).document(doc_id)

    # evitar duplicados
    snap = ref.get()
    if snap.exists:
        d = snap.to_dict() or {}
        st.warning(f"Ya existe registro para {holiday_date} (status: {d.get('status')}).")
        return False

    payload = {
        "user_code": user_code,
        "date": holiday_date,
        "holiday_name": holiday_name,
        "credits": 1.0,
        "source": source,  # "ZK" o "MANUAL"
        "status": "PENDING",
        "requested_to": boss_code,
        "created_at": _now_utc(),
        "reviewed_by": None,
        "reviewed_at": None,
    }
    ref.set(payload)
    return True

def submit_timeoff_request(user_code: str, ttype: str, start_date: str, days_requested: float, boss_code: str, note: str = ""):
    """
    Solicitud de uso: VACATION / SICK / FLEX
    (FLEX aquí es USO de flex ya ganado)
    """
    request_id = str(uuid.uuid4())
    payload = {
        "request_id": request_id,
        "user_code": user_code,
        "type": ttype.upper().strip(),
        "start_date": start_date,
        "days_requested": float(days_requested),
        "note": (note or "").strip(),
        "status": "PENDING",
        "requested_to": boss_code,
        "created_at": _now_utc(),
        "reviewed_by": None,
        "reviewed_at": None,
    }
    db.collection(COL_TIMEOFF_REQUESTS).document(request_id).set(payload)
    return True

def approve_reject_flex_earned(doc_id: str, approve: bool, reviewer_code: str):
    ref = db.collection(COL_FLEX_EARNED).document(doc_id)
    snap = ref.get()
    if not snap.exists:
        return "NOT_FOUND"
    d = snap.to_dict() or {}
    if d.get("status") != "PENDING":
        return "ALREADY_REVIEWED"

    ref.update({
        "status": "APPROVED" if approve else "REJECTED",
        "reviewed_by": reviewer_code,
        "reviewed_at": _now_utc(),
    })
    return "APPROVED" if approve else "REJECTED"

def approve_reject_timeoff_request(request_id: str, approve: bool, reviewer_code: str):
    ref = db.collection(COL_TIMEOFF_REQUESTS).document(request_id)
    snap = ref.get()
    if not snap.exists:
        return "NOT_FOUND"
    d = snap.to_dict() or {}
    if d.get("status") != "PENDING":
        return "ALREADY_REVIEWED"

    ref.update({
        "status": "APPROVED" if approve else "REJECTED",
        "reviewed_by": reviewer_code,
        "reviewed_at": _now_utc(),
    })
    return "APPROVED" if approve else "REJECTED"

def show_days_off(user_code: str):
    st.header("🌴 Days Off")

    # 1) Balances
    bal = compute_days_off_balance(user_code)
    if bal.get("error"):
        st.error(bal.get("message", "No pude calcular balances."))
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### 🧳 Vacation (Accrues daily)")
        st.metric("Balance", f"{bal['vacation_balance']}")
        st.caption(f"Accrued: {bal['vacation_accrued']} | Used: {bal['vacation_used']} | Annual: {bal['vacation_annual']}")
    with c2:
        st.markdown("### 🤒 Sick")
        st.metric("Balance", f"{bal['sick_balance']}")
        st.caption(f"Entitled: {bal['sick_entitled']} | Used: {bal['sick_used']}")
    with c3:
        st.markdown("### 🌉 Flex (Earned)")
        st.metric("Balance", f"{bal['flex_balance']}")
        st.caption(f"Earned: {bal['flex_earned']} | Used: {bal['flex_used']}")

    st.caption(f"Hire date: {bal['hire_date']} | Period: {bal['period_start']} → {bal['period_end']}")
    st.divider()

    # 2) Earn Flex Day (worked a holiday)
    st.subheader("✅ Earn Flex Day (worked a holiday/bridge)")

    period_start = _parse_yyyy_mm_dd(bal["period_start"])
    period_end = _parse_yyyy_mm_dd(bal["period_end"])
    holidays = list_holidays_between(period_start, period_end)

    if not holidays:
        st.info("No hay feriados cargados en company_holidays para tu periodo. (Se deben registrar en Firestore).")
    else:
        holiday_options = [f"{h['date']} — {h['name']}" for h in holidays]
        pick = st.selectbox("Selecciona el feriado que trabajaste", holiday_options)
        picked_date = pick.split(" — ")[0].strip()
        picked_name = pick.split(" — ")[1].strip() if " — " in pick else ""

        emp_id = get_employee_id(user_code)
        zk_ok = has_zk_punch_for_day(db, emp_id, picked_date)

        st.write(f"Checador detectado para ese día: {'✅' if zk_ok else '❌'} (Employee ID: {emp_id})")
        source = "ZK" if zk_ok else "MANUAL"

        boss = get_direct_boss(user_code)
        st.write(f"Jefe directo (aprobador): **{valid_users.get(boss, boss)} ({boss})**")

        if st.button("📩 Solicitar Flex Earned (enviar a aprobación)"):
            ok = submit_flex_earned_request(
                user_code=user_code,
                holiday_date=picked_date,
                holiday_name=picked_name,
                source=source,
                boss_code=boss
            )
            if ok:
                st.success("Solicitud enviada ✅ (Flex Earned)")

    st.divider()

    # 3) Request Days Off (use)
    st.subheader("📅 Request Day Off")
    boss = get_direct_boss(user_code)
    st.write(f"Se enviará a: **{valid_users.get(boss, boss)} ({boss})**")

    with st.form("form_timeoff_request", clear_on_submit=True):
        ttype = st.selectbox("Type", ["VACATION", "FLEX", "SICK"])
        start_d = st.date_input("Start date", value=_today_local_date())
        days_req = st.number_input("Days requested", min_value=0.5, step=0.5, value=1.0)
        note = st.text_area("Note (optional)")
        submit = st.form_submit_button("Send request")

    if submit:
        # Validación de saldo
        bal_now = compute_days_off_balance(user_code)
        if ttype == "VACATION" and days_req > bal_now["vacation_balance"]:
            st.error("No tienes suficiente saldo de Vacation.")
        elif ttype == "FLEX" and days_req > bal_now["flex_balance"]:
            st.error("No tienes suficiente saldo de Flex.")
        elif ttype == "SICK" and days_req > bal_now["sick_balance"]:
            st.error("No tienes suficiente saldo de Sick.")
        else:
            submit_timeoff_request(
                user_code=user_code,
                ttype=ttype,
                start_date=start_d.strftime("%Y-%m-%d"),
                days_requested=float(days_req),
                boss_code=boss,
                note=note
            )
            st.success("Solicitud enviada ✅")

    st.divider()

    # 4) My requests (history)
    st.subheader("📄 My Requests (History)")
    my_rows = []
    for doc in db.collection(COL_TIMEOFF_REQUESTS).where("user_code", "==", user_code).stream():
        d = doc.to_dict() or {}
        d["id"] = doc.id
        my_rows.append(d)
    if my_rows:
        df = pd.DataFrame(my_rows)
        if "created_at" in df.columns:
            try:
                df = df.sort_values(by="created_at", ascending=False)
            except Exception:
                pass
        st.dataframe(df[["type","start_date","days_requested","status","requested_to","created_at","reviewed_by","reviewed_at"]], use_container_width=True)
    else:
        st.info("Sin solicitudes aún.")

    # 5) TL Approval Panel
    if user_code in TL_USERS:
        st.divider()
        st.subheader("🔒 Approval Panel (TL)")

        # Flex earned approvals
        st.markdown("### Flex Earned (Holiday worked)")
        pend_flex = []
        for doc in db.collection(COL_FLEX_EARNED).where("requested_to", "==", user_code).where("status", "==", "PENDING").stream():
            d = doc.to_dict() or {}
            d["id"] = doc.id
            pend_flex.append(d)

        if not pend_flex:
            st.info("No pending Flex Earned requests.")
        else:
            for r in pend_flex:
                st.markdown(f"**{valid_users.get(r.get('user_code'), r.get('user_code'))}** | {r.get('date')} | {r.get('holiday_name','')} | source: {r.get('source')}")
                cA, cB = st.columns(2)
                with cA:
                    if st.button("✅ Approve Flex Earned", key=f"ap_flex_{r['id']}"):
                        res = approve_reject_flex_earned(r["id"], True, user_code)
                        st.success(res)
                        st.rerun()
                with cB:
                    if st.button("❌ Reject Flex Earned", key=f"rej_flex_{r['id']}"):
                        res = approve_reject_flex_earned(r["id"], False, user_code)
                        st.success(res)
                        st.rerun()
                st.markdown("---")

        # Timeoff approvals (use)
        st.markdown("### Time Off Requests (Use vacation/flex/sick)")
        pend_to = []
        for doc in db.collection(COL_TIMEOFF_REQUESTS).where("requested_to", "==", user_code).where("status", "==", "PENDING").stream():
            d = doc.to_dict() or {}
            d["id"] = doc.id
            pend_to.append(d)

        if not pend_to:
            st.info("No pending Time Off requests.")
        else:
            for r in pend_to:
                st.markdown(f"**{valid_users.get(r.get('user_code'), r.get('user_code'))}** | {r.get('type')} | {r.get('start_date')} | {r.get('days_requested')} days")
                if r.get("note"):
                    st.caption(r.get("note"))
                cA, cB = st.columns(2)
                with cA:
                    if st.button("✅ Approve Time Off", key=f"ap_to_{r['id']}"):
                        res = approve_reject_timeoff_request(r["id"], True, user_code)
                        st.success(res)
                        st.rerun()
                with cB:
                    if st.button("❌ Reject Time Off", key=f"rej_to_{r['id']}"):
                        res = approve_reject_timeoff_request(r["id"], False, user_code)
                        st.success(res)
                        st.rerun()
                st.markdown("---")


# ================================
# USERS MAP (Firestore) -> employee_id
# ================================
COL_USERS = "users"

def get_user_profile(user_code: str) -> dict:
    """
    Lee users/{user_code} y lo cachea en session_state.
    """
    key = f"_profile_{user_code}"
    if key in st.session_state and isinstance(st.session_state[key], dict):
        return st.session_state[key]

    try:
        snap = db.collection(COL_USERS).document(user_code).get()
        profile = snap.to_dict() if snap.exists else {}
    except Exception:
        profile = {}

    st.session_state[key] = profile
    return profile

def get_employee_id(user_code: str) -> str:
    """
    Devuelve employee_id de Firestore (si no existe, regresa 'N/A').
    """
    profile = get_user_profile(user_code)
    emp = (profile.get("employee_id") or "").strip()
    return emp if emp else "N/A"

# ================================
# 5S GAMES (Puntos + Evidencia + Aprobación)
# ================================
FIVE_S_TEAMS = [
    "Accounts Payable",
    "VQH",
    "Cost Match",
    "Verification",
    "Claims",
    "MDM",
    "Office Support",
    "Project Management / Controller",
    "BCM",
    "Intercompany",

    # ✅ Separamos Banking de Cash para bajar puntos por separado
    "Banking",
    "Cash",
    "Office Managment & P&O",
    "Local IT",

    "Global IT",
]


# Colores (solo referencia UI, no crítico)
FIVE_S_TEAM_COLORS = {
    "Accounts Payable": "#7FDBFF",
    "VQH": "#7FDBFF",
    "Cost Match": "#7FDBFF",
    "Verification": "#7FDBFF",
    "Claims": "#B10DC9",
    "MDM": "#FFDC00",
    "Office Support": "#DDDDDD",
    "Project Management / Controller": "#2ECC40",
    "BCM": "#FF4136",
    "Intercompany": "#FF851B",
    "Cash Management": "#B10DC9",
    "Global IT": "#C7F3C2",
    "Banking": "#B10DC9",
    "Cash": "#B10DC9",

}

COL_5S_SCORES = "5s_scores"        # docs: team_name -> {score, updated_at}
COL_5S_REQUESTS = "5s_requests"    # docs: requests pendientes/aprobadas/rechazadas
def _team_doc_id(team: str) -> str:
    """
    Firestore doc IDs cannot contain '/'.
    Convert team name into a safe doc_id.
    """
    # Lower + replace slashes and spaces
    safe = team.strip().lower()
    safe = safe.replace("/", " - ")
    safe = re.sub(r"\s+", "_", safe)          # spaces -> _
    safe = re.sub(r"[^a-z0-9_\-]", "", safe)  # keep only safe chars
    return safe[:120]  # keep it short

def _ensure_5s_scores_initialized():
    """
    Crea documentos iniciales si no existen.
    Todos empiezan con 100.
    """
    for team in FIVE_S_TEAMS:
        doc_id = _team_doc_id(team)
        ref = db.collection(COL_5S_SCORES).document(doc_id)
        snap = ref.get()
        if not snap.exists:
            ref.set({
                "team": team,          # nombre real
                "doc_id": doc_id,      # id seguro
                "score": 100,
                "updated_at": datetime.now(),
            })


def _get_5s_scores_dict():
    """
    Retorna {team: score} asegurando init.
    """
    _ensure_5s_scores_initialized()
    scores = {}
    for team in FIVE_S_TEAMS:
        doc_id = _team_doc_id(team)
        snap = db.collection(COL_5S_SCORES).document(doc_id).get()
        if snap.exists:
            scores[team] = int(snap.to_dict().get("score", 100))
        else:
            scores[team] = 100
    return scores



def _compute_5s_leader(scores: dict):
    """
    Si hay un ganador único -> regresa el team
    si hay empate -> "TBD"
    """
    if not scores:
        return "TBD"
    max_score = max(scores.values())
    winners = [t for t, s in scores.items() if s == max_score]
    return winners[0] if len(winners) == 1 else "TBD"

def _upload_evidence_to_storage(uploaded_file, request_id: str):
    """
    Sube el archivo a Firebase Storage y regresa:
      (storage_path, public_or_signed_url_optional)

    Nota: En Streamlit Cloud normalmente usarás signed URLs al leer (como ya haces).
    """
    if uploaded_file is None:
        return None

    try:
        raw = uploaded_file.getvalue()
        # Carpeta ordenada por requests
        storage_path = f"5s_evidence/{request_id}/{uploaded_file.name}"

        blob = bucket.blob(storage_path)
        blob.upload_from_string(raw, content_type=uploaded_file.type)

        return storage_path
    except Exception as e:
        st.error(f"Error subiendo evidencia a Storage: {e}")
        return None

# --- Función de utilidad para limpiar datos antes de Firestore ---
def _firestore_safe(obj):
    import math
    from datetime import datetime, date, timezone

    # 1. Manejo de tipos de Numpy/Pandas (causa común de errores 400)
    try:
        import numpy as np
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)):
            v = float(obj)
            return v if not (math.isnan(v) or math.isinf(v)) else None
        if isinstance(obj, (np.bool_,)): return bool(obj)
    except ImportError:
        pass

    # 2. Manejo de tipos básicos
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj): return None
        return obj
    
    if isinstance(obj, (str, int, bool)) or obj is None:
        return obj

    # 3. Manejo de fechas
    if isinstance(obj, datetime):
        return obj.replace(tzinfo=timezone.utc) if obj.tzinfo is None else obj
    if isinstance(obj, date):
        return datetime(obj.year, obj.month, obj.day, tzinfo=timezone.utc)

    # 4. RECURSIÓN: Aquí estaba el problema con los "nested entities"
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            # Firestore no permite puntos en las llaves de diccionarios anidados
            safe_key = str(k).replace(".", "_").replace("[", "").replace("]", "")
            new_dict[safe_key] = _firestore_safe(v)
        return new_dict

    if isinstance(obj, (list, tuple)):
        return [_firestore_safe(i) for i in obj]

    # Si es un objeto de Streamlit (UploadedFile), Firestore fallará. 
    # Lo convertimos a string para evitar el crash.
    return str(obj)
    
# --- Versión corregida de la función de creación de request ---
def _create_5s_request(requester_code: str, team: str, delta: int, reason: str, uploaded_file=None):
    """
    Crea una solicitud 5S en Firestore.
    Si hay archivo, lo sube a Firebase Storage y guarda solo el path.
    """
    try:
        request_id = str(uuid.uuid4())

        # 1) Subir evidencia (si existe)
        evidence_storage_path = None
        if uploaded_file is not None:
            evidence_storage_path = _upload_evidence_to_storage(uploaded_file, request_id)

        # 2) Documento Firestore (ligero)
        data = {
            "request_id": request_id,
            "requester_code": str(requester_code),
            "requester_name": str(valid_users.get(requester_code, requester_code)),
            "team": str(team),
            "delta": int(delta),
            "reason": str(reason or "").strip(),
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc),
            "reviewed_by": None,
            "reviewed_at": None,
            "has_evidence": True if evidence_storage_path else False,
            "evidence_storage_path": evidence_storage_path,
        }

        final_data = _firestore_safe(data)

        # Guardamos con ID fijo (útil para trazabilidad)
        db.collection(COL_5S_REQUESTS).document(request_id).set(final_data)
        return True

    except Exception as e:
        st.error(f"Error crítico en Firestore: {e}")
        return False

        
def _apply_5s_request_transaction(request_doc_id: str, approve: bool, reviewer_code: str):
    """
    Si approve=True:
      - aplica delta al score del team
      - marca request como APPROVED
    Si approve=False:
      - marca como REJECTED
    """
    req_ref = db.collection(COL_5S_REQUESTS).document(request_doc_id)

    @firestore.transactional
    def _tx(trx: firestore.Transaction):
        req_snap = req_ref.get(transaction=trx)
        if not req_snap.exists:
            return "NOT_FOUND"
        req = req_snap.to_dict()

        if req.get("status") != "PENDING":
            return "ALREADY_REVIEWED"

        if not approve:
            trx.update(req_ref, {
                "status": "REJECTED",
                "reviewed_by": reviewer_code,
                "reviewed_at": datetime.now(),
            })
            return "REJECTED"

        team = req.get("team")
        delta = int(req.get("delta", 0))

        score_ref = db.collection(COL_5S_SCORES).document(_team_doc_id(team))
        score_snap = score_ref.get(transaction=trx)
        if not score_snap.exists:
            # Si por algo no existía, init con 100
            current_score = 100
            trx.set(score_ref, {"team": team, "score": 100, "updated_at": datetime.now()})
        else:
            current_score = int(score_snap.to_dict().get("score", 100))

        new_score = current_score + delta
        # opcional: clamp 0..200 (si no quieres límites, borra estas 2 líneas)
        new_score = max(0, min(200, new_score))

        trx.update(score_ref, {"score": new_score, "updated_at": datetime.now()})
        trx.update(req_ref, {
            "status": "APPROVED",
            "reviewed_by": reviewer_code,
            "reviewed_at": datetime.now(),
            "applied_new_score": new_score,
        })
        return "APPROVED"

    trx = db.transaction()
    return _tx(trx)

def show_5s_games(user_code: str):
    st.subheader("🏁 5SGAMES | Team Scoreboard + Evidence + Approval")

    # Refresh manual (sin autorefresh)
    if st.button("🔄 Refresh scoreboard", key="btn_refresh_5s"):
        st.rerun()


    scores = _get_5s_scores_dict()
    leader = _compute_5s_leader(scores)

    # Banner winner
    if leader == "TBD":
        st.info("🏆 Current winner: **TBD** (tie)")
    else:
        st.success(f"🏆 Current winner: **{leader}**")

    # Scoreboard
    st.markdown("### 📊 Current Scores")
    scoreboard_rows = []
    for t in FIVE_S_TEAMS:
        scoreboard_rows.append({
            "Team": t,
            "Score": scores.get(t, 100)
        })
    df_scores = pd.DataFrame(scoreboard_rows).sort_values(by="Score", ascending=False).reset_index(drop=True)
    st.dataframe(df_scores, use_container_width=True)

    st.markdown("---")

# ======================
    # SUBMIT REQUEST
    # ======================
    st.markdown("### ✅ Submit Evidence + Points Request")
    st.caption("Puntos se ajustan en pasos de 10. El cambio **no aplica** hasta aprobación de CNAPOLES.")

    # 1. El Formulario para recolectar datos
    with st.form("form_5s_submit", clear_on_submit=True):
        team_sel = st.selectbox("Team", FIVE_S_TEAMS)
        action_sel = st.radio("Action", ["Add points (+)", "Remove points (-)"], horizontal=True)
        points_sel = st.selectbox("Points", [10, 20, 30, 40, 50])
        reason_sel = st.text_area("Reason / Comment")
        evidence_file = st.file_uploader("Upload evidence (optional)", type=["png", "jpg", "jpeg", "pdf"])
        submit_btn = st.form_submit_button("Review Request")

        if submit_btn:
            delta = points_sel if action_sel.startswith("Add") else -points_sel
            
            # GUARDAMOS EL ARCHIVO REAL EN LA SESIÓN
            st.session_state["pending_5s_submit"] = {
                "requester_code": user_code,
                "team": team_sel,
                "delta": int(delta),
                "reason": reason_sel.strip(),
                "file": evidence_file # Pasamos el objeto del archivo completo
            }
            st.rerun()

   # 2. BLOQUE DE REVISIÓN (Confirmación corregida)
    if st.session_state.get("pending_5s_submit"):
        p = st.session_state["pending_5s_submit"]
        
        with st.status("🔍 Revisa tu solicitud antes de enviar", expanded=True):
            st.write(f"**Equipo:** {p['team']} | **Ajuste:** {p['delta']} puntos")
            st.write(f"**Motivo:** {p['reason'] if p['reason'] else 'Sin motivo'}")
            
            # Corregido: Verificamos 'file' en lugar de 'evidence_payload'
            if p.get('file'):
                st.write(f"**Evidencia:** {p['file'].name} cargada.")
            
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                if st.button("✅ Confirmar y Enviar", use_container_width=True):
                    # Pasamos p['file'] que es donde realmente guardamos el archivo
                    success = _create_5s_request(
                        requester_code=p["requester_code"],
                        team=p["team"],
                        delta=p["delta"],
                        reason=p["reason"],
                        uploaded_file=p.get("file") 
                    )
                    if success:
                        st.toast("¡Solicitud enviada!", icon="✅")
                        st.session_state["pending_5s_submit"] = None
                        st.rerun()
            
            with col_c2:
                if st.button("❌ Cancelar", use_container_width=True):
                    st.session_state["pending_5s_submit"] = None
                    st.rerun()
    # ======================
    # APPROVAL PANEL (CNAPOLES ONLY)
    # ======================
    if user_code == "CNAPOLES":
        st.markdown("### 🔒 Approval Panel (CNAPOLES)")
        pending = list(
            db.collection(COL_5S_REQUESTS)
              .where("status", "==", "PENDING")
              .stream()
        )

        if not pending:
            st.info("No pending requests.")
            return

        for doc in pending:
            req = doc.to_dict()
            req_id = doc.id

            st.markdown(f"**Team:** {req.get('team')}  |  **Delta:** {req.get('delta')}  |  **Requested by:** {req.get('requester_name')} ({req.get('requester_code')})")
            st.write(f"**Reason:** {req.get('reason','')}")
            st.write(f"**Created at:** {req.get('created_at')}")

            # --- Dentro del bucle de CNAPOLES ---
            # Reemplaza la parte de base64.b64decode por esto:
            if req.get("has_evidence") and req.get("evidence_storage_path"):
                try:
                    blob = bucket.blob(req.get("evidence_storage_path"))
                    # Generar una URL firmada válida por 1 hora
                    img_url = blob.generate_signed_url(expiration=timedelta(hours=1))
                    st.image(img_url, caption="Evidencia cargada", use_container_width=True)
                except Exception as e:
                    st.warning("No se pudo generar la vista previa de la evidencia.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Approve", key=f"approve_5s_{req_id}"):
                    result = _apply_5s_request_transaction(req_id, True, user_code)
                    if result == "APPROVED":
                        st.success("Approved and applied ✅")
                    else:
                        st.warning(f"Approval result: {result}")
                    st.rerun()

            with c2:
                if st.button("❌ Reject", key=f"reject_5s_{req_id}"):
                    result = _apply_5s_request_transaction(req_id, False, user_code)
                    if result == "REJECTED":
                        st.success("Rejected ✅")
                    else:
                        st.warning(f"Reject result: {result}")
                    st.rerun()

            st.markdown("---")
    else:
        st.markdown("### ⏳ Pending / History (Your requests)")
        my_reqs = []
        for doc in db.collection(COL_5S_REQUESTS).where("requester_code", "==", user_code).stream():
            d = doc.to_dict()
            d["id"] = doc.id
            my_reqs.append(d)

        if not my_reqs:
            st.info("You have no requests yet.")
        else:
            df_my = pd.DataFrame(my_reqs)
            # Ordenar por created_at si existe
            if "created_at" in df_my.columns:
                try:
                    df_my = df_my.sort_values(by="created_at", ascending=False)
                except:
                    pass
            st.dataframe(df_my[["team","delta","status","created_at","reviewed_by","reviewed_at"]], use_container_width=True)



def get_direct_boss(destinatario_code):
    if destinatario_code in group_rtr:
        return TEAM_TL_MAP["RTR"]
    return "N/A"

def get_team_for_tl(tl_code):
    if tl_code == TEAM_TL_MAP["RTR"]:
        # el TL ve a todo su equipo (incluyéndose si quieres, o quítalo)
        return list(group_rtr)
    return [tl_code]

# ================================
# Función para obtener la "fecha activa" (día laboral)
# ================================
def get_active_date():
    today = date.today()
    if today.weekday() == 5:
        active = today - timedelta(days=1)
    elif today.weekday() == 6:
        active = today - timedelta(days=2)
    else:
        active = today
    return active.strftime("%Y-%m-%d")

# ================================
# Función para eliminar tareas en grupo
# ================================
def delete_task_group(collection, group_id):
    query = db.collection(collection).where("group_id", "==", group_id).stream()
    for doc in query:
        db.collection(collection).document(doc.id).delete()



# ================================
# Dashboard KPI para usuario KPI (filtrado diario, semanal y mensual)
# ================================
def show_kpi_dashboard():
    st.header("Dashboard KPI")
    st.markdown("Resumen general de reportes:")
    period = st.radio("Filtrar por:", ["Diaria", "Semanal", "Mensual"])
    today = date.today()
    if period == "Diaria":
        start_date = today
        end_date = today
    elif period == "Semanal":
        start_date = today - timedelta(days=today.weekday())  # Lunes
        end_date = start_date + timedelta(days=6)
    else:  # Mensual
        start_date = today.replace(day=1)
        if today.month == 12:
            end_date = today.replace(year=today.year+1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = today.replace(month=today.month+1, day=1) - timedelta(days=1)
    st.write("Mostrando datos desde", start_date.strftime("%Y-%m-%d"), "hasta", end_date.strftime("%Y-%m-%d"))

    # Asistencia: consulta documentos en "attendance" en el rango seleccionado
    attendance_docs = []
    for doc in db.collection("attendance").stream():
        data = doc.to_dict()
        try:
            doc_date = datetime.strptime(data.get("fecha", "2100-01-01"), "%Y-%m-%d").date()
        except:
            continue
        if start_date <= doc_date <= end_date:
            attendance_docs.append(data)
    if attendance_docs:
        df_att = pd.DataFrame(attendance_docs)
        df_att["fecha"] = pd.to_datetime(df_att["fecha"])
        df_count = df_att.groupby("fecha").size().reset_index(name="Asistencias")
        chart_att = alt.Chart(df_count).mark_line(point=True).encode(
            x=alt.X("fecha:T", title="Fecha"),
            y=alt.Y("Asistencias:Q", title="Número de Asistencias"),
            tooltip=["fecha", "Asistencias"]
        ).properties(
            width=600,
            height=300,
            title="Asistencia por día"
        )
        st.altair_chart(chart_att, use_container_width=True)
    else:
        st.info("No hay registros de asistencia en el período seleccionado.")

    # Top 3: consulta documentos en "top3"
    top3_docs = []
    for doc in db.collection("top3").stream():
        data = doc.to_dict()
        try:
            doc_date = datetime.strptime(data.get("fecha_inicio", "2100-01-01"), "%Y-%m-%d").date()
        except:
            continue
        if start_date <= doc_date <= end_date:
            top3_docs.append(data)
    if top3_docs:
        df_top3 = pd.DataFrame(top3_docs)
        df_status = df_top3["status"].value_counts().reset_index()
        df_status.columns = ["Status", "Cantidad"]
        chart_top3 = alt.Chart(df_status).mark_bar().encode(
            x=alt.X("Status:N", title="Status"),
            y=alt.Y("Cantidad:Q", title="Tareas"),
            color="Status:N",
            tooltip=["Status", "Cantidad"]
        ).properties(
            width=300,
            height=300,
            title="Distribución de Status en Top 3"
        )
        st.altair_chart(chart_top3, use_container_width=True)
    else:
        st.info("No hay tareas Top 3 en el período seleccionado.")

    # Actions: consulta documentos en "actions"
    actions_docs = []
    for doc in db.collection("actions").stream():
        data = doc.to_dict()
        try:
            doc_date = datetime.strptime(data.get("fecha_inicio", "2100-01-01"), "%Y-%m-%d").date()
        except:
            continue
        if start_date <= doc_date <= end_date:
            actions_docs.append(data)
    if actions_docs:
        df_actions = pd.DataFrame(actions_docs)
        df_actions_count = df_actions.groupby("status").size().reset_index(name="Cantidad")
        chart_actions = alt.Chart(df_actions_count).mark_bar().encode(
            x=alt.X("status:N", title="Status"),
            y=alt.Y("Cantidad:Q", title="Acciones"),
            color="status:N",
            tooltip=["status", "Cantidad"]
        ).properties(
            width=300,
            height=300,
            title="Distribución de Status en Actions"
        )
        st.altair_chart(chart_actions, use_container_width=True)
    else:
        st.info("No hay acciones en el período seleccionado.")

# ================================
# Función para enviar una tarea de Action Board a Top 3
# ================================
def send_action_to_top3(action_doc):
    data_ref = action_doc
    if not hasattr(data_ref, "to_dict"):
        data_ref = action_doc.get()
    data = data_ref.to_dict()
    new_data = data.copy()
    new_data.pop("timestamp", None)
    new_data["fecha_inicio"] = datetime.now().strftime("%Y-%m-%d")
    new_data["group_id"] = str(uuid.uuid4())
    # Mapear el campo "accion" a "descripcion" si es necesario
    if "accion" in new_data and "descripcion" not in new_data:
        new_data["descripcion"] = new_data.pop("accion")
    db.collection("top3").add(new_data)
    st.success("Tarea enviada de Action Board a Top 3.")

# ================================
# App Principal
# ================================
def show_allocation_module(user_code):
    st.header("📦 Alocación de Facturas - Verification & Cost Match")
    st.info("Carga el archivo de verificación para distribuir las facturas equitativamente entre el equipo.")
    
    uploaded_file = st.file_uploader(
        "Cargar archivo de verificación (CSV / Excel)",
        type=["csv", "xlsx", "xls"]
    )
    
    if uploaded_file is not None:
        filename = (uploaded_file.name or "").lower()

        # --- Leer según extensión ---
        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            elif filename.endswith(".xlsx") or filename.endswith(".xls"):
                # Requiere openpyxl para .xlsx (en Streamlit Cloud ponlo en requirements.txt)
                df = pd.read_excel(uploaded_file, engine="openpyxl")
            else:
                st.error("Formato no soportado. Usa CSV, XLSX o XLS.")
                return
        except Exception as e:
            st.error(f"No pude leer el archivo. Detalle: {e}")
            return

        # Limpiar espacios en nombres de columnas
        df.columns = df.columns.astype(str).str.strip()

        st.write(f"Total de facturas encontradas: **{len(df)}**")
        
        # Obtener equipo de verificación para alocar
        team_members = list(group_verification)
        random.shuffle(team_members) # Aleatoriedad para justicia en la carga
        
        # Distribución equitativa
        assigned_users = []
        for i in range(len(df)):
            assigned_users.append(team_members[i % len(team_members)])
        
        df["Assignee_Code"] = assigned_users
        df["Assignee_Name"] = df["Assignee_Code"].map(valid_users)
        
        st.subheader("Preview de Alocación")
        # Permitir edición manual (mover +100/-100 o cambiar responsable)
        edited_df = st.data_editor(df, num_rows="dynamic")
        
        if st.button("Confirmar y Guardar en Firebase"):
            batch = db.batch()
            for _, row in edited_df.iterrows():
                doc_id = str(uuid.uuid4())
                ref = db.collection("facturas_alocadas").document(doc_id)
                data = row.to_dict()
                data["id_alocacion"] = doc_id
                data["fecha_alocacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data["status_sap"] = "Pending"
                batch.set(ref, data)
            batch.commit()
            st.success("Facturas alocadas y guardadas correctamente.")
            
def show_main_app():
    user_code = st.session_state["user_code"]

    # Si el usuario es KPI, mostrar el dashboard de KPIs y detener la ejecución del resto
    if user_code == "KPI":
        show_kpi_dashboard()
        return

   

    # Botón de Asignar Roles para TL
   # Botón de Asignar Roles para TL (GENÉRICO por equipo)
    if user_code in TL_USERS:
        if st.button("Asignar Roles"):
            team = get_team_for_tl(user_code)
    
            # Quitar TLs de su propia lista para no asignarse
            team = [u for u in team if u != user_code]
    
            # si el team es muy chico, no revientes
            if len(team) < 2:
                st.error("Equipo insuficiente para asignar roles (mínimo 2 personas).")
            else:
                # ALECCION/ICLEAD/WORLEAD suelen asignar 3 roles, el resto 2 (ajústalo como prefieras)
                want_3 = True   # RTR: si quieres 3 roles siempre
                k = 3 if (want_3 and len(team) >= 3) else 2
    
                roles_asignados = random.sample(team, k)
    
                st.session_state["roles"] = {
                    "Timekeeper": roles_asignados[0],
                    "ActionTaker": roles_asignados[1],
                    "Coach": roles_asignados[2] if k == 3 else None
                }
                st.json(st.session_state["roles"])


    st.image("https://play-lh.googleusercontent.com/A0wA3S1uGiGXOc_-Cbp8f1_CHzNJxzgvHTGAZJqlG0Eg5SojX8VSJqk2E5449IRjwak", width=160)
    
    st.title("🔥 Daily Huddle")
    emp_id = get_employee_id(user_code)
    st.markdown(f"**Usuario:** {valid_users[user_code]}  ({user_code})  |  **Employee ID:** {emp_id}")
    
    
    # ------------------- Lógica de Menú Filtrado -------------------
    if user_code in restricted_teams:
        # Menú restringido: No ven Top 3 ni Action Board normal
        menu_options = ["Alocación de Facturas", "Asistencia", "5SGAMES", "Wallet", "Contacto"]
    else:
        # Menú estándar para los demás equipos
        menu_options = ["Asistencia", "Top 3", "Action Board", "Escalation", "Recognition",
                "5SGAMES",
                "Store DBSCHENKER", "Wallet", "Communications", "Calendar","Days Off", "Compliance", "Todas las Tareas",
                "Consultorio Optimizacion", "Contacto"]


    
    if user_code in TL_USERS:
        menu_options.append("Roles")
    
    menu_choice = st.sidebar.selectbox("📌 Selecciona una pestaña:", menu_options)

    # --- Lógica de renderizado de la pestaña de Alocación ---
    if menu_choice == "Alocación de Facturas":
        show_allocation_module(user_code)

    
    # ------------------- Asistencia -------------------
    if menu_choice == "Asistencia":
        if user_code not in TL_USERS:
            st.subheader("📝 Registro de Asistencia")
            today_date = datetime.now().strftime("%Y-%m-%d")
            attendance_doc = db.collection("attendance").document(user_code).get()
            if attendance_doc.exists:
                data = attendance_doc.to_dict()
                if data.get("fecha") != today_date:
                    db.collection("attendance").document(user_code).delete()
            st.write("💡 ¿Cómo te sientes hoy?")
            feelings = {"😃": "Feliz", "😐": "Normal", "😔": "Triste", "😡": "Molesto", "😴": "Cansado", "🤒": "Enfermo"}
            selected_feeling = st.radio("Selecciona tu estado de ánimo:", list(feelings.keys()))
            health_problem = st.radio("❓ ¿Te has sentido con problemas de salud esta semana?", ["Sí", "No"])
            st.write("Nivel de energía (elige entre 20, 40, 60, 80 o 100):")
            energy_options = [20, 40, 60, 80, 100]
            energy_level = st.radio("Nivel de energía:", options=energy_options, horizontal=True)
            st.write("🏢 Modalidad de trabajo:")
            work_location = st.radio("Oficina o Casa (HO):", ["Oficina", "Casa (HO)"], horizontal=True)
            battery_html = f"""
            <div style="display: inline-block; border: 2px solid #000; width: 40px; height: 100px; position: relative;">
              <div style="position: absolute; bottom: 0; width: 100%; height: {energy_level}%; background-color: #00ff00;"></div>
            </div>
            """
            st.markdown(battery_html, unsafe_allow_html=True)
            if st.button("✅ Registrar asistencia"):
                db.collection("attendance").document(user_code).set({
                    "fecha": today_date,
                    "estado_animo": feelings[selected_feeling],
                    "problema_salud": health_problem,
                    "energia": energy_level,
                    "work_location": work_location,
                    "usuario": user_code,
                    "employee_id": get_employee_id(user_code),
                })
                st.success("Asistencia registrada correctamente.")
        else:
            st.subheader("📊 Resumen de Asistencia de tu equipo")
            active_date = get_active_date()
            team = get_team_for_tl(user_code)
            attendance_list = []
            for u in team:
                doc = db.collection("attendance").document(u).get()
                if doc.exists and doc.to_dict().get("fecha") == active_date:
                    info = doc.to_dict()
                    attendance = "✅"
                    feeling = info.get("estado_animo", "N/A")
                    fecha = info.get("fecha", "N/A")
                    pregunta = info.get("problema_salud", "N/A")
                    energia = f"{info.get('energia', 0)}%"
                else:
                    attendance = "❌"
                    feeling = "N/A"
                    fecha = active_date
                    pregunta = "N/A"
                    energia = "N/A"
                attendance_list.append({
                    "Nombre": valid_users.get(u, u),
                    "Asistencia": attendance,
                    "Feeling": feeling,
                    "Fecha": fecha,
                    "Pregunta de la semana": pregunta,
                    "Nivel de energía": energia,
                })
            if attendance_list:
                df_attendance = pd.DataFrame(attendance_list).reset_index(drop=True)
                st.dataframe(df_attendance)
                st.divider()
                st.subheader("📥 Reporte: Oficina vs Checador")
                
                report_date = st.date_input("Fecha del reporte", value=date.fromisoformat(active_date))
                report_date_str = report_date.strftime("%Y-%m-%d")
                
                if st.button("⬇️ Bajar reporte (Excel)"):
                    user_to_emp, emp_to_user, user_to_name = load_users_map(db)
                
                    # Manual attendance (team)
                    att_rows = []
                    for u in team:
                        doc = db.collection("attendance").document(u).get()
                        info = doc.to_dict() if doc.exists else {}
                
                        employee_id = str(info.get("employee_id") or user_to_emp.get(u, "")).strip()
                        work_location = info.get("work_location", "NO REGISTRO")
                        fecha = info.get("fecha", report_date_str)
                
                        # Si el doc existe pero es otro día, lo tratamos como no registro
                        if doc.exists and fecha != report_date_str:
                            work_location = "NO REGISTRO"
                            fecha = report_date_str
                
                        att_rows.append({
                            "user_code": u,
                            "full_name": valid_users.get(u, user_to_name.get(u, u)),
                            "employee_id": employee_id,
                            "fecha": fecha,
                            "work_location": work_location,
                        })
                
                    df_manual = pd.DataFrame(att_rows)
                
                    # Checador punches del día (set de employee_ids que sí checaron)
                    zk_emp_ids = fetch_zk_punches_for_day(db, report_date_str)
                    df_manual["checador_punch"] = df_manual["employee_id"].apply(lambda x: "✅" if x and x in zk_emp_ids else "❌")
                
                    # Validación
                    def consistency(row):
                        wl = (row.get("work_location") or "").strip()
                        punch = row.get("checador_punch")
                
                        if wl == "Oficina" and punch == "✅":
                            return "OK"
                        if wl == "Oficina" and punch == "❌":
                            return "INCONSISTENTE (dijo Oficina, no checó)"
                        if wl == "Casa (HO)" and punch == "❌":
                            return "OK"
                        if wl == "Casa (HO)" and punch == "✅":
                            return "INCONSISTENTE (dijo HO, sí checó)"
                        if wl == "NO REGISTRO":
                            return "SIN REGISTRO MANUAL"
                        return "REVISAR"
                
                    df_manual["validacion"] = df_manual.apply(consistency, axis=1)
                
                    # Export Excel
                    import io
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="openpyxl") as writer:
                        df_manual.to_excel(writer, index=False, sheet_name="Reporte")
                    output.seek(0)
                
                    st.download_button(
                        "✅ Descargar Excel",
                        data=output,
                        file_name=f"reporte_oficina_vs_checador_{report_date_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                
                    st.dataframe(df_manual)
            else:
                st.info("No hay registros para la fecha activa: " + active_date)
    # ------------------- 5SGAMES -------------------
    elif menu_choice == "5SGAMES":
        show_5s_games(user_code)
 

    
    # ------------------- Top 3 -------------------
    elif menu_choice == "Top 3":
        st.subheader("📌 Top 3 Prioridades - Resumen")
        if user_code in TL_USERS:
            team = get_team_for_tl(user_code)
            if user_code == "ALECCION":
                team_namer = [u for u in team if u in group_namer]
                team_latam = [u for u in team if u in group_latam]
                
                filtro_region = st.radio("Filtrar por región:", ["Todas", "NAMER", "LATAM"], horizontal=True)
                
                if filtro_region == "NAMER":
                    team = team_namer
                elif filtro_region == "LATAM":
                    team = team_latam
            
                selected_user = st.selectbox("Filtrar por usuario:", ["Todos"] + [valid_users[u] for u in team])
                if selected_user != "Todos":
                    team = [u for u in team if valid_users[u] == selected_user]

            tasks = []
            for task in db.collection("top3").stream():
                data = task.to_dict()
                usuario = data.get("usuario")
                primary = usuario[0] if isinstance(usuario, list) else usuario
                if primary in team:
                    tasks.append(task)
        else:
            tasks = list(db.collection("top3").where("usuario", "==", user_code).stream())
        groups = {}
        for task in tasks:
            data = task.to_dict()
            data["id"] = task.id
            usuario = data.get("usuario")
            primary = usuario[0] if isinstance(usuario, list) else usuario
            groups.setdefault(primary, []).append(data)
        status_colors = {"Pendiente": "red", "En proceso": "orange", "Completado": "green"}
        def get_status(selected, custom):
            return custom.strip() if custom and custom.strip() != "" else selected
        for u, t_list in groups.items():
            st.markdown(f"**Usuario: {valid_users.get(u, u)}**")
            for task_data in t_list:
                st.markdown(f"- [TOP 3] {task_data.get('descripcion','(Sin descripción)')}")
                st.write(f"Inicio: {task_data.get('fecha_inicio','')}, Compromiso: {task_data.get('fecha_compromiso','')}, Real: {task_data.get('fecha_real','')}")
                # Calcular indicador delayed automáticamente
                compromiso = task_data.get("fecha_compromiso", None)
                if compromiso:
                    comp_date = datetime.strptime(compromiso, "%Y-%m-%d").date()
                    delay_indicator = "Delayed" if comp_date < date.today() else "On time"
                else:
                    delay_indicator = "N/A"
                current_usuario = task_data.get("usuario", "")
                if user_code in TL_USERS:
                    new_usuario = st.selectbox("Modificar usuario", options=list(get_team_for_tl(current_usuario)), 
                                                index=list(get_team_for_tl(current_usuario)).index(current_usuario),
                                                key=f"mod_usuario_top3_{task_data.get('id')}")
                    if new_usuario != current_usuario:
                        db.collection("top3").document(task_data.get("id")).update({"usuario": new_usuario})
                        st.success("Usuario actualizado.")
                origen_field = task_data.get("origen", None)
                if origen_field:
                    st.markdown(f"**Usuario:** {valid_users.get(current_usuario, current_usuario)} (Colaborador) - Creado por: {valid_users.get(origen_field, origen_field)}")
                else:
                    st.markdown(f"**Usuario:** {valid_users.get(current_usuario, current_usuario)}")
                st.markdown(f"**Status:** <span style='color:{status_colors.get(task_data.get('status',''), 'black')};'>{task_data.get('status','')}</span> - <strong>{delay_indicator}</strong>", unsafe_allow_html=True)
                edit_key = f"edit_top3_{task_data.get('id')}"
                if st.session_state.get(edit_key, False):
                    new_status = st.selectbox("Nuevo status", ["Pendiente", "En proceso", "Completado"], key=f"top3_status_{task_data.get('id')}")
                    custom_status = st.text_input("Status personalizado (opcional)", key=f"top3_custom_{task_data.get('id')}")
                    if st.button("Guardar cambios", key=f"save_top3_{task_data.get('id')}"):
                        final_status = get_status(new_status, custom_status)
                        compromiso = task_data.get("fecha_compromiso", "")
                        if compromiso:
                            comp_date = datetime.strptime(compromiso, "%Y-%m-%d").date()
                            time_label = "On time" if comp_date >= date.today() else "Delayed"
                        else:
                            time_label = "N/A"
                        fecha_real = datetime.now().strftime("%Y-%m-%d") if final_status.lower() == "completado" else task_data.get("fecha_real", "")
                        db.collection("top3").document(task_data.get("id")).update({
                            "status": final_status,
                            "fecha_real": fecha_real,
                            "time_label": time_label
                        })
                        st.success("Status actualizado.")
                        st.session_state[edit_key] = False
                else:
                    if st.button("Editar status", key=f"edit_btn_top3_{task_data.get('id')}"):
                        st.session_state[edit_key] = True
                if st.button("🗑️ Eliminar", key=f"delete_top3_{task_data.get('id')}"):
                    group_id = task_data.get("group_id")
                    if group_id:
                        delete_task_group("top3", group_id)
                    else:
                        db.collection("top3").document(task_data.get("id")).delete()
                    st.success("Tarea eliminada.")
                st.markdown("---")
        if st.button("➕ Agregar Tarea de Top 3"):
            st.session_state.show_top3_form = True
        if st.session_state.get("show_top3_form"):
            with st.form("top3_add_form"):
                st.markdown("### Nueva Tarea - Top 3")
                selected_activity = st.selectbox("Selecciona actividad predefinida (opcional)", [""] + activity_repo)
                p = selected_activity if selected_activity != "" else st.text_input("Descripción")
                ti = st.date_input("Fecha de inicio")
                tc = st.date_input("Fecha compromiso")
                s = st.selectbox("Status", ["Pendiente", "En proceso", "Completado"], key="top3_new_status")
                custom_status = st.text_input("Status personalizado (opcional)", key="top3_new_custom")
                
                                # Mostrar todos los usuarios menos yo
                base_collab = sorted(
                    [u for u in valid_users if u != user_code],
                    key=lambda x: valid_users.get(x, x)
                )

                all_collab_options = base_collab

                colaboradores = st.multiselect(
                    "Colaboradores (opcional)",
                    options=all_collab_options,
                    format_func=lambda x: f"{valid_users.get(x, x)} ({x})"
                )

 
               
                privado = st.checkbox("Marcar como privado")
                submit_new_top3 = st.form_submit_button("Guardar tarea")
            if submit_new_top3:
                final_status = get_status(s, custom_status)
                fecha_real = datetime.now().strftime("%Y-%m-%d") if final_status.lower() == "completado" else ""
                group_id = str(uuid.uuid4()) if colaboradores else None
                
                # Expandir los TEAM: si se selecciona "IC TEAM", "FA TEAM" o "GL TEAM"
                final_collaborators = []
                for c in colaboradores:
                    if c == "IC TEAM":
                        final_collaborators.extend(list(group_ic - {user_code}))
                    elif c == "FA TEAM":
                        final_collaborators.extend(list(group_fa - {user_code}))
                    elif c == "GL TEAM":
                        final_collaborators.extend(list(group_namer.union(group_latam) - {user_code}))
                    else:
                        final_collaborators.append(c)
                final_collaborators = list(set(final_collaborators))
                
                data = {
                    "usuario": user_code,
                    "descripcion": p,
                    "fecha_inicio": ti.strftime("%Y-%m-%d"),
                    "fecha_compromiso": tc.strftime("%Y-%m-%d"),
                    "fecha_real": fecha_real,
                    "status": final_status,
                    "privado": privado,
                    "timestamp": datetime.now(),
                    "group_id": group_id
                }
                db.collection("top3").add(data)
                if final_collaborators:
                    for collab in final_collaborators:
                        data_collab = data.copy()
                        data_collab["usuario"] = collab
                        data_collab["origen"] = user_code
                        db.collection("top3").add(data_collab)
                st.success("Tarea de Top 3 guardada.")
                st.session_state.show_top3_form = False

    # ------------------- Action Board -------------------
    elif menu_choice == "Action Board":
        st.subheader("✅ Acciones y Seguimiento - Resumen")
        if user_code in TL_USERS:
            team = get_team_for_tl(user_code)
            if user_code == "ALECCION":
                team_namer = [u for u in team if u in group_namer]
                team_latam = [u for u in team if u in group_latam]
                
                filtro_region = st.radio("Filtrar por región:", ["Todas", "NAMER", "LATAM"], horizontal=True)
                
                if filtro_region == "NAMER":
                    team = team_namer
                elif filtro_region == "LATAM":
                    team = team_latam
            
                selected_user = st.selectbox("Filtrar por usuario:", ["Todos"] + [valid_users[u] for u in team])
                if selected_user != "Todos":
                    team = [u for u in team if valid_users[u] == selected_user]

            actions = []
            for action in db.collection("actions").stream():
                data = action.to_dict()
                usuario = data.get("usuario")
                primary = usuario[0] if isinstance(usuario, list) else usuario
                if primary in team:
                    actions.append(action)
        else:
            actions = list(db.collection("actions").where("usuario", "==", user_code).stream())
        groups_actions = {}
        for action in actions:
            data = action.to_dict()
            data["id"] = action.id
            usuario = data.get("usuario")
            primary = usuario[0] if isinstance(usuario, list) else usuario
            groups_actions.setdefault(primary, []).append(data)
        status_colors = {"Pendiente": "red", "En proceso": "orange", "Completado": "green"}
        def get_status(selected, custom):
            return custom.strip() if custom and custom.strip() != "" else selected
        for u, acts in groups_actions.items():
            st.markdown(f"**Usuario: {valid_users.get(u, u)}**")
            for act_data in acts:
                st.markdown(f"- [Action Board] {act_data.get('accion','(Sin descripción)')}")
                st.write(f"Inicio: {act_data.get('fecha_inicio','')}, Compromiso: {act_data.get('fecha_compromiso','')}, Real: {act_data.get('fecha_real','')}")
                # Calcular indicador delayed automáticamente
                compromiso = act_data.get("fecha_compromiso", None)
                if compromiso:
                    comp_date = datetime.strptime(compromiso, "%Y-%m-%d").date()
                    delay_indicator = "Delayed" if comp_date < date.today() else "On time"
                else:
                    delay_indicator = "N/A"
                current_usuario = act_data.get("usuario", "")
                if user_code in TL_USERS:
                    new_usuario = st.selectbox("Modificar usuario", options=list(get_team_for_tl(current_usuario)), 
                                                index=list(get_team_for_tl(current_usuario)).index(current_usuario),
                                                key=f"mod_usuario_action_{act_data.get('id')}")
                    if new_usuario != current_usuario:
                        db.collection("actions").document(act_data.get("id")).update({"usuario": new_usuario})
                        st.success("Usuario actualizado.")
                origen_field = act_data.get("origen", None)
                if origen_field:
                    st.markdown(f"**Usuario:** {valid_users.get(current_usuario, current_usuario)} (Colaborador) - Creado por: {valid_users.get(origen_field, origen_field)}")
                else:
                    st.markdown(f"**Usuario:** {valid_users.get(current_usuario, current_usuario)}")
                st.markdown(f"**Status:** <span style='color:{status_colors.get(act_data.get('status',''), 'black')};'>{act_data.get('status','')}</span> - <strong>{delay_indicator}</strong>", unsafe_allow_html=True)
                edit_key = f"edit_action_{act_data.get('id')}"
                if st.session_state.get(edit_key, False):
                    new_status = st.selectbox("Nuevo status", ["Pendiente", "En proceso", "Completado"], key=f"action_status_{act_data.get('id')}")
                    custom_status = st.text_input("Status personalizado (opcional)", key=f"action_custom_{act_data.get('id')}")
                    if st.button("Guardar cambios", key=f"save_action_{act_data.get('id')}"):
                        final_status = get_status(new_status, custom_status)
                        compromiso = act_data.get("fecha_compromiso", "")
                        if compromiso:
                            comp_date = datetime.strptime(compromiso, "%Y-%m-%d").date()
                            time_label = "On time" if comp_date >= date.today() else "Delayed"
                        else:
                            time_label = "N/A"
                        fecha_real = datetime.now().strftime("%Y-%m-%d") if final_status.lower() == "completado" else act_data.get("fecha_real", "")
                        db.collection("actions").document(act_data.get("id")).update({
                            "status": final_status,
                            "fecha_real": fecha_real,
                            "time_label": time_label
                        })
                        st.success("Status actualizado.")
                        st.session_state[edit_key] = False
                else:
                    if st.button("Editar status", key=f"edit_btn_action_{act_data.get('id')}"):
                        st.session_state[edit_key] = True
                if st.button("🗑️ Eliminar", key=f"delete_action_{act_data.get('id')}"):
                    group_id = act_data.get("group_id")
                    if group_id:
                        delete_task_group("actions", group_id)
                    else:
                        db.collection("actions").document(act_data.get("id")).delete()
                    st.success("Acción eliminada.")
                if st.button("Enviar a Top3", key=f"send_to_top3_{act_data.get('id')}"):
                    send_action_to_top3(db.collection("actions").document(act_data.get("id")))
                st.markdown("---")
        if st.button("➕ Agregar Acción"):
            st.session_state.show_action_form = True
        if st.session_state.get("show_action_form"):
            with st.form("action_add_form"):
                st.markdown("### Nueva Acción")
                accion = st.text_input("Descripción de la acción")
                ti = st.date_input("Fecha de inicio")
                tc = st.date_input("Fecha compromiso")
                s = st.selectbox("Status", ["Pendiente", "En proceso", "Completado"], key="action_new_status")
                custom_status = st.text_input("Status personalizado (opcional)", key="action_new_custom")

                # ✅ Colaboradores (opcional) + Teams
                team_options = ["IC TEAM", "FA TEAM", "GL TEAM"]

                base_collab = sorted(
                    [u for u in valid_users if u != user_code],
                    key=lambda x: valid_users.get(x, x)
                )

                all_collab_options = base_collab + team_options

                colaboradores = st.multiselect(
                    "Colaboradores (opcional)",
                    options=all_collab_options,
                    format_func=lambda x: f"{valid_users.get(x, x)} ({x})" if x in valid_users else x
                )

                privado = st.checkbox("Marcar como privado")
                submit_new_action = st.form_submit_button("Guardar acción")

            if submit_new_action:
                final_status = get_status(s, custom_status)
                fecha_real = datetime.now().strftime("%Y-%m-%d") if final_status.lower() == "completado" else ""
                group_id = str(uuid.uuid4()) if colaboradores else None
                
                # Expandir TEAM: si se selecciona "IC TEAM", "FA TEAM" o "GL TEAM", se añaden todos los miembros del grupo
                final_collaborators = []
                for c in colaboradores:
                    if c == "IC TEAM":
                        final_collaborators.extend(list(group_ic - {user_code}))
                    elif c == "FA TEAM":
                        final_collaborators.extend(list(group_fa - {user_code}))
                    elif c == "GL TEAM":
                        final_collaborators.extend(list(group_namer.union(group_latam) - {user_code}))
                    else:
                        final_collaborators.append(c)
                final_collaborators = list(set(final_collaborators))
                
                data = {
                    "usuario": user_code,
                    "accion": accion,
                    "fecha_inicio": ti.strftime("%Y-%m-%d"),
                    "fecha_compromiso": tc.strftime("%Y-%m-%d"),
                    "fecha_real": fecha_real,
                    "status": final_status,
                    "privado": privado,
                    "timestamp": datetime.now(),
                    "group_id": group_id
                }
                db.collection("actions").add(data)
                
                if final_collaborators:
                    for collab in final_collaborators:
                        data_collab = data.copy()
                        data_collab["usuario"] = collab
                        data_collab["origen"] = user_code
                        db.collection("actions").add(data_collab)
                st.success("Acción guardada.")
                st.session_state.show_action_form = False

    # ------------------- Escalation -------------------
    elif menu_choice == "Escalation":
        st.subheader("⚠️ Escalation")
        escalador = user_code
        common_options = {"GMAYORALM", "MGONZALEZ"}
        if user_code in group_fa:
            additional = {"ABARRERA"}
        elif user_code in group_ic:
            additional = {"YAEL"}
        elif user_code in (group_namer.union(group_latam)):
            additional = {"MSANCHEZ"}
        elif user_code in group_wor:
            additional = set()
        else:
            additional = set()
        para_quien_options = sorted(list(common_options.union(additional)))
        para_quien = st.selectbox("¿Para quién?", para_quien_options, format_func=lambda x: f"{valid_users.get(x, x)} ({x})")
        with st.form("escalation_form"):
            razon = st.text_area("Razón")
            con_quien = st.multiselect("¿Con quién se tiene el tema?", options=[code for code in valid_users if code != escalador],
                                         format_func=lambda x: f"{valid_users.get(x, x)} ({x})")
            submit_escalation = st.form_submit_button("Enviar escalación")
        if submit_escalation:
            involucrados = [escalador, para_quien]
            if con_quien:
                involucrados.extend(con_quien)
            involucrados = list(set(involucrados))
            escalacion_data = {
                "escalador": escalador,
                "razon": razon,
                "para_quien": para_quien,
                "con_quien": con_quien,
                "involucrados": involucrados,
                "fecha": datetime.now().strftime("%Y-%m-%d")
            }
            db.collection("escalations").add(escalacion_data)
            st.success("Escalación registrada.")
            st.warning(f"Notificación: Se ha enviado un escalation a {valid_users.get(para_quien, para_quien)}.")
        st.markdown("### Escalaciones en las que estás involucrado")
        escalations = list(db.collection("escalations").stream())
        count = 0
        for esc in escalations:
            esc_data = esc.to_dict()
            if user_code in esc_data.get("involucrados", []):
                count += 1
                st.markdown(f"**Escalación:** {esc_data.get('razon','(Sin razón)')}")
                st.write(f"Escalador: {esc_data.get('escalador','')}, Para quién: {esc_data.get('para_quien','')}, Con quién: {esc_data.get('con_quien','')}")
                st.write(f"Fecha: {esc_data.get('fecha','')}")
                st.warning("¡Estás involucrado en esta escalación!")
                st.markdown("---")
        if count == 0:
            st.info("No tienes escalaciones asignadas.")
    
    elif menu_choice == "Days Off":
        show_days_off(user_code)
    
    
    # ------------------- Recognition -------------------
    elif menu_choice == "Recognition":
        if user_code not in TL_USERS:
            st.subheader("Reconocimientos otorgados")
            recs = [doc.to_dict() for doc in db.collection("recognitions").stream() if doc.to_dict().get("destinatario") == user_code]
            if recs:
                for rec in recs:
                    st.markdown(f"**De:** {valid_users.get(rec.get('usuario'), rec.get('usuario'))}  |  **Asunto:** {rec.get('asunto','')}")
                    st.write(f"Mensaje: {rec.get('mensaje','')}")
                    st.write(f"Fecha: {rec.get('fecha','')}")
                    st.markdown("---")
            else:
                st.info("No has recibido reconocimientos.")
            with st.form("recognition_form"):
                st.markdown("**Enviar Reconocimiento**")
                st.markdown(f"**De:** {valid_users[user_code]} ({user_code})")
                destinatario = st.selectbox("Para:", [code for code in valid_users if code != user_code],
                                              format_func=lambda x: f"{valid_users[x]} ({x})")
                jefe_directo = get_direct_boss(destinatario)
                st.markdown(f"**Jefe Directo:** {valid_users.get(jefe_directo, jefe_directo)} ({jefe_directo})")
                kudo_options = [
                    "Great Job! – ¡Excelente trabajo!",
                    "Well Done! – ¡Bien hecho!",
                    "Outstanding! – ¡Sobresaliente!",
                    "Keep it up! – ¡Sigue así!"
                ]
                kudo_card = st.selectbox("Kudo Card:", kudo_options)
                subject = st.text_input("Asunto:", value="Kudo Card de Daily Huddle")
                mensaje = st.text_area("Mensaje:")
                submit_recognition = st.form_submit_button("Enviar Reconocimiento")
            if submit_recognition:
                body = f"KUDO CARD: {kudo_card}\n\n{mensaje}"
                recognition_data = {
                    "usuario": user_code,
                    "destinatario": destinatario,
                    "jefe_directo": jefe_directo,
                    "asunto": subject,
                    "mensaje": body,
                    "fecha": datetime.now().strftime("%Y-%m-%d")
                }
                db.collection("recognitions").add(recognition_data)
                st.success("Reconocimiento enviado.")
                st.warning(f"Notificación: Se ha enviado un reconocimiento a {valid_users.get(destinatario, destinatario)}.")
        else:
            st.subheader("Reconocimientos de tu equipo")
            team = get_team_for_tl(user_code)
            recs = [doc.to_dict() for doc in db.collection("recognitions").stream() if doc.to_dict().get("destinatario") in team]
            if recs:
                for rec in recs:
                    st.markdown(f"**De:** {valid_users.get(rec.get('usuario'), rec.get('usuario'))}  |  **Para:** {valid_users.get(rec.get('destinatario'), rec.get('destinatario'))}  |  **Asunto:** {rec.get('asunto','')}")
                    st.write(f"Mensaje: {rec.get('mensaje','')}")
                    st.write(f"Fecha: {rec.get('fecha','')}")
                    st.markdown("---")
            else:
                st.info("No hay reconocimientos para mostrar.")
    
    # ------------------- Store DBSCHENKER -------------------
    elif menu_choice == "Store DBSCHENKER":
        st.subheader("🛍️ Store DBSCHENKER")
        st.write("Productos corporativos (prototipo):")
        products = [
            {"name": "Taza DBS", "price": 10, "image": "https://via.placeholder.com/150?text=Taza+DBS"},
            {"name": "Playera DBS", "price": 20, "image": "https://via.placeholder.com/150?text=Playera+DBS"},
            {"name": "Gorra DBS", "price": 15, "image": "https://via.placeholder.com/150?text=Gorra+DBS"}
        ]
        for prod in products:
            st.image(prod["image"], width=150)
            st.markdown(f"**{prod['name']}** - {prod['price']} DB COINS")
            if st.button(f"Comprar {prod['name']}", key=f"buy_{prod['name']}"):
                st.info("Función de compra no implementada.")
            st.markdown("---")
    
    # ------------------- Wallet -------------------
    elif menu_choice == "Wallet":
        st.subheader("💰 Mi Wallet (DB COINS)")
        wallet_ref = db.collection("wallets").document(user_code)
        doc = wallet_ref.get()
        current_coins = 0
        if doc.exists:
            current_coins = doc.to_dict().get("coins", 0)
        st.write(f"**Saldo actual:** {current_coins} DB COINS")
        if user_code == "LARANDA":
            add_coins = st.number_input("Generar DB COINS:", min_value=1, step=1, value=10)
            if st.button("Generar DB COINS"):
                new_balance = current_coins + add_coins
                wallet_ref.set({"coins": new_balance})
                st.success(f"Generados {add_coins} DB COINS. Nuevo saldo: {new_balance}.")
            st.markdown("### Funciones Administrativas")
            admin_key = st.text_input("Clave Admin", type="password")
            if admin_key == "ADMIN123":
                if st.button("Resetear todas las monedas a 0"):
                    for u in valid_users:
                        db.collection("wallets").document(u).set({"coins": 0})
                target = st.selectbox("Generar monedas para el usuario:", list(valid_users.keys()),
                                        format_func=lambda x: f"{valid_users[x]} ({x})")
                amt = st.number_input("Cantidad de DB COINS a generar:", min_value=1, step=1, value=10)
                if st.button("Generar para usuario seleccionado"):
                    target_ref = db.collection("wallets").document(target)
                    doc_target = target_ref.get()
                    current = 0
                    if doc_target.exists:
                        current = doc_target.to_dict().get("coins", 0)
                    target_ref.set({"coins": current + amt})
                    st.success(f"Generados {amt} DB COINS para {valid_users[target]}.")
    
    # ------------------- Communications -------------------
    elif menu_choice == "Communications":
        st.subheader("📢 Mensajes Importantes")
        mensaje = st.text_area("📝 Escribe un mensaje o anuncio")
        if st.button("📩 Enviar mensaje"):
            db.collection("communications").document().set({
                "usuario": user_code,
                "fecha": datetime.now().strftime("%Y-%m-%d"),
                "mensaje": mensaje
            })
            st.success("Mensaje enviado.")
    
    # ------------------- Calendar -------------------
    elif menu_choice == "Calendar":
        st.subheader("📅 Calendario")
        cal_option = st.radio("Selecciona una opción", ["Crear Evento", "Ver Calendario"])
        if cal_option == "Crear Evento":
            st.markdown("### Crear Evento")
            evento = st.text_input("📌 Nombre del evento")
            start_date, end_date = st.date_input("Selecciona el rango de fechas", value=(date.today(), date.today()))
            tipo_evento = st.radio("Tipo de evento", ["Público", "Privado"])
            if st.button("✅ Agendar evento"):
                event_data = {
                    "usuario": user_code,
                    "evento": evento,
                    "fecha": start_date.strftime("%Y-%m-%d"),
                    "fecha_fin": end_date.strftime("%Y-%m-%d"),
                    "publico": True if tipo_evento == "Público" else False
                }
                db.collection("calendar").document().set(event_data)
                st.success("Evento agendado.")
        else:
            st.markdown("### Ver Calendario")
            start_date, end_date = st.date_input("Selecciona el rango de fechas para ver eventos", value=(date.today(), date.today()))
            events = []
            for doc in db.collection("calendar").stream():
                data = doc.to_dict()
                if data.get("fecha"):
                    event_date = datetime.strptime(data["fecha"], "%Y-%m-%d").date()
                    if start_date <= event_date <= end_date:
                        title = data.get("evento", "Evento")
                        if not data.get("publico", False):
                            title += f" (Privado - {data.get('usuario','')})"
                        events.append({
                            "title": title,
                            "start": data.get("fecha")
                        })
            events_json = json.dumps(events)
            calendar_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset='utf-8' />
              <link href='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.css' rel='stylesheet' />
              <script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.js'></script>
              <style>
                body {{
                  margin: 0;
                  padding: 0;
                }}
                #calendar {{
                  max-width: 900px;
                  margin: 40px auto;
                }}
              </style>
            </head>
            <body>
              <div id='calendar'></div>
              <script>
                document.addEventListener('DOMContentLoaded', function() {{
                  var calendarEl = document.getElementById('calendar');
                  var calendar = new FullCalendar.Calendar(calendarEl, {{
                    initialView: 'dayGridMonth',
                    events: {events_json}
                  }});
                  calendar.render();
                }});
              </script>
            </body>
            </html>
            """
            components.html(calendar_html, height=600, scrolling=True)
    
    # ------------------- Consultorio Optimizacion -------------------
    elif menu_choice == "Consultorio Optimizacion":
        st.subheader("Consultorio de Optimización")
        st.markdown("Envía un archivo y/o un mensaje para requerir apoyo. Esto se enviará a **CNAPOLES**.")
        with st.form("consultorio_form"):
            mensaje_consult = st.text_area("Describe tu requerimiento o tarea:")
            archivo = st.file_uploader("Adjuntar archivo (opcional)")
            submit_consult = st.form_submit_button("Enviar Consulta")
        if submit_consult:
            data_consult = {
                "usuario": user_code,
                "mensaje": mensaje_consult,
                "archivo": archivo.name if archivo is not None else None,
                "fecha": datetime.now().strftime("%Y-%m-%d"),
                "destinatario": "CNAPOLES"
            }
            db.collection("consultorio").add(data_consult)
            st.success("Consulta enviada a CNAPOLES.")
    
    # ------------------- Contacto -------------------
    elif menu_choice == "Contacto":
        st.subheader("Contacto / Reporte de Problemas")
        st.markdown("Si tienes algún problema con la aplicación, por favor envía tu reporte aquí.")
        with st.form("contacto_form"):
            asunto_contact = st.text_input("Asunto:")
            mensaje_contact = st.text_area("Describe tu problema o sugerencia:")
            submit_contact = st.form_submit_button("Enviar Reporte")
        if submit_contact:
            data_contact = {
                "usuario": user_code,
                "asunto": asunto_contact,
                "mensaje": mensaje_contact,
                "fecha": datetime.now().strftime("%Y-%m-%d")
            }
            db.collection("contacto").add(data_contact)
            st.success("Reporte enviado. Gracias por tu feedback.")
    
    # ------------------- Roles -------------------
    elif menu_choice == "Roles":
        if user_code in {"ALECCION", "WORLEAD", "R2RGRAL", "FALEAD", "ICLEAD"}:
            st.subheader("📝 Asignación de Roles Semanal")
            if st.button("Asignar Roles"):
                if user_code == "ALECCION":
                    posibles = [code for code in valid_users if code not in {"ALECCION", "WORLEAD", "LARANDA", "R2RGRAL", "FALEAD", "ICLEAD", "KPI"}]
                elif user_code == "WORLEAD":
                    posibles = [code for code in valid_users if code not in {"WORLEAD", "ALECCION", "LARANDA", "R2RGRAL", "FALEAD", "ICLEAD", "KPI"} and code in group_wor]
                elif user_code == "R2RGRAL":
                    posibles = [code for code in valid_users if code not in {"R2RGRAL", "ALECCION", "WORLEAD", "LARANDA", "FALEAD", "ICLEAD", "KPI"} and code in group_r2r_gral]
                elif user_code == "FALEAD":
                    posibles = [code for code in valid_users if code not in {"FALEAD", "ALECCION", "WORLEAD", "LARANDA", "R2RGRAL", "ICLEAD", "KPI"} and code in group_fa]
                elif user_code == "ICLEAD":
                    posibles = [code for code in valid_users if code not in {"ICLEAD", "ALECCION", "WORLEAD", "LARANDA", "R2RGRAL", "FALEAD", "KPI"} and code in group_ic]
                roles_asignados = random.sample(possibles, 3) if user_code in {"ALECCION", "WORLEAD", "ICLEAD"} else random.sample(possibles, 2)
                st.session_state["roles"] = {
                    "Timekeeper": roles_asignados[0],
                    "ActionTaker": roles_asignados[1],
                    "Coach": roles_asignados[2] if len(roles_asignados) == 3 else None
                }
                st.json(st.session_state["roles"])
        else:
            st.error("Acceso denegado. Esta opción es exclusiva para los TL.")
    
    # ------------------- Compliance -------------------
    elif menu_choice == "Compliance":
        if user_code in {"ALECCION", "WORLEAD", "R2RGRAL", "FALEAD", "ICLEAD"} or ("roles" in st.session_state and st.session_state["roles"].get("Coach") == user_code):
            st.subheader("📝 Compliance - Feedback")
            feedback_options = [code for code in valid_users if code != user_code]
            target_user = st.selectbox("Dar feedback a:", feedback_options, format_func=lambda x: f"{valid_users.get(x, x)} ({x})")
            feedback = st.text_area("Feedback:")
            if st.button("Enviar Feedback"):
                db.collection("compliance").add({
                    "from": user_code,
                    "to": target_user,
                    "feedback": feedback,
                    "fecha": datetime.now().strftime("%Y-%m-%d")
                })
                st.success("Feedback enviado.")
        else:
            st.error("Acceso denegado. Esta opción es exclusiva para los TL o el Coach.")
    
    # ------------------- Todas las Tareas (solo para TL) -------------------
    elif menu_choice == "Todas las Tareas":
        if user_code not in TL_USERS:
            st.error("Esta opción es exclusiva para perfiles de Team Lead.")
        else:
            st.subheader("🗂️ Todas las Tareas")
            st.markdown("### Tareas TOP3")
            tasks_top3 = [task for task in db.collection("top3").stream() 
                          if (task.to_dict().get("usuario")[0] if isinstance(task.to_dict().get("usuario"), list)
                              else task.to_dict().get("usuario")) in get_team_for_tl(user_code)]
            if tasks_top3:
                for task in tasks_top3:
                    task_data = task.to_dict()
                    st.markdown(f"**[TOP 3] {task_data.get('descripcion','(Sin descripción)')}**")
                    st.write(f"Inicio: {task_data.get('fecha_inicio','')}, Compromiso: {task_data.get('fecha_compromiso','')}, Real: {task_data.get('fecha_real','')}")
                    compromiso = task_data.get("fecha_compromiso", None)
                    if compromiso:
                        comp_date = datetime.strptime(compromiso, "%Y-%m-%d").date()
                        delay_indicator = "Delayed" if comp_date < date.today() else "On time"
                    else:
                        delay_indicator = "N/A"
                    current_usuario = task_data.get("usuario", "")
                    if user_code in TL_USERS:
                        new_usuario = st.selectbox("Modificar usuario", options=list(get_team_for_tl(current_usuario)), 
                                                    index=list(get_team_for_tl(current_usuario)).index(current_usuario),
                                                    key=f"mod_usuario_top3_{task_data.get('id')}")
                        if new_usuario != current_usuario:
                            db.collection("top3").document(task_data.get("id")).update({"usuario": new_usuario})
                            st.success("Usuario actualizado.")
                    origen_field = task_data.get("origen", None)
                    if origen_field:
                        st.markdown(f"**Usuario:** {valid_users.get(current_usuario, current_usuario)} (Colaborador) - Creado por: {valid_users.get(origen_field, origen_field)}")
                    else:
                        st.markdown(f"**Usuario:** {valid_users.get(current_usuario, current_usuario)}")
                    st.markdown(f"**Status:** <span style='color:{status_colors.get(task_data.get('status',''), 'black')};'>{task_data.get('status','')}</span> - <strong>{delay_indicator}</strong>", unsafe_allow_html=True)
                    edit_key = f"edit_top3_{task_data.get('id')}"
                    if st.session_state.get(edit_key, False):
                        new_status = st.selectbox("Nuevo status", ["Pendiente", "En proceso", "Completado"], key=f"top3_status_{task_data.get('id')}")
                        custom_status = st.text_input("Status personalizado (opcional)", key=f"top3_custom_{task_data.get('id')}")
                        if st.button("Guardar cambios", key=f"save_top3_{task_data.get('id')}"):
                            final_status = get_status(new_status, custom_status)
                            compromiso = task_data.get("fecha_compromiso", "")
                            if compromiso:
                                comp_date = datetime.strptime(compromiso, "%Y-%m-%d").date()
                                time_label = "On time" if comp_date >= date.today() else "Delayed"
                            else:
                                time_label = "N/A"
                            fecha_real = datetime.now().strftime("%Y-%m-%d") if final_status.lower() == "completado" else task_data.get("fecha_real", "")
                            db.collection("top3").document(task_data.get("id")).update({
                                "status": final_status,
                                "fecha_real": fecha_real,
                                "time_label": time_label
                            })
                            st.success("Status actualizado.")
                            st.session_state[edit_key] = False
                    else:
                        if st.button("Editar status", key=f"edit_btn_top3_{task_data.get('id')}"):
                            st.session_state[edit_key] = True
                    if st.button("🗑️ Eliminar", key=f"delete_top3_{task_data.get('id')}"):
                        group_id = task_data.get("group_id")
                        if group_id:
                            delete_task_group("top3", group_id)
                        else:
                            db.collection("top3").document(task_data.get("id")).delete()
                        st.success("Tarea eliminada.")
                    st.markdown("---")
            else:
                st.info("No hay tareas TOP3 asignadas.")
            
            st.markdown("### Tareas Action Board")
            tasks_actions = [action for action in db.collection("actions").stream() 
                             if (action.to_dict().get("usuario")[0] if isinstance(action.to_dict().get("usuario"), list)
                                 else action.to_dict().get("usuario")) in get_team_for_tl(user_code)]
            if tasks_actions:
                for action in tasks_actions:
                    action_data = action.to_dict()
                    st.markdown(f"**[Action Board] {action_data.get('accion','(Sin descripción)')}**")
                    st.write(f"Inicio: {action_data.get('fecha_inicio','')}, Compromiso: {action_data.get('fecha_compromiso','')}, Real: {action_data.get('fecha_real','')}")
                    compromiso = action_data.get("fecha_compromiso", None)
                    if compromiso:
                        comp_date = datetime.strptime(compromiso, "%Y-%m-%d").date()
                        delay_indicator = "Delayed" if comp_date < date.today() else "On time"
                    else:
                        delay_indicator = "N/A"
                    current_usuario = action_data.get("usuario", "")
                    if user_code in TL_USERS:
                        new_usuario = st.selectbox("Modificar usuario", options=list(get_team_for_tl(current_usuario)), 
                                                    index=list(get_team_for_tl(current_usuario)).index(current_usuario),
                                                    key=f"mod_usuario_action_{action_data.get('id')}")
                        if new_usuario != current_usuario:
                            db.collection("actions").document(action_data.get("id")).update({"usuario": new_usuario})
                            st.success("Usuario actualizado.")
                    origen_field = action_data.get("origen", None)
                    if origen_field:
                        st.markdown(f"**Usuario:** {valid_users.get(current_usuario, current_usuario)} (Colaborador) - Creado por: {valid_users.get(origen_field, origen_field)}")
                    else:
                        st.markdown(f"**Usuario:** {valid_users.get(current_usuario, current_usuario)}")
                    st.markdown(f"**Status:** <span style='color:{status_colors.get(action_data.get('status',''), 'black')};'>{action_data.get('status','')}</span> - <strong>{delay_indicator}</strong>", unsafe_allow_html=True)
                    edit_key = f"edit_action_{action_data.get('id')}"
                    if st.session_state.get(edit_key, False):
                        new_status = st.selectbox("Nuevo status", ["Pendiente", "En proceso", "Completado"], key=f"action_status_{action_data.get('id')}")
                        custom_status = st.text_input("Status personalizado (opcional)", key=f"action_custom_{action_data.get('id')}")
                        if st.button("Guardar cambios", key=f"save_action_{action_data.get('id')}"):
                            final_status = get_status(new_status, custom_status)
                            compromiso = action_data.get("fecha_compromiso", "")
                            if compromiso:
                                comp_date = datetime.strptime(compromiso, "%Y-%m-%d").date()
                                time_label = "On time" if comp_date >= date.today() else "Delayed"
                            else:
                                time_label = "N/A"
                            fecha_real = datetime.now().strftime("%Y-%m-%d") if final_status.lower() == "completado" else action_data.get("fecha_real", "")
                            db.collection("actions").document(action_data.get("id")).update({
                                "status": final_status,
                                "fecha_real": fecha_real,
                                "time_label": time_label
                            })
                            st.success("Status actualizado.")
                            st.session_state[edit_key] = False
                    else:
                        if st.button("Editar status", key=f"edit_btn_action_{action_data.get('id')}"):
                            st.session_state[edit_key] = True
                    if st.button("🗑️ Eliminar", key=f"delete_action_{action_data.get('id')}"):
                        group_id = action_data.get("group_id")
                        if group_id:
                            delete_task_group("actions", group_id)
                        else:
                            db.collection("actions").document(action_data.get("id")).delete()
                        st.success("Acción eliminada.")
                    if st.button("Enviar a Top3", key=f"send_to_top3_{action_data.get('id')}"):
                        send_action_to_top3(db.collection("actions").document(action_data.get("id")))
                    st.markdown("---")
            else:
                st.info("No hay tareas Action Board asignadas.")
    
    # ------------------- Store DBSCHENKER -------------------
    elif menu_choice == "Store DBSCHENKER":
        st.subheader("🛍️ Store DBSCHENKER")
        st.write("Productos corporativos (prototipo):")
        products = [
            {"name": "Taza DBS", "price": 10, "image": "https://via.placeholder.com/150?text=Taza+DBS"},
            {"name": "Playera DBS", "price": 20, "image": "https://via.placeholder.com/150?text=Playera+DBS"},
            {"name": "Gorra DBS", "price": 15, "image": "https://via.placeholder.com/150?text=Gorra+DBS"}
        ]
        for prod in products:
            st.image(prod["image"], width=150)
            st.markdown(f"**{prod['name']}** - {prod['price']} DB COINS")
            if st.button(f"Comprar {prod['name']}", key=f"buy_{prod['name']}"):
                st.info("Función de compra no implementada.")
            st.markdown("---")
    
    # ------------------- Wallet -------------------
    elif menu_choice == "Wallet":
        st.subheader("💰 Mi Wallet (DB COINS)")
        wallet_ref = db.collection("wallets").document(user_code)
        doc = wallet_ref.get()
        current_coins = 0
        if doc.exists:
            current_coins = doc.to_dict().get("coins", 0)
        st.write(f"**Saldo actual:** {current_coins} DB COINS")
        if user_code == "LARANDA":
            add_coins = st.number_input("Generar DB COINS:", min_value=1, step=1, value=10)
            if st.button("Generar DB COINS"):
                new_balance = current_coins + add_coins
                wallet_ref.set({"coins": new_balance})
                st.success(f"Generados {add_coins} DB COINS. Nuevo saldo: {new_balance}.")
            st.markdown("### Funciones Administrativas")
            admin_key = st.text_input("Clave Admin", type="password")
            if admin_key == "ADMIN123":
                if st.button("Resetear todas las monedas a 0"):
                    for u in valid_users:
                        db.collection("wallets").document(u).set({"coins": 0})
                target = st.selectbox("Generar monedas para el usuario:", list(valid_users.keys()),
                                        format_func=lambda x: f"{valid_users[x]} ({x})")
                amt = st.number_input("Cantidad de DB COINS a generar:", min_value=1, step=1, value=10)
                if st.button("Generar para usuario seleccionado"):
                    target_ref = db.collection("wallets").document(target)
                    doc_target = target_ref.get()
                    current = 0
                    if doc_target.exists:
                        current = doc_target.to_dict().get("coins", 0)
                    target_ref.set({"coins": current + amt})
                    st.success(f"Generados {amt} DB COINS para {valid_users[target]}.")
    
    # ------------------- Communications -------------------
    elif menu_choice == "Communications":
        st.subheader("📢 Mensajes Importantes")
        mensaje = st.text_area("📝 Escribe un mensaje o anuncio")
        if st.button("📩 Enviar mensaje"):
            db.collection("communications").document().set({
                "usuario": user_code,
                "fecha": datetime.now().strftime("%Y-%m-%d"),
                "mensaje": mensaje
            })
            st.success("Mensaje enviado.")
    
    # ------------------- Calendar -------------------
    elif menu_choice == "Calendar":
        st.subheader("📅 Calendario")
        cal_option = st.radio("Selecciona una opción", ["Crear Evento", "Ver Calendario"])
        if cal_option == "Crear Evento":
            st.markdown("### Crear Evento")
            evento = st.text_input("📌 Nombre del evento")
            start_date, end_date = st.date_input("Selecciona el rango de fechas", value=(date.today(), date.today()))
            tipo_evento = st.radio("Tipo de evento", ["Público", "Privado"])
            if st.button("✅ Agendar evento"):
                event_data = {
                    "usuario": user_code,
                    "evento": evento,
                    "fecha": start_date.strftime("%Y-%m-%d"),
                    "fecha_fin": end_date.strftime("%Y-%m-%d"),
                    "publico": True if tipo_evento == "Público" else False
                }
                db.collection("calendar").document().set(event_data)
                st.success("Evento agendado.")
        else:
            st.markdown("### Ver Calendario")
            start_date, end_date = st.date_input("Selecciona el rango de fechas para ver eventos", value=(date.today(), date.today()))
            events = []
            for doc in db.collection("calendar").stream():
                data = doc.to_dict()
                if data.get("fecha"):
                    event_date = datetime.strptime(data["fecha"], "%Y-%m-%d").date()
                    if start_date <= event_date <= end_date:
                        title = data.get("evento", "Evento")
                        if not data.get("publico", False):
                            title += f" (Privado - {data.get('usuario','')})"
                        events.append({
                            "title": title,
                            "start": data.get("fecha")
                        })
            events_json = json.dumps(events)
            calendar_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset='utf-8' />
              <link href='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.css' rel='stylesheet' />
              <script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.js'></script>
              <style>
                body {{
                  margin: 0;
                  padding: 0;
                }}
                #calendar {{
                  max-width: 900px;
                  margin: 40px auto;
                }}
              </style>
            </head>
            <body>
              <div id='calendar'></div>
              <script>
                document.addEventListener('DOMContentLoaded', function() {{
                  var calendarEl = document.getElementById('calendar');
                  var calendar = new FullCalendar.Calendar(calendarEl, {{
                    initialView: 'dayGridMonth',
                    events: {events_json}
                  }});
                  calendar.render();
                }});
              </script>
            </body>
            </html>
            """
            components.html(calendar_html, height=600, scrolling=True)
    
    # ------------------- Consultorio Optimizacion -------------------
    elif menu_choice == "Consultorio Optimizacion":
        st.subheader("Consultorio de Optimización")
        st.markdown("Envía un archivo y/o un mensaje para requerir apoyo. Esto se enviará a **CNAPOLES**.")
        with st.form("consultorio_form"):
            mensaje_consult = st.text_area("Describe tu requerimiento o tarea:")
            archivo = st.file_uploader("Adjuntar archivo (opcional)")
            submit_consult = st.form_submit_button("Enviar Consulta")
        if submit_consult:
            data_consult = {
                "usuario": user_code,
                "mensaje": mensaje_consult,
                "archivo": archivo.name if archivo is not None else None,
                "fecha": datetime.now().strftime("%Y-%m-%d"),
                "destinatario": "CNAPOLES"
            }
            db.collection("consultorio").add(data_consult)
            st.success("Consulta enviada a CNAPOLES.")
    
    # ------------------- Contacto -------------------
    elif menu_choice == "Contacto":
        st.subheader("Contacto / Reporte de Problemas")
        st.markdown("Si tienes algún problema con la aplicación, por favor envía tu reporte aquí.")
        with st.form("contacto_form"):
            asunto_contact = st.text_input("Asunto:")
            mensaje_contact = st.text_area("Describe tu problema o sugerencia:")
            submit_contact = st.form_submit_button("Enviar Reporte")
        if submit_contact:
            data_contact = {
                "usuario": user_code,
                "asunto": asunto_contact,
                "mensaje": mensaje_contact,
                "fecha": datetime.now().strftime("%Y-%m-%d")
            }
            db.collection("contacto").add(data_contact)
            st.success("Reporte enviado. Gracias por tu feedback.")
    
show_main_app()
