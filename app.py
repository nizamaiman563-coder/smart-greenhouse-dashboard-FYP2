import base64
import random
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from fuzzy_controller import fuzzy_outputs

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Smart Greenhouse Command Centre",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = Path(__file__).resolve().parent
ASSET_DIR = APP_DIR / "assets"
GREENHOUSE_IMAGE = ASSET_DIR / "greenhouse_digital_twin.png"

# ============================================================
# PROJECT THRESHOLDS
# ============================================================
CONTROL = {
    "soil_low": 40.0,
    "temp_fan": 28.0,  # Used for warm/normal sensor status only
}

# EXAMPLE tank calibration. Replace these distances with measurements
# for YOUR tank: full = sensor-to-water distance when full; empty =
# sensor-to-bottom (or minimum usable water) distance when empty.
TANK = {
    "full_distance_cm": 4.0,
    "empty_distance_cm": 30.0,
    "low_level_pct": 25.0,
    "critical_level_pct": 15.0,
    "simulated_pump_usage_pct_per_min": 3.0,
}

ALARM = {
    "temp_high": 30.0,
    "soil_low": 40.0,
    "humidity_high": 80.0,
}

DEFAULT_READING = {
    "soil": 61.0,
    "temperature": 27.4,
    "humidity": 68.0,
    "tank_distance_cm": 13.5,
    "lighting_request_pct": 78.0,  # Simulated schedule demand; NOT a light sensor
}

SENSOR_META = {
    "temperature": {
        "name": "Temperature",
        "tag": "TT-101",
        "icon": "♨",
        "unit": "°C",
        "min": 15,
        "max": 40,
        "target": "≤ 30°C",
        "accent": "#ff9f43",
    },
    "humidity": {
        "name": "Humidity",
        "tag": "HT-101",
        "icon": "◉",
        "unit": "%",
        "min": 20,
        "max": 100,
        "target": "≤ 80%",
        "accent": "#17c9ff",
    },
    "soil": {
        "name": "Soil Moisture",
        "tag": "SM-101",
        "icon": "♧",
        "unit": "%",
        "min": 0,
        "max": 100,
        "target": "≥ 40%",
        "accent": "#35ef72",
    },
    "tank_level": {
        "name": "Ultrasonic Tank Level",
        "tag": "LT-201",
        "icon": "▤",
        "unit": "%",
        "min": 0,
        "max": 100,
        "target": "≥ 25% reserve",
        "accent": "#b86cff",
    },
}

SCENARIO_VALUES = {
    "FYP Preliminary Test": {
        "soil": 61.0,
        "temperature": 31.0,
        "humidity": 71.4,
        "tank_distance_cm": 17.0,
        "lighting_request_pct": 92.0,
    },
    "Normal Conditions": DEFAULT_READING,
    "Dry Soil": {
        "soil": 36.0,
        "temperature": 27.0,
        "humidity": 62.0,
        "tank_distance_cm": 12.0,
        "lighting_request_pct": 80.0,
    },
    "Low Tank Level": {
        "soil": 34.0,
        "temperature": 27.0,
        "humidity": 67.0,
        "tank_distance_cm": 25.0,
        "lighting_request_pct": 72.0,
    },
    "Tank Nearly Empty": {
        "soil": 30.0,
        "temperature": 28.0,
        "humidity": 67.0,
        "tank_distance_cm": 29.0,
        "lighting_request_pct": 72.0,
    },
    "Heat Stress": {
        "soil": 48.0,
        "temperature": 34.0,
        "humidity": 76.0,
        "tank_distance_cm": 15.0,
        "lighting_request_pct": 95.0,
    },
}

# ============================================================
# FUTURISTIC UI THEME
# ============================================================
st.markdown(
    """
    <style>
    :root {
        --bg:#020811;
        --panel:rgba(4,20,34,.88);
        --panel2:rgba(5,27,43,.74);
        --cyan:#10dfff;
        --cyan2:#4df2ff;
        --green:#35ef72;
        --blue:#168cff;
        --purple:#b86cff;
        --yellow:#ffc83d;
        --orange:#ff9f43;
        --red:#ff5d72;
        --text:#eefcff;
        --muted:#78a8ba;
        --line:rgba(29,219,255,.26);
    }

    html, body, [class*="css"] {font-family: Inter, "Segoe UI", Arial, sans-serif;}

    .stApp {
        color:var(--text);
        background:
            radial-gradient(circle at 45% -10%, rgba(0,157,255,.16), transparent 28%),
            radial-gradient(circle at 92% 16%, rgba(0,224,255,.08), transparent 22%),
            linear-gradient(145deg,#02050b 0%,#03101b 48%,#020812 100%);
    }

    .stApp::before {
        content:"";
        position:fixed;
        inset:0;
        pointer-events:none;
        opacity:.16;
        background-image:
            linear-gradient(rgba(0,208,255,.08) 1px,transparent 1px),
            linear-gradient(90deg,rgba(0,208,255,.08) 1px,transparent 1px);
        background-size:38px 38px;
        mask-image:linear-gradient(to bottom,black,transparent 82%);
        z-index:0;
    }

    .block-container {
        max-width:1880px;
        padding-top:.45rem;
        padding-bottom:1.6rem;
        padding-left:1.1rem;
        padding-right:1.1rem;
        position:relative;
        z-index:1;
    }

    [data-testid="stSidebar"] {
        background:linear-gradient(180deg,rgba(3,12,22,.995),rgba(4,20,32,.995));
        border-right:1px solid rgba(16,223,255,.20);
    }

    [data-testid="stSidebar"] .stRadio > label,
    [data-testid="stSidebar"] .stSelectbox > label,
    [data-testid="stSidebar"] .stSlider > label {
        color:#8dc5d5;
        font-size:.72rem;
        letter-spacing:.08em;
        text-transform:uppercase;
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    .stNumberInput input {
        background:rgba(5,27,43,.92)!important;
        border-color:rgba(16,223,255,.20)!important;
    }

    .top-shell {
        border:1px solid rgba(16,223,255,.24);
        border-radius:18px;
        background:linear-gradient(155deg,rgba(3,17,31,.94),rgba(3,31,47,.72));
        box-shadow:0 0 30px rgba(0,189,255,.05), inset 0 0 25px rgba(0,210,255,.025);
        padding:14px 18px;
        margin-bottom:8px;
    }

    .top-grid {
        display:grid;
        grid-template-columns:minmax(320px,1.8fr) repeat(3,minmax(150px,.55fr));
        gap:12px;
        align-items:center;
    }

    .brand-wrap {display:flex;align-items:center;gap:12px;}
    .brand-logo {
        width:48px;height:48px;border-radius:15px;
        display:grid;place-items:center;
        border:1px solid rgba(16,223,255,.48);
        background:radial-gradient(circle,rgba(53,239,114,.16),rgba(16,223,255,.05));
        box-shadow:0 0 22px rgba(16,223,255,.16),inset 0 0 18px rgba(53,239,114,.08);
        color:#35ef72;font-size:25px;
    }
    .brand-title {font-size:24px;font-weight:900;letter-spacing:.02em;color:#f4fdff;line-height:1.04;}
    .brand-sub {font-size:11px;font-weight:750;color:#10dfff;letter-spacing:.06em;margin-top:5px;}

    .head-card {
        min-height:52px;
        border-radius:13px;
        padding:9px 12px;
        border:1px solid rgba(16,223,255,.18);
        background:rgba(3,16,29,.56);
        display:flex;align-items:center;gap:9px;
    }
    .head-icon {font-size:18px;color:#10dfff;}
    .head-label {font-size:8px;color:#6c9bac;letter-spacing:.10em;text-transform:uppercase;}
    .head-value {font-size:13px;font-weight:850;color:#e9fbff;margin-top:2px;}
    .online {color:#35ef72;}

    .section-caption {
        display:flex;justify-content:space-between;align-items:end;gap:10px;
        margin:4px 0 7px;
    }
    .section-title {font-size:11px;font-weight:900;letter-spacing:.10em;color:#dffbff;text-transform:uppercase;}
    .section-sub {font-size:8px;color:#5f8d9e;letter-spacing:.08em;text-transform:uppercase;}

    .panel-shell {
        border:1px solid rgba(16,223,255,.20);
        border-radius:17px;
        background:linear-gradient(155deg,rgba(4,24,39,.84),rgba(2,13,24,.88));
        box-shadow:inset 0 0 28px rgba(16,223,255,.022),0 10px 32px rgba(0,0,0,.18);
        overflow:hidden;
    }

    .sensor-stack {
        border:1px solid rgba(16,223,255,.18);
        border-radius:17px;
        padding:10px;
        background:linear-gradient(160deg,rgba(4,23,38,.84),rgba(2,12,22,.90));
        min-height:606px;
    }
    .stack-head {padding:2px 3px 8px 3px;}
    .stack-title {font-size:11px;font-weight:900;color:#dffbff;letter-spacing:.09em;}
    .stack-sub {font-size:8px;color:#5e8ea0;margin-top:2px;}

    .sensor-card {
        min-height:99px;
        border:1px solid rgba(16,223,255,.16);
        border-radius:13px;
        padding:10px 11px;
        margin-bottom:8px;
        background:linear-gradient(150deg,rgba(6,31,48,.78),rgba(3,16,29,.76));
        position:relative;
        overflow:hidden;
    }
    .sensor-card:last-child {margin-bottom:0;}
    .sensor-card::after {
        content:"";position:absolute;right:-25px;bottom:-35px;width:92px;height:92px;border-radius:50%;
        background:radial-gradient(circle,var(--sensor-glow),transparent 66%);opacity:.15;
    }
    .sensor-top {display:flex;align-items:center;justify-content:space-between;gap:8px;}
    .sensor-main {display:flex;align-items:center;gap:9px;}
    .sensor-icon {
        width:34px;height:34px;border-radius:50%;display:grid;place-items:center;
        color:var(--sensor-accent);border:1px solid color-mix(in srgb,var(--sensor-accent) 52%,transparent);
        background:color-mix(in srgb,var(--sensor-accent) 9%,transparent);
        box-shadow:0 0 18px color-mix(in srgb,var(--sensor-accent) 18%,transparent);
        font-size:18px;font-weight:900;
    }
    .sensor-name {font-size:9px;color:#a8ced9;letter-spacing:.05em;}
    .sensor-value {font-size:21px;font-weight:900;color:#f2fdff;line-height:1;margin-top:4px;}
    .sensor-unit {font-size:9px;color:#85aab7;font-weight:700;margin-left:2px;}
    .status-chip {font-size:7px;font-weight:900;padding:4px 6px;border-radius:999px;letter-spacing:.07em;}
    .status-good {color:#64ff9a;background:rgba(53,239,114,.10);border:1px solid rgba(53,239,114,.22);}
    .status-warn {color:#ffc76c;background:rgba(255,159,67,.10);border:1px solid rgba(255,159,67,.22);}
    .status-bad {color:#ff8796;background:rgba(255,93,114,.10);border:1px solid rgba(255,93,114,.22);}
    .sensor-track {height:4px;border-radius:999px;background:rgba(255,255,255,.055);margin-top:8px;overflow:hidden;}
    .sensor-fill {height:100%;border-radius:999px;box-shadow:0 0 12px currentColor;}
    .sensor-foot {display:flex;justify-content:space-between;margin-top:5px;color:#4f7f90;font-size:7px;}
    .sensor-detail {font-size:8px;color:#a6b8ed;margin-top:5px;letter-spacing:.025em;}

    .twin-stage {
        position:relative;
        min-height:606px;
        border:1px solid rgba(16,223,255,.20);
        border-radius:17px;
        overflow:hidden;
        background:
            radial-gradient(circle at 50% 53%,rgba(0,180,255,.15),transparent 32%),
            linear-gradient(160deg,rgba(2,16,29,.90),rgba(2,10,19,.96));
        box-shadow:inset 0 0 45px rgba(16,223,255,.035),0 12px 34px rgba(0,0,0,.18);
    }
    .twin-stage::before {
        content:"";position:absolute;inset:0;opacity:.17;pointer-events:none;
        background-image:
            linear-gradient(rgba(18,206,255,.08) 1px,transparent 1px),
            linear-gradient(90deg,rgba(18,206,255,.08) 1px,transparent 1px);
        background-size:32px 32px;
        mask-image:radial-gradient(circle at 50% 52%,black,transparent 72%);
    }
    .twin-head {position:absolute;left:16px;top:13px;z-index:4;}
    .twin-title {font-size:12px;font-weight:900;color:#c9f7ff;letter-spacing:.07em;}
    .twin-sub {font-size:8px;color:#10dfff;margin-top:2px;}
    .twin-img {
        position:absolute;left:8%;top:18%;width:84%;height:67%;object-fit:cover;
        border-radius:18px;
        filter:saturate(1.12) contrast(1.04) drop-shadow(0 0 22px rgba(0,198,255,.22));
        opacity:.97;
        mask-image:radial-gradient(ellipse at center,black 62%,transparent 99%);
    }
    .twin-callout {
        position:absolute;z-index:5;min-width:120px;
        border:1px solid rgba(16,223,255,.32);
        border-radius:13px;padding:8px 10px;
        background:linear-gradient(145deg,rgba(4,28,44,.94),rgba(2,15,26,.92));
        box-shadow:0 0 20px rgba(0,197,255,.08),inset 0 0 14px rgba(0,197,255,.025);
    }
    .call-light {top:6%;left:42%;}
    .call-temp {top:23%;left:3%;border-color:rgba(255,159,67,.38);}
    .call-hum {top:42%;left:2%;}
    .call-tank {top:66%;left:3%;border-color:rgba(184,108,255,.38);}
    .call-soil {top:45%;right:2%;border-color:rgba(53,239,114,.38);}
    .call-label {font-size:7px;color:#79a8b8;letter-spacing:.08em;text-transform:uppercase;}
    .call-value {font-size:20px;font-weight:900;color:#f2fdff;line-height:1;margin-top:4px;}
    .call-unit {font-size:8px;color:#80a5b3;margin-left:2px;}
    .call-good {font-size:7px;color:#5cff93;margin-top:4px;font-weight:800;}
    .health-badge {
        position:absolute;z-index:6;left:50%;bottom:3%;transform:translateX(-50%);
        min-width:210px;text-align:center;padding:9px 14px;
        border:1px solid rgba(53,239,114,.48);border-radius:18px;
        background:linear-gradient(145deg,rgba(5,43,43,.94),rgba(3,20,31,.96));
        box-shadow:0 0 26px rgba(53,239,114,.14),inset 0 0 16px rgba(53,239,114,.06);
    }
    .health-label {font-size:7px;color:#9dd9ce;letter-spacing:.10em;}
    .health-value {font-size:27px;font-weight:950;color:#f6ffff;line-height:1;margin-top:3px;}
    .health-state {font-size:8px;color:#59ff93;font-weight:850;margin-top:4px;}

    .status-stack {
        border:1px solid rgba(16,223,255,.18);border-radius:17px;padding:10px;
        background:linear-gradient(160deg,rgba(4,23,38,.84),rgba(2,12,22,.90));min-height:606px;
    }
    .system-card {
        border:1px solid rgba(16,223,255,.16);border-radius:13px;padding:11px 12px;margin-bottom:9px;
        background:linear-gradient(150deg,rgba(6,31,48,.78),rgba(3,16,29,.76));min-height:94px;
    }
    .system-card:last-child {margin-bottom:0;}
    .system-row {display:flex;align-items:center;gap:10px;}
    .system-icon {
        width:38px;height:38px;border-radius:50%;display:grid;place-items:center;
        border:1px solid rgba(16,223,255,.38);background:rgba(16,223,255,.07);color:#10dfff;font-size:18px;
        box-shadow:0 0 15px rgba(16,223,255,.08);
    }
    .system-label {font-size:8px;color:#80a8b6;letter-spacing:.08em;text-transform:uppercase;}
    .system-value {font-size:17px;font-weight:900;color:#f2fdff;margin-top:3px;line-height:1.05;}
    .system-sub {font-size:7px;color:#5a8b9c;margin-top:5px;}

    .alert-wrap {
        border:1px solid rgba(16,223,255,.18);border-radius:17px;padding:12px;
        background:linear-gradient(160deg,rgba(4,23,38,.84),rgba(2,12,22,.90));min-height:260px;
    }
    .alert-safe {
        border:1px solid rgba(53,239,114,.22);border-radius:12px;padding:12px;background:rgba(53,239,114,.045);
        display:flex;gap:10px;align-items:center;margin-bottom:8px;
    }
    .alert-safe-icon {width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:rgba(53,239,114,.10);color:#35ef72;font-size:18px;}
    .alert-safe-title {font-size:10px;font-weight:900;color:#dfffea;}
    .alert-safe-sub {font-size:7px;color:#69a786;margin-top:3px;}
    .alert-item {border:1px solid rgba(255,93,114,.20);border-radius:10px;padding:8px 9px;margin-bottom:6px;background:rgba(255,93,114,.04);}
    .alert-item-title {font-size:8px;font-weight:900;color:#ff8796;}
    .alert-item-text {font-size:7px;color:#9f6f78;margin-top:3px;}

    .quick-grid {display:grid;grid-template-columns:1fr 1fr;gap:8px;}
    .quick-card {
        min-height:106px;border:1px solid rgba(16,223,255,.16);border-radius:12px;padding:10px;
        background:linear-gradient(150deg,rgba(6,31,48,.78),rgba(3,16,29,.76));text-align:center;
    }
    .quick-icon {font-size:18px;color:#10dfff;}
    .quick-label {font-size:7px;color:#6f9dac;text-transform:uppercase;letter-spacing:.08em;margin-top:5px;}
    .quick-value {font-size:18px;font-weight:900;color:#f3fdff;margin-top:5px;}
    .quick-sub {font-size:7px;color:#35ef72;font-weight:750;margin-top:4px;}

    .control-card {
        border:1px solid rgba(16,223,255,.16);border-radius:15px;padding:14px;
        background:linear-gradient(155deg,rgba(6,31,48,.76),rgba(3,16,29,.82));min-height:124px;
    }
    .control-top {display:flex;align-items:center;justify-content:space-between;}
    .control-name {font-size:10px;color:#a9d0da;}
    .control-state {font-size:22px;font-weight:900;margin-top:8px;}
    .state-on {color:#35ef72;}.state-off {color:#617d89;}
    .control-rule {font-size:8px;color:#5d8998;margin-top:7px;}
    .pwm-track{height:7px;background:rgba(71,120,146,.19);border:1px solid rgba(16,223,255,.12);border-radius:12px;overflow:hidden;margin-top:10px;}
    .pwm-fill{height:100%;border-radius:12px;background:linear-gradient(90deg,#1d94d9,#10dfff,#35ef72);box-shadow:0 0 10px rgba(16,223,255,.35);transition:width .5s;}
    .pwm-foot{font-size:8px;color:#7cbacc;margin-top:6px;}
    .pwm-live-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:0 0 12px;}
    .pwm-live-card{padding:11px 13px;background:linear-gradient(135deg,rgba(6,36,54,.9),rgba(7,24,38,.94));border:1px solid rgba(16,223,255,.22);border-radius:12px;}
    .pwm-live-title{font-size:9px;color:#8cb6c4;font-weight:700;letter-spacing:.04em;}
    .pwm-live-value{font-size:22px;color:#e2faff;font-weight:900;margin-top:4px;}
    .pwm-live-unit{font-size:9px;color:#6894a2;font-weight:600;}
    @media(max-width:650px){.pwm-live-grid{grid-template-columns:1fr;}}

    .stTabs [data-baseweb="tab-list"] {
        gap:4px;background:rgba(2,14,25,.86);border:1px solid rgba(16,223,255,.16);border-radius:12px;padding:4px;margin-bottom:8px;
    }
    .stTabs [data-baseweb="tab"] {
        height:38px;border-radius:9px;color:#759cab;font-size:10px;font-weight:800;padding:0 20px;
    }
    .stTabs [aria-selected="true"] {
        background:rgba(16,223,255,.10);color:#dffaff!important;box-shadow:inset 0 0 14px rgba(16,223,255,.04);
    }

    div[data-testid="stPlotlyChart"] {
        border:1px solid rgba(16,223,255,.16);border-radius:17px;
        background:linear-gradient(155deg,rgba(4,23,38,.82),rgba(2,12,22,.88));padding:3px;
    }
    div[data-testid="stDataFrame"] {border:1px solid rgba(16,223,255,.14);border-radius:14px;overflow:hidden;}
    div[data-testid="stMetric"] {display:none;}

    .brand-lockup {display:flex;gap:10px;align-items:center;padding:8px 1px 16px;}
    .brand-mark {width:40px;height:40px;border-radius:12px;display:grid;place-items:center;border:1px solid rgba(16,223,255,.35);color:#35ef72;background:rgba(16,223,255,.05);font-size:21px;}
    .brand-name {font-size:12px;font-weight:900;letter-spacing:.08em;color:#effcff;}
    .brand-side-sub {font-size:8px;color:#608b9c;margin-top:2px;letter-spacing:.08em;}
    .logic-chip {display:inline-block;padding:5px 7px;border-radius:7px;margin:2px 3px 2px 0;font-size:8px;color:#9bc6d3;border:1px solid rgba(16,223,255,.13);background:rgba(7,27,39,.55);}
    .footer-note {margin-top:14px;padding-top:9px;border-top:1px solid rgba(16,223,255,.08);color:#416d7d;font-size:8px;letter-spacing:.07em;text-transform:uppercase;display:flex;justify-content:space-between;gap:10px;}

    @media(max-width:1100px){
        .top-grid{grid-template-columns:1fr 1fr;}
        .brand-title{font-size:20px;}
        .twin-stage,.sensor-stack,.status-stack{min-height:auto;}
        .twin-stage{min-height:560px;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# HELPERS
# ============================================================
def image_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def compact_html(html: str) -> str:
    """Remove indentation/newlines that Markdown may interpret as code blocks."""
    return "".join(line.strip() for line in html.splitlines() if line.strip())


def ultrasonic_level_pct(distance_cm):
    """Map top-mounted ultrasonic distance (cm) to 0–100% tank fill."""
    full = TANK["full_distance_cm"]
    empty = TANK["empty_distance_cm"]
    if empty <= full:
        raise ValueError("Tank empty distance must exceed full distance")
    return max(0.0, min(100.0, 100.0 * (empty - distance_cm) / (empty - full)))


def ultrasonic_distance_cm(level_pct):
    """Inverse mapping; used only for simulated tank drain/refill."""
    level_pct = max(0.0, min(100.0, level_pct))
    return TANK["empty_distance_cm"] - level_pct / 100.0 * (
        TANK["empty_distance_cm"] - TANK["full_distance_cm"]
    )


def with_tank_level(r):
    r = dict(r)
    r["tank_level"] = ultrasonic_level_pct(r["tank_distance_cm"])
    return r


def evaluate_alarms(r):
    alarms = []
    if r["temperature"] > ALARM["temp_high"]:
        alarms.append(("High Temperature", f"TT-101 is {r['temperature']:.1f} °C. Fuzzy ventilation should increase PWM duty."))
    if r["soil"] < ALARM["soil_low"]:
        alarms.append(("Low Soil Moisture", f"SM-101 is {r['soil']:.1f}%. Irrigation requested if sufficient tank water remains."))
    if r["humidity"] > ALARM["humidity_high"]:
        alarms.append(("High Humidity", f"HT-101 is {r['humidity']:.1f}%. Increase ventilation."))
    if r["tank_level"] <= TANK["critical_level_pct"]:
        alarms.append(("Critical Water Level", f"LT-201 indicates {r['tank_level']:.1f}% remaining (ultrasonic distance {r['tank_distance_cm']:.1f} cm). Pump is inhibited to avoid dry running."))
    elif r["tank_level"] <= TANK["low_level_pct"]:
        alarms.append(("Low Tank Level", f"LT-201 indicates {r['tank_level']:.1f}% remaining. Refill the reservoir soon."))
    return alarms


def auto_outputs(r):
    """Pump is threshold-based; fan and LED commands use Sugeno fuzzy rules."""
    pwm = fuzzy_outputs(r["temperature"], r["humidity"], r["lighting_request_pct"])
    return {
        "pump": r["soil"] < CONTROL["soil_low"] and r["tank_level"] > TANK["critical_level_pct"],
        **pwm,
    }


def sensor_status(key, value):
    if key == "temperature":
        if value > ALARM["temp_high"]:
            return "HIGH", "bad"
        if value > CONTROL["temp_fan"]:
            return "WARM", "warn"
        return "NORMAL", "good"
    if key == "soil":
        return ("LOW", "bad") if value < ALARM["soil_low"] else ("NORMAL", "good")
    if key == "humidity":
        return ("HIGH", "bad") if value > ALARM["humidity_high"] else ("NORMAL", "good")
    if key == "tank_level":
        if value <= TANK["critical_level_pct"]:
            return "CRITICAL", "bad"
        if value <= TANK["low_level_pct"]:
            return "LOW", "warn"
        return "NORMAL", "good"
    return "NORMAL", "good"


def normalized_percent(key, value):
    meta = SENSOR_META[key]
    pct = (value - meta["min"]) / (meta["max"] - meta["min"]) * 100
    return max(3, min(100, pct))


def sensor_card(key, value, distance_cm=None):
    meta = SENSOR_META[key]
    status, cls = sensor_status(key, value)
    decimals = 1
    pct = normalized_percent(key, value)
    detail = f'<div class="sensor-detail">Ultrasonic distance: {distance_cm:.1f} cm</div>' if key == "tank_level" and distance_cm is not None else ""
    return compact_html(f"""
    <div class="sensor-card" style="--sensor-accent:{meta['accent']};--sensor-glow:{meta['accent']}">
        <div class="sensor-top">
            <div class="sensor-main">
                <div class="sensor-icon">{meta['icon']}</div>
                <div>
                    <div class="sensor-name">{meta['name']}</div>
                    <div class="sensor-value">{value:.{decimals}f}<span class="sensor-unit"> {meta['unit']}</span></div>
                </div>
            </div>
            <div class="status-chip status-{cls}">{status}</div>
        </div>
        <div class="sensor-track"><div class="sensor-fill" style="width:{pct:.0f}%;background:{meta['accent']};color:{meta['accent']}"></div></div>
        <div class="sensor-foot"><span>{meta['min']}</span><span>{meta['target']}</span><span>{meta['max']}</span></div>
        {detail}
    </div>
    """)


def system_health(r):
    # Continuous presentation score centred around desirable greenhouse conditions.
    temp_score = max(0, 100 - abs(r["temperature"] - 25.0) * 6.0)
    hum_score = max(0, 100 - abs(r["humidity"] - 65.0) * 1.2)
    soil_score = max(0, 100 - abs(r["soil"] - 60.0) * 1.0)
    tank_score = min(100.0, r["tank_level"] / TANK["low_level_pct"] * 100.0)
    score = int(round((temp_score + hum_score + soil_score + tank_score) / 4))

    # Hard threshold breaches reduce the overall score visibly.
    breaches = len(evaluate_alarms(r))
    if breaches:
        score = min(score, max(25, 82 - (breaches - 1) * 12))
    return max(0, min(100, score))


def jitter_reading(base, intensity=1.0):
    return {
        "soil": max(0, min(100, base["soil"] + random.uniform(-0.7, 0.7) * intensity)),
        "temperature": base["temperature"] + random.uniform(-0.22, 0.22) * intensity,
        "humidity": max(0, min(100, base["humidity"] + random.uniform(-0.45, 0.45) * intensity)),
        "tank_distance_cm": max(TANK["full_distance_cm"], min(TANK["empty_distance_cm"], base["tank_distance_cm"] + random.uniform(-0.10, 0.10) * intensity)),
        "lighting_request_pct": base["lighting_request_pct"],
    }


def new_history_row(r, outputs):
    return {
        "time": datetime.now(),
        "Temperature (°C)": round(r["temperature"], 1),
        "Humidity (%)": round(r["humidity"], 1),
        "Soil Moisture (%)": round(r["soil"], 1),
        "Lighting Request (%)": round(r["lighting_request_pct"], 1),
        "Tank Level (%)": round(r["tank_level"], 1),
        "Ultrasonic Distance (cm)": round(r["tank_distance_cm"], 2),
        "Pump": int(outputs["pump"]),
        "Fan 1 PWM (%)": round(outputs["fan1_pct"], 1),
        "Fan 2 PWM (%)": round(outputs["fan2_pct"], 1),
        "Grow LED PWM (%)": round(outputs["led_pct"], 1),
    }


def chart_layout(fig, height=290):
    fig.update_layout(
        height=height,
        margin=dict(l=18, r=18, t=46, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8eb5c2", size=9),
        hoverlabel=dict(bgcolor="#041827", font_color="#effcff", bordercolor="#10dfff"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)", font=dict(size=8)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color="#547f90")
    fig.update_yaxes(gridcolor="rgba(16,223,255,.07)", zeroline=False, color="#547f90")
    return fig


def environment_trend(df):
    fig = go.Figure()
    traces = [
        ("Temperature (°C)", "#ff9f43", "y"),
        ("Humidity (%)", "#17c9ff", "y"),
        ("Soil Moisture (%)", "#35ef72", "y"),
        ("Tank Level (%)", "#b86cff", "y"),
    ]
    for col, color, axis in traces:
        fig.add_trace(go.Scatter(x=df["time"], y=df[col], mode="lines", name=col, line=dict(width=2, color=color), yaxis=axis))
    fig.update_layout(
        title=dict(text="ENVIRONMENT TREND · LIVE", font=dict(size=11, color="#dffbff"), x=.02),
        yaxis=dict(title="Climate / Soil / Tank", gridcolor="rgba(16,223,255,.07)", color="#547f90"),
    )
    return chart_layout(fig, 260)


def pwm_trend(df):
    fig = go.Figure()
    for field, color in [
        ("Fan 1 PWM (%)", "#10dfff"),
        ("Fan 2 PWM (%)", "#b86cff"),
        ("Grow LED PWM (%)", "#ffc83d"),
    ]:
        fig.add_trace(go.Scatter(x=df["time"], y=df[field], mode="lines", name=field, line=dict(width=2.5, color=color)))
    fig.update_layout(title=dict(text="FUZZY PWM OUTPUTS · LIVE", font=dict(size=11, color="#dffbff"), x=.02))
    fig.update_yaxes(title="Duty cycle (%)", range=[0, 105])
    return chart_layout(fig, 260)


def line_chart(df, columns, title, y_title):
    palette = ["#10dfff", "#35ef72", "#b86cff", "#ffc83d", "#ff7a88"]
    fig = go.Figure()
    for i, col in enumerate(columns):
        fig.add_trace(go.Scatter(x=df["time"], y=df[col], mode="lines", name=col, line=dict(width=2.2, color=palette[i % len(palette)])))
    fig.update_layout(title=dict(text=title, font=dict(size=12, color="#dffaff")))
    fig.update_yaxes(title=y_title)
    return chart_layout(fig, 320)


def health_gauge(health):
    color = "#35ef72" if health >= 80 else "#ffbd66" if health >= 60 else "#ff5d72"
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=health,
            number={"suffix": "%", "font": {"size": 38, "color": "#effcff"}},
            title={"text": "SYSTEM HEALTH", "font": {"size": 10, "color": "#75a5b4"}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 0, "tickfont": {"color": "#547f90"}},
                "bar": {"color": color, "thickness": .22},
                "bgcolor": "rgba(255,255,255,.03)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 60], "color": "rgba(255,93,114,.06)"},
                    {"range": [60, 80], "color": "rgba(255,200,61,.05)"},
                    {"range": [80, 100], "color": "rgba(53,239,114,.05)"},
                ],
            },
        )
    )
    fig.update_layout(height=285, margin=dict(l=28, r=28, t=45, b=22), paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#8eb5c2"))
    return fig


def environmental_radar(r):
    values = [
        max(0, min(100, 100 - abs(r["temperature"] - 25) * 7)),
        max(0, min(100, 100 - abs(r["humidity"] - 65) * 2)),
        max(0, min(100, 100 - abs(r["soil"] - 60) * 1.5)),
        max(0, min(100, r["tank_level"] / TANK["low_level_pct"] * 100)),
    ]
    cats = ["Thermal", "Humidity", "Soil", "Tank"]
    fig = go.Figure(go.Scatterpolar(r=values + [values[0]], theta=cats + [cats[0]], fill="toself", line=dict(color="#10dfff", width=2), fillcolor="rgba(16,223,255,.11)"))
    fig.update_layout(
        height=285,
        margin=dict(l=28, r=28, t=35, b=26),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(color="#82aab8", size=9),
        polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=True, range=[0,100], showticklabels=False, gridcolor="rgba(16,223,255,.08)"), angularaxis=dict(gridcolor="rgba(16,223,255,.08)")),
    )
    return fig


def output_card(icon, name, tag, value, rule, is_pump=False):
    """Proportional duty display for fans/LED; boolean state for pump."""
    pct = (100.0 if value else 0.0) if is_pump else max(0.0, min(100.0, float(value)))
    is_on = pct > 0.1
    state = ("ON" if is_on else "OFF") if is_pump else f"{pct:.1f}%"
    cls = "state-on" if is_on else "state-off"
    mode_note = "Relay / ON-OFF" if is_pump else "PWM duty request · 0–100%"
    return compact_html(f"""
    <div class="control-card">
        <div class="control-top"><span style="font-size:18px;color:#10dfff">{icon}</span><span class="status-chip {'status-good' if is_on else 'status-warn'}">{tag}</span></div>
        <div class="control-name">{name}</div>
        <div class="control-state {cls}">{state}</div>
        <div class="pwm-track"><div class="pwm-fill" style="width:{pct:.1f}%"></div></div>
        <div class="pwm-foot">{mode_note}</div>
        <div class="control-rule">{rule}</div>
    </div>
    """)


def pwm_summary_html(outputs):
    """Glanceable live proportional output cards on the Overview page."""
    html = '<div class="pwm-live-grid">'
    for name, tag, val in [
        ("✣ FAN 1 · VENTILATION", "FAN-101", outputs["fan1_pct"]),
        ("✣ FAN 2 · EXHAUST", "FAN-102", outputs["fan2_pct"]),
        ("☀ FULL-SPECTRUM LED", "LED-101", outputs["led_pct"]),
    ]:
        html += f'<div class="pwm-live-card"><div class="pwm-live-title">{name} · {tag}</div><div class="pwm-live-value">{val:.1f}% <span class="pwm-live-unit">PWM DUTY</span></div><div class="pwm-track"><div class="pwm-fill" style="width:{val:.1f}%"></div></div></div>'
    return compact_html(html + '</div>')


def twin_html(r, health, outputs):
    uri = image_data_uri(GREENHOUSE_IMAGE)
    health_state = "Excellent" if health >= 90 else "Good" if health >= 80 else "Attention"
    return compact_html(f"""
    <div class="twin-stage">
        <div class="twin-head"><div class="twin-title">◉ DIGITAL TWIN</div><div class="twin-sub">Live greenhouse visualisation</div></div>
        <img class="twin-img" src="{uri}" alt="Modern smart greenhouse digital twin" />
        <div class="twin-callout call-light"><div class="call-label">☀ Grow LED</div><div class="call-value">{outputs['led_pct']:.1f}<span class="call-unit"> % PWM</span></div><div class="call-good">FUZZY BRIGHTNESS</div></div>
        <div class="twin-callout call-temp"><div class="call-label">♨ Temperature</div><div class="call-value">{r['temperature']:.1f}<span class="call-unit"> °C</span></div><div class="call-good">LIVE SENSOR</div></div>
        <div class="twin-callout call-hum"><div class="call-label">◉ Humidity</div><div class="call-value">{r['humidity']:.1f}<span class="call-unit"> %</span></div><div class="call-good">LIVE SENSOR</div></div>
        <div class="twin-callout call-tank"><div class="call-label">▤ Water Tank</div><div class="call-value">{r['tank_level']:.1f}<span class="call-unit"> %</span></div><div class="call-good">ULTRASONIC · {r['tank_distance_cm']:.1f} cm</div></div>
        <div class="twin-callout call-soil"><div class="call-label">♧ Soil Moisture</div><div class="call-value">{r['soil']:.1f}<span class="call-unit"> %</span></div><div class="call-good">ROOT ZONE</div></div>
        <div class="health-badge"><div class="health-label">SYSTEM HEALTH</div><div class="health-value">{health}%</div><div class="health-state">{health_state.upper()}</div></div>
    </div>
    """)


def status_card(icon, label, value, sub, green=True):
    value_cls = "online" if green else ""
    return compact_html(f"""
    <div class="system-card">
        <div class="system-row">
            <div class="system-icon">{icon}</div>
            <div><div class="system-label">{label}</div><div class="system-value {value_cls}">{value}</div><div class="system-sub">{sub}</div></div>
        </div>
    </div>
    """)


def uptime_text(start):
    seconds = int((datetime.now() - start).total_seconds())
    hours, rem = divmod(seconds, 3600)
    minutes, _ = divmod(rem, 60)
    return f"{hours:02d}h {minutes:02d}m"


# ============================================================
# SIDEBAR CONTROLS
# ============================================================
st.sidebar.markdown(
    compact_html("""
    <div class="brand-lockup"><div class="brand-mark">🌱</div><div><div class="brand-name">SMART GREENHOUSE</div><div class="brand-side-sub">SIMULATION & CONTROL PANEL</div></div></div>
    """),
    unsafe_allow_html=True,
)

mode = st.sidebar.radio("System mode", ["AUTO", "MANUAL"], horizontal=True)
scenario_options = ["FYP Preliminary Test", "Normal Conditions", "Dry Soil", "Low Tank Level", "Tank Nearly Empty", "Heat Stress", "Custom"]
scenario = st.sidebar.selectbox("Demo scenario", scenario_options, index=1)
live_demo = st.sidebar.toggle("Live telemetry simulation", value=True)
refresh_speed = st.sidebar.select_slider("Telemetry refresh", options=["1 sec", "2 sec", "5 sec"], value="2 sec")
noise = st.sidebar.slider("Simulation variation", 0.0, 2.0, 0.7, 0.1)

if scenario == "Custom":
    st.sidebar.markdown("#### Custom telemetry")
    base_reading = {
        "temperature": st.sidebar.slider("Temperature (°C)", 10.0, 45.0, 27.0, .5),
        "humidity": st.sidebar.slider("Humidity (%)", 20.0, 100.0, 65.0, 1.0),
        "soil": st.sidebar.slider("Soil Moisture (%)", 0.0, 100.0, 55.0, 1.0),
        "lighting_request_pct": st.sidebar.slider("Lighting request (%) · demo schedule", 0.0, 100.0, 80.0, 1.0),
        "tank_distance_cm": st.sidebar.slider("Ultrasonic distance to water (cm)", TANK["full_distance_cm"], TANK["empty_distance_cm"], 13.5, 0.5),
    }
else:
    base_reading = dict(SCENARIO_VALUES[scenario])

manual_states = None
if mode == "MANUAL":
    st.sidebar.markdown("#### Manual output control")
    manual_states = {
        "pump": st.sidebar.toggle("Water Pump · P-101", value=False),
        "fan1_pct": float(st.sidebar.slider("Fan 1 PWM (%) · FAN-101", 0, 100, 0, 1)),
        "fan2_pct": float(st.sidebar.slider("Fan 2 PWM (%) · FAN-102", 0, 100, 0, 1)),
        "led_pct": float(st.sidebar.slider("LED brightness (%) · LED-101", 0, 100, 0, 1)),
    }
else:
    st.sidebar.caption("Fuzzy rules control Fan 1, Fan 2 and the grow LED automatically. Switch to MANUAL for individual 0–100% PWM sliders.")

st.sidebar.markdown("---")
st.sidebar.markdown("#### Fuzzy lighting input")
if scenario != "Custom":
    st.sidebar.caption("This is a simulated photoperiod / lighting demand, not a measured lux value.")
    light_request = st.sidebar.slider("Lighting request (%) · demo schedule", 0.0, 100.0, float(base_reading["lighting_request_pct"]), 1.0)
    base_reading["lighting_request_pct"] = light_request
else:
    st.sidebar.caption("Custom scenario lighting request is controlled above.")
st.sidebar.markdown("#### Water tank simulation")
st.sidebar.caption(f"Example calibration: full at {TANK['full_distance_cm']:.0f} cm, empty at {TANK['empty_distance_cm']:.0f} cm; recalibrate for your tank.")
refill_demo = st.sidebar.button("Refill tank to 100% (demo)")
st.sidebar.markdown('<span class="logic-chip">SIMULATION MODE</span><span class="logic-chip">MQTT NOT CONNECTED</span><span class="logic-chip">CLOUD NOT CONNECTED</span>', unsafe_allow_html=True)
st.sidebar.caption("SIMULATION ONLY: no MQTT or physical PWM output. LED demand is a demonstration schedule request, not a light sensor reading. Real ESP32 PWM needs rated drivers.")

refresh_seconds = {"1 sec":1, "2 sec":2, "5 sec":5}[refresh_speed]

# ============================================================
# SESSION STATE
# ============================================================
if "history" not in st.session_state:
    st.session_state.history = []
if "session_started" not in st.session_state:
    st.session_state.session_started = datetime.now()

# A scenario change resets the simulated reservoir. A refill button lets the
# user demonstrate recovery from a low-water pump interlock.
tank_signature = (scenario, base_reading["tank_distance_cm"])
if st.session_state.get("tank_signature") != tank_signature:
    st.session_state.tank_signature = tank_signature
    st.session_state.tank_level_pct = ultrasonic_level_pct(base_reading["tank_distance_cm"])
if refill_demo:
    st.session_state.tank_level_pct = 100.0

# Plant model and pump hysteresis remain in session state across refreshes.
# They reset when a new scenario or physical starting point is selected.
plant_signature = (scenario, base_reading["temperature"], base_reading["humidity"], base_reading["soil"])
if st.session_state.get("plant_signature") != plant_signature:
    st.session_state.plant_signature = plant_signature
    st.session_state.plant = dict(base_reading)
    st.session_state.pump_latched = False

# ============================================================
# LIVE APP
# ============================================================
@st.fragment(run_every=f"{refresh_seconds}s")
def live_dashboard():
    r = jitter_reading(st.session_state.plant, noise * .35) if live_demo else dict(base_reading)
    # Lighting request is a schedule input, not a physical brightness reading.
    r["lighting_request_pct"] = base_reading["lighting_request_pct"]
    if live_demo:
        # Reservoir level responds to irrigation; ultrasonic echo has noise.
        distance = ultrasonic_distance_cm(st.session_state.tank_level_pct)
        r["tank_distance_cm"] = max(TANK["full_distance_cm"], min(TANK["empty_distance_cm"], distance + random.uniform(-.08, .08) * noise))
    r = with_tank_level(r)
    outputs = auto_outputs(r) if mode == "AUTO" else dict(manual_states)

    # Real plants need irrigation hysteresis to prevent frequent pump cycling.
    if mode == "AUTO":
        if r["soil"] < CONTROL["soil_low"] and r["tank_level"] > TANK["critical_level_pct"]:
            st.session_state.pump_latched = True
        if r["soil"] >= 55.0 or r["tank_level"] <= TANK["critical_level_pct"]:
            st.session_state.pump_latched = False
        outputs["pump"] = st.session_state.pump_latched
    if r["tank_level"] <= TANK["critical_level_pct"]:
        outputs["pump"] = False  # Manual mode cannot bypass dry-run protection.
        st.session_state.pump_latched = False

    if live_demo:
        dt = float(refresh_seconds)
        if outputs["pump"]:
            st.session_state.tank_level_pct = max(0.0, st.session_state.tank_level_pct - TANK["simulated_pump_usage_pct_per_min"] * dt / 60.0)
        # Simplified illustrative plant model for visible closed-loop effects.
        # This is NOT a validated crop/thermal or hydraulic model.
        plant = st.session_state.plant
        fan_mean = (outputs["fan1_pct"] + outputs["fan2_pct"]) / 2.0
        plant["temperature"] += (base_reading["temperature"] - plant["temperature"]) * .015 * dt - fan_mean * .0014 * dt + outputs["led_pct"] * .00025 * dt
        plant["humidity"] = max(0.0, min(100.0, plant["humidity"] + (base_reading["humidity"] - plant["humidity"]) * .015 * dt - outputs["fan2_pct"] * .0015 * dt + (0.018 * dt if outputs["pump"] else 0.0)))
        plant["soil"] = max(0.0, min(100.0, plant["soil"] + (0.55 * dt if outputs["pump"] else -0.012 * dt)))
    alarms = evaluate_alarms(r)
    health = system_health(r)
    efficiency = max(0, min(100, int(round(health * .98))))

    st.session_state.history.append(new_history_row(r, outputs))
    st.session_state.history = st.session_state.history[-240:]
    df = pd.DataFrame(st.session_state.history)

    # Header matching the command-centre reference interface.
    st.markdown(
        compact_html(f"""
        <div class="top-shell">
            <div class="top-grid">
                <div class="brand-wrap"><div class="brand-logo">🌱</div><div><div class="brand-title">SMART GREENHOUSE</div><div class="brand-sub">EDGE–CLOUD CONTROL · SIMULATION</div></div></div>
                <div class="head-card"><div class="head-icon">●</div><div><div class="head-label">System Status</div><div class="head-value online">DEMO ACTIVE</div></div></div>
                <div class="head-card"><div class="head-icon">◷</div><div><div class="head-label">Last Update</div><div class="head-value">{datetime.now().strftime('%H:%M:%S')}</div></div></div>
                <div class="head-card"><div class="head-icon">AI</div><div><div class="head-label">Control Mode</div><div class="head-value online">{mode} MODE</div></div></div>
            </div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    overview_tab, trends_tab, control_tab, analytics_tab, log_tab = st.tabs([
        "⌂  OVERVIEW", "⌁  TRENDS", "⚙  CONTROL", "◈  ANALYTICS", "▦  DATA LOG"
    ])

    with overview_tab:
        st.markdown(pwm_summary_html(outputs), unsafe_allow_html=True)
        left, centre, right = st.columns([1.02, 2.35, 1.02], gap="small")

        with left:
            sensor_html = '<div class="sensor-stack"><div class="stack-head"><div class="stack-title">GREENHOUSE TELEMETRY</div><div class="stack-sub">Real-time sensor readings</div></div>'
            for key in ["temperature", "humidity", "soil", "tank_level"]:
                sensor_html += sensor_card(key, r[key], r["tank_distance_cm"] if key == "tank_level" else None)
            sensor_html += '</div>'
            st.markdown(compact_html(sensor_html), unsafe_allow_html=True)

        with centre:
            st.markdown(compact_html(twin_html(r, health, outputs)), unsafe_allow_html=True)

        with right:
            right_html = '<div class="status-stack"><div class="stack-head"><div class="stack-title">SYSTEM STATUS</div><div class="stack-sub">Platform & connectivity</div></div>'
            right_html += status_card("AI", "Control Mode", f"{mode} MODE", "Sugeno fuzzy PWM · 2 fans + LED", True)
            right_html += status_card("◉", "Telemetry", "SIMULATED", "4 physical sensor parameters", True)
            right_html += status_card("⌁", "MQTT Connection", "NOT CONNECTED", "Ready for Raspberry Pi 5 integration", False)
            right_html += status_card("☁", "Cloud Status", "NOT CONNECTED", "Demo only · no cloud data sent", False)
            right_html += status_card("∿", "Data Stream", "LIVE", f"Refresh every {refresh_seconds}s", True)
            right_html += '</div>'
            st.markdown(compact_html(right_html), unsafe_allow_html=True)

        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        trend_col, alert_col, quick_col = st.columns([1.75, 1.03, 1.14], gap="small")

        with trend_col:
            st.plotly_chart(environment_trend(df), use_container_width=True, config={"displayModeBar":False})
            st.plotly_chart(pwm_trend(df), use_container_width=True, config={"displayModeBar":False})

        with alert_col:
            if alarms:
                alert_html = '<div class="alert-wrap"><div class="stack-title">ALERTS & NOTIFICATIONS</div><div class="stack-sub" style="margin-bottom:8px">Live threshold events</div>'
                for title, text in alarms[:4]:
                    alert_html += f'<div class="alert-item"><div class="alert-item-title">⚠ {title}</div><div class="alert-item-text">{text}</div></div>'
                alert_html += '</div>'
            else:
                alert_html = f'''<div class="alert-wrap"><div class="stack-title">ALERTS & NOTIFICATIONS</div><div class="stack-sub" style="margin-bottom:8px">System event console</div><div class="alert-safe"><div class="alert-safe-icon">✓</div><div><div class="alert-safe-title">All conditions normal</div><div class="alert-safe-sub">System operating within configured limits.</div></div></div><div class="alert-item" style="border-color:rgba(16,223,255,.12);background:rgba(16,223,255,.025)"><div class="alert-item-title" style="color:#74dcec">● Sensor data updated</div><div class="alert-item-text">{datetime.now().strftime('%H:%M:%S')} · four sensor parameters updated</div></div><div class="alert-item" style="border-color:rgba(16,223,255,.12);background:rgba(16,223,255,.025)"><div class="alert-item-title" style="color:#74dcec">● Simulation active</div><div class="alert-item-text">No physical MQTT connection in this version</div></div></div>'''
            st.markdown(compact_html(alert_html), unsafe_allow_html=True)

        with quick_col:
            points = len(df) * 4
            quick_html = f'''<div class="alert-wrap"><div class="stack-title">QUICK OVERVIEW</div><div class="stack-sub" style="margin-bottom:8px">Current session</div><div class="quick-grid"><div class="quick-card"><div class="quick-icon">◷</div><div class="quick-label">Uptime</div><div class="quick-value">{uptime_text(st.session_state.session_started)}</div><div class="quick-sub">SESSION</div></div><div class="quick-card"><div class="quick-icon">▤</div><div class="quick-label">Data Points</div><div class="quick-value">{points:,}</div><div class="quick-sub">CAPTURED</div></div><div class="quick-card"><div class="quick-icon">⌾</div><div class="quick-label">Channels</div><div class="quick-value">4</div><div class="quick-sub">SENSORS</div></div><div class="quick-card"><div class="quick-icon">♧</div><div class="quick-label">Efficiency</div><div class="quick-value">{efficiency}%</div><div class="quick-sub">{'OPTIMAL' if efficiency >= 85 else 'REVIEW'}</div></div></div></div>'''
            st.markdown(compact_html(quick_html), unsafe_allow_html=True)

    with trends_tab:
        st.markdown('<div class="section-caption"><div class="section-title">Interactive Trend Explorer</div><div class="section-sub">Power BI-style telemetry analysis</div></div>', unsafe_allow_html=True)
        selector, chart = st.columns([1, 3], gap="small")
        with selector:
            metric_choice = st.selectbox("Metric", ["Temperature (°C)", "Humidity (%)", "Soil Moisture (%)", "Tank Level (%)", "Ultrasonic Distance (cm)", "Lighting Request (%)", "Fan 1 PWM (%)", "Fan 2 PWM (%)", "Grow LED PWM (%)"], key="metric_choice")
            max_points = max(20, min(240, len(df)))
            visible = st.slider("Visible samples", 20, 240, min(90, max_points), 10)
            selected = df.tail(visible)
            if not selected.empty:
                latest = selected[metric_choice].iloc[-1]
                avg = selected[metric_choice].mean()
                st.markdown(f'<div class="control-card"><div class="control-name">LATEST READING</div><div class="control-state state-on">{latest:.1f}</div><div class="control-rule">Average · {avg:.1f}</div></div>', unsafe_allow_html=True)
        with chart:
            st.plotly_chart(line_chart(selected, [metric_choice], f"{metric_choice} · Rolling Trend", metric_choice), use_container_width=True, config={"displayModeBar":True, "scrollZoom":True})

        c1, c2 = st.columns(2, gap="small")
        with c1:
            st.plotly_chart(line_chart(df, ["Temperature (°C)", "Humidity (%)", "Soil Moisture (%)"], "Climate Interaction", "Reading"), use_container_width=True, config={"displayModeBar":False})
        with c2:
            st.plotly_chart(line_chart(df, ["Tank Level (%)"], "Ultrasonic Water Tank Level", "Tank fill (%)"), use_container_width=True, config={"displayModeBar":False})
        st.plotly_chart(pwm_trend(df), use_container_width=True, config={"displayModeBar":False})

    with control_tab:
        st.markdown('<div class="section-caption"><div class="section-title">Fuzzy Logic Output Control</div><div class="section-sub">Independent 0–100% PWM duty requests for two fans and the grow LED · pump stays relay ON/OFF</div></div>', unsafe_allow_html=True)
        o1, o2, o3, o4 = st.columns(4, gap="small")
        o1.markdown(output_card("💧", "Water Pump", "P-101", outputs["pump"], "Soil < 40% AND tank > 15%", is_pump=True), unsafe_allow_html=True)
        o2.markdown(output_card("✣", "Fan 1 · Temperature", "FAN-101", outputs["fan1_pct"], "Fuzzy: temperature + relative humidity"), unsafe_allow_html=True)
        o3.markdown(output_card("✣", "Fan 2 · Exhaust", "FAN-102", outputs["fan2_pct"], "Fuzzy: temperature + relative humidity"), unsafe_allow_html=True)
        o4.markdown(output_card("☀", "Grow LED Brightness", "LED-101", outputs["led_pct"], "Fuzzy: schedule request + temperature"), unsafe_allow_html=True)

        if r["tank_level"] <= TANK["critical_level_pct"]:
            st.error(f"Pump inhibited: ultrasonic tank level is {r['tank_level']:.1f}% (≤ {TANK['critical_level_pct']:.0f}%). Refill the tank in the sidebar to demonstrate recovery.")
        st.caption("Fan/LED percentages are simulated PWM duty-cycle COMMANDS, not a true analog voltage or verified physical speed/brightness. The real ESP32 requires suitable motor and LED drivers. Configure a minimum starting duty for fans if needed.")
        st.plotly_chart(pwm_trend(df), use_container_width=True, config={"displayModeBar":False})
        st.markdown("#### Fuzzy control logic · zero-order Sugeno")
        logic_df = pd.DataFrame([
            ["SM-101 + LT-201", "Soil + tank", "Threshold + dry-run protection", "P-101 ON/OFF", "Pump inhibited ≤ 15% tank"],
            ["TT-101 + HT-101", "Temperature + humidity", "3 × 3 fuzzy rule table", "FAN-101 PWM 0–100%", "Temperature-dominant ventilation"],
            ["TT-101 + HT-101", "Temperature + humidity", "3 × 3 fuzzy rule table", "FAN-102 PWM 0–100%", "Humidity-responsive exhaust"],
            ["DEMO SCHEDULE + TT-101", "Lighting request + temperature", "4 × 3 fuzzy rule table", "LED-101 PWM 0–100%", "High temperature reduces brightness"],
        ], columns=["Input Tag(s)", "Input Parameters", "Control Method", "Output", "Purpose"])
        st.dataframe(logic_df, use_container_width=True, hide_index=True)
        with st.expander("View fuzzy membership functions and example rules"):
            st.markdown("""
**Fan inputs:** temperature (cool / warm / hot) and relative humidity (dry / normal / humid).

**Examples:** hot + humid → Fan 1 = 100%, Fan 2 = 100%; warm + normal → both roughly 35–40%; cool + dry → fans stop.

**LED inputs:** scheduled lighting demand (off / low / medium / high) and temperature (cool / warm / hot).

**Examples:** high demand + cool → LED up to 100%; high demand + hot → dim to ~55%; zero demand → LED OFF.

**Inference:** multiply the input membership strengths for each rule, then calculate a weighted average of the 0–100% singleton outputs (zero-order Sugeno).

The precise values are **illustrative rules** for simulation. They require tuning against your crop, fan speed characteristics and full-spectrum LED driver.
            """)

    with analytics_tab:
        st.markdown('<div class="section-caption"><div class="section-title">Greenhouse Intelligence</div><div class="section-sub">Health, environmental balance and current rule evaluation</div></div>', unsafe_allow_html=True)
        a1, a2 = st.columns(2, gap="small")
        with a1:
            st.plotly_chart(health_gauge(health), use_container_width=True, config={"displayModeBar":False})
        with a2:
            st.plotly_chart(environmental_radar(r), use_container_width=True, config={"displayModeBar":False})

        eval_rows = []
        for key in ["temperature", "humidity", "soil", "tank_level"]:
            status, _ = sensor_status(key, r[key])
            meta = SENSOR_META[key]
            decimals = 1
            extra = f" (distance {r['tank_distance_cm']:.1f} cm)" if key == "tank_level" else ""
            eval_rows.append({"Sensor":meta["tag"], "Parameter":meta["name"], "Reading":f"{r[key]:.{decimals}f} {meta['unit']}{extra}", "Target":meta["target"], "State":status})
        st.dataframe(pd.DataFrame(eval_rows), use_container_width=True, hide_index=True)

    with log_tab:
        st.markdown('<div class="section-caption"><div class="section-title">Telemetry Data Log</div><div class="section-sub">Latest edge records</div></div>', unsafe_allow_html=True)
        display_df = df.tail(50).sort_values("time", ascending=False).copy()
        if not display_df.empty:
            display_df["time"] = display_df["time"].dt.strftime("%H:%M:%S")
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download telemetry CSV", data=csv, file_name=f"greenhouse_telemetry_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")

    st.markdown(f'<div class="footer-note"><span>Smart Greenhouse FYP · Raspberry Pi 5 + 3 ESP32 · STREAMLIT SIMULATOR</span><span>● DEMO TELEMETRY · {scenario.upper()}</span></div>', unsafe_allow_html=True)


live_dashboard()
