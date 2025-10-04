import io
import os
import numpy as np
import pandas as pd
import requests
from fastapi import FastAPI, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# --- Constants ---
TZ = "America/Chicago"
SUMMER = [5, 6, 7, 8, 9]
SHOULDER = [3, 4, 10, 11]
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"
NILM_ENDPOINT = os.getenv("NILM_ENDPOINT", "")
COACH_ENDPOINT = os.getenv("COACH_ENDPOINT", "")

# --- App setup ---
app = FastAPI(title="Energy-AI API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- Core logic ---
def parse_csv(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(file_bytes))
    ts = pd.to_datetime(
        df["USAGE_DATE"].astype(str) + " " + df["USAGE_START_TIME"].astype(str),
        errors="coerce"
    )
    out = pd.DataFrame({
        "timestamp": ts,
        "kWh": pd.to_numeric(df["USAGE_KWH"], errors="coerce")
    }).dropna()
    out["timestamp"] = out["timestamp"].dt.tz_localize(TZ, nonexistent="shift_forward", ambiguous="NaT")
    out = out.dropna().sort_values("timestamp")
    out["kW"] = out["kWh"] / 0.25
    out["date"] = out["timestamp"].dt.date
    out["hour"] = out["timestamp"].dt.hour
    out["dow"] = out["timestamp"].dt.dayofweek
    out["month"] = out["timestamp"].dt.month
    return out


def baseload_kw(df: pd.DataFrame) -> float:
    overnight = df[(df["hour"] >= 2) & (df["hour"] <= 5) & (df["kW"] > 0)]["kW"]
    if len(overnight):
        return float(np.percentile(overnight, 40))
    positives = df[df["kW"] > 0]["kW"]
    return float(np.percentile(positives, 10)) if len(positives) else 0.5


def top4_metrics(df: pd.DataFrame):
    kwh = df.set_index("timestamp")["kWh"]
    daily = df.groupby("date")["kWh"].sum()
    rolling4 = kwh.rolling("4h").sum()  # lowercase 'h'
    top4_by_date = rolling4.groupby(rolling4.index.date).max()
    share = float((top4_by_date / daily).dropna().mean() * 100)

    starts = {}
    wk, we = [], []
    for d in daily.index:
        day = kwh.loc[str(d)]
        if day.empty:
            continue
        idx = day.rolling("4h").sum().idxmax()
        if pd.isna(idx):
            continue
        start = (idx - pd.Timedelta(hours=4)).tz_convert(TZ)
        h = start.hour
        key = f"{h:02d}"
        starts[key] = starts.get(key, 0) + 1
        (wk if start.weekday() < 5 else we).append(h)

    def mode_or(defh, arr):
        return f"{(pd.Series(arr).mode().iloc[0] if len(arr) else defh):02d}:00"

    return {
        "share": round(share, 1),
        "starts": starts,
        "wk_mode": mode_or(9, wk),
        "we_mode": mode_or(10, we)
    }


def series_tables(df: pd.DataFrame):
    daily = df.groupby("date")["kWh"].sum().reset_index()
    monthly = df.set_index("timestamp")["kWh"].resample("MS").sum().reset_index()
    monthly["month"] = monthly["timestamp"].dt.strftime("%Y-%m")
    hourly = (df.groupby("hour")["kWh"].mean() * 4).reset_index().rename(columns={"kWh": "kWh_per_hour"})
    return (
        daily.to_dict(orient="records"),
        monthly[["month", "kWh"]].to_dict(orient="records"),
        hourly.to_dict(orient="records")
    )


def detect_oven_dryer(df: pd.DataFrame):
    df = df.copy()
    cand = df[df["kW"] >= 4.0].sort_values("timestamp")
    dryer_idx = set()
    start = end = None
    for row in cand.itertuples():
        ts = row.timestamp
        if start is None:
            start = end = ts
        elif (ts - end).total_seconds() <= 16 * 60:
            end = ts
        else:
            dur = (end - start).total_seconds() / 60
            if 30 <= dur <= 90:
                dryer_idx.update(df[(df["timestamp"] >= start) & (df["timestamp"] <= end)].index)
            start = end = ts
    if start is not None:
        dur = (end - start).total_seconds() / 60
        if 30 <= dur <= 90:
            dryer_idx.update(df[(df["timestamp"] >= start) & (df["timestamp"] <= end)].index)
    df["is_dryer"] = df.index.isin(dryer_idx)
    df["prev_kW"] = df["kW"].shift(1).fillna(df["kW"])
    df["delta_up"] = df["kW"] - df["prev_kW"]
    df["is_oven"] = (df["kW"] >= 4.0) & (df["delta_up"] > 1.0) & (~df["is_dryer"])
    return df


def cooling_kwh(df: pd.DataFrame, baseload_day_kwh: float) -> float:
    summer = df[df["month"].isin(SUMMER)].set_index("timestamp")["kWh"].resample("D").sum()
    shoulder = df[df["month"].isin(SHOULDER)].set_index("timestamp")["kWh"].resample("D").sum()
    if not len(summer):
        return 0.0
    summer_mean = float(summer.mean())
    shoulder_mean = float(shoulder.mean() if len(shoulder) else 0)
    per_day = max(0.0, summer_mean - max(baseload_day_kwh, shoulder_mean))
    return float(per_day * len(summer))


def top10_intervals(df: pd.DataFrame):
    top10 = df.nlargest(10, "kW")[["timestamp", "kW", "kWh"]].copy()
    top10["timestamp"] = top10["timestamp"].dt.strftime("%Y-%m-%d %H:%M %Z")
    return top10.to_dict(orient="records")


def call_nilm(kw, hours, months):
    if not NILM_ENDPOINT:
        return None
    try:
        r = requests.post(
            NILM_ENDPOINT,
            json={"kw": kw.tolist(), "hours": hours.tolist(), "months": months.tolist(), "sample_rate_min": 15},
            timeout=20
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def call_coach(payload: dict):
    if not COACH_ENDPOINT:
        return None
    try:
        r = requests.post(COACH_ENDPOINT, json=payload, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# --- Main Endpoint ---
@app.post("/v1/energy/analyze")
async def analyze(file: UploadFile = File(...), has_gas_heat: bool = Form(True), timezone: str = Form(TZ)):
    df = parse_csv(await file.read())
    total_kwh = float(df["kWh"].sum())
    days = int(df.groupby("date")["kWh"].sum().shape[0])
    peak_row = df.loc[df["kW"].idxmax()]
    peak_kw = float(peak_row["kW"])
    peak_time = peak_row["timestamp"].strftime("%Y-%m-%d %H:%M %Z")

    baseline = baseload_kw(df)
    baseload_day_kwh = baseline * 24
    annual_baseload = baseload_day_kwh * days

    nilm = call_nilm(df["kW"].to_numpy(), df["hour"].to_numpy(), df["month"].to_numpy())
    if nilm and "per_device_kwh" in nilm:
        pd_kwh = nilm["per_device_kwh"]
        oven_kwh = float(pd_kwh.get("oven", 0.0))
        dryer_kwh = float(pd_kwh.get("dryer", 0.0))
        fridge = float(pd_kwh.get("fridge", annual_baseload * 0.35))
        tv_elec = float(pd_kwh.get("tv_elec", annual_baseload * 0.25))
        misc = float(pd_kwh.get("misc", max(0.0, annual_baseload - fridge - tv_elec)))
    else:
        df2 = detect_oven_dryer(df)
        oven_kwh = float(df2[df2["is_oven"]]["kWh"].sum())
        dryer_kwh = float(df2[df2["is_dryer"]]["kWh"].sum())
        fridge = annual_baseload * 0.35
        tv_elec = annual_baseload * 0.25
        misc = max(0.0, annual_baseload - fridge - tv_elec)

    cool_kwh = cooling_kwh(df, baseload_day_kwh)
    captured = cool_kwh + annual_baseload + oven_kwh + dryer_kwh
    other = max(0.0, total_kwh - captured)

    tm = top4_metrics(df)
    kwh = df.set_index("timestamp")["kWh"]
    daily = df.groupby("date")["kWh"].sum()
    evening = kwh[(kwh.index.hour >= 19) & (kwh.index.hour < 23)].resample("D").sum()
    evening_share = float((evening.groupby(evening.index.date).sum() / daily).dropna().mean() * 100)

    daily_series, monthly_series, hourly_profile = series_tables(df)

    rows = []
    df2 = detect_oven_dryer(df)
    for d, grp in df2.groupby("date"):
        s = grp.set_index("timestamp")["kWh"]
        idx = s.rolling("4h").sum().idxmax()
        if pd.isna(idx):
            continue
        win = df2[(df2["timestamp"] > idx - pd.Timedelta(hours=4)) & (df2["timestamp"] <= idx)]
        total = float(win["kWh"].sum())
        base = baseline * 4
        oven = float(win[win["is_oven"]]["kWh"].sum())
        dryer = float(win[win["is_dryer"]]["kWh"].sum())
        mask = (~win["is_oven"]) & (~win["is_dryer"]) & (win["month"].isin(SUMMER))
        hvac = float(np.maximum(0, win.loc[mask, "kW"].values - baseline).sum() * 0.25)
        other_c = max(0.0, total - base - oven - dryer - hvac)
        rows.append([base, hvac, oven, dryer, other_c, total])

    avg = np.array(rows).mean(axis=0) if len(rows) else np.zeros(6)
    comp = [
        {"component": "hvac", "kWh": round(float(avg[1]), 2),
         "pct": round(float(avg[1] / avg[5] * 100), 1) if avg[5] > 0 else 0},
        {"component": "oven", "kWh": round(float(avg[2]), 2),
         "pct": round(float(avg[2] / avg[5] * 100), 1) if avg[5] > 0 else 0},
        {"component": "dryer", "kWh": round(float(avg[3]), 2),
         "pct": round(float(avg[3] / avg[5] * 100), 1) if avg[5] > 0 else 0},
        {"component": "baseload", "kWh": round(float(avg[0]), 2),
         "pct": round(float(avg[0] / avg[5] * 100), 1) if avg[5] > 0 else 0},
        {"component": "other", "kWh": round(float(avg[4]), 2),
         "pct": round(float(avg[4] / avg[5] * 100), 1) if avg[5] > 0 else 0},
    ]

    # Coach recommendations
    recs = call_coach({
        "summary": {
            "top4_share_pct": tm["share"],
            "evening_share_pct": evening_share,
            "baseload_kwh_per_day": baseload_day_kwh
        },
        "devices": {
            "baseload_total_kwh": annual_baseload,
            "cooling_kwh": cool_kwh
        },
        "preferences": {"has_gas_heat": str(has_gas_heat).lower(), "locale": "en-US"}
    }) or {
        "cards": [
            {"title": "Set thermostat to pre-cool 3–6 pm, then +2°F from 6–10 pm",
             "impact": "high",
             "why": "Midday/evening concentration with cooling.",
             "actions": ["Upstairs cooler overnight", "Replace filters monthly", "Seal ducts & shade windows"]},
            {"title": "Cut baseload ~20% with smart-plug schedules",
             "impact": "high",
             "why": "Baseload is significant; TVs/office/gaming standby.",
             "actions": ["Schedule overnight OFF", "Aggressive sleep on TVs/monitors", "Fridge at 37–40°F"]},
        ],
        "narrative": "Your biggest 4-hour block is around midday and accounts for ~30% of daily use."
    }

    return {
        "summary": {
            "total_kwh": round(total_kwh, 1),
            "days": days,
            "avg_daily_kwh": round(total_kwh / days, 1),
            "peak_kw": round(peak_kw, 2),
            "peak_time_local": peak_time,
            "baseload_kwh_per_day": round(baseload_day_kwh, 1),
            "cooling_kwh": round(cool_kwh, 0),
            "heating_kwh": 0,
            "top4_share_pct": tm["share"],
            "top4_start_mode_weekday": tm["wk_mode"],
            "top4_start_mode_weekend": tm["we_mode"],
            "evening_share_pct": round(evening_share, 1),
        },
        "devices": {
            "cooling_kwh": round(cool_kwh, 0),
            "oven_kwh": round(oven_kwh, 1),
            "dryer_kwh": round(dryer_kwh, 1),
            "baseload_total_kwh": round(annual_baseload, 0),
            "fridge_kwh_est": round(fridge, 0),
            "tv_elec_kwh_est": round(tv_elec, 0),
            "misc_kwh_est": round(misc, 0),
            "other_kwh": round(other, 0),
        },
        "timing": {
            "top4_start_distribution": tm["starts"],
            "top10_demand": top10_intervals(df),
        },
        "series": {
            "daily": daily_series,
            "monthly": monthly_series,
            "hourly_profile": hourly_profile,
        },
        "composition_top4_avg": comp,
        "recommendations": recs,
        "notes": [
            "Heating set to 0 if has_gas_heat=true.",
            "Device estimates are approximate from 15-min data.",
        ],
    }
