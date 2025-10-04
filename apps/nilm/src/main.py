import os, numpy as np
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict

class PredictIn(BaseModel):
    kw: List[float]
    hours: List[int]
    months: List[int]
    sample_rate_min: int = 15

class PredictOut(BaseModel):
    per_device_kwh: Dict[str, float]
    per_device_kw_ts: Dict[str, List[float]]

app = FastAPI(title="Dummy NILM", version="1.0")

# === DROP-IN: REAL ONNX MODEL LOADING ==============================
# import onnxruntime as ort
# ORT_SESS = ort.InferenceSession("/models/nilm.onnx", providers=["CPUExecutionProvider"])
# def infer_real_model(kw): ...
# ===================================================================

@app.post("/predict", response_model=PredictOut)
def predict(inp: PredictIn):
    kw = np.array(inp.kw, dtype=float)
    hours = np.array(inp.hours, dtype=int)
    months = np.array(inp.months, dtype=int)
    dt_h = inp.sample_rate_min / 60.0

    night = (hours >= 2) & (hours <= 5) & (kw > 0)
    baseline_kw = float(np.percentile(kw[night], 40)) if night.any() else 0.5
    base_kw = np.full_like(kw, baseline_kw)

    win = 4
    pad = np.pad(kw, (win, win), mode="edge")
    ma = (np.cumsum(pad)[2*win:] - np.cumsum(pad)[:-2*win]) / (2*win)
    hvac_kw = np.clip(ma - baseline_kw, 0, None)
    summer = np.isin(months, [5,6,7,8,9]).astype(float)
    hour_weight = np.clip(1.2 - np.abs((hours - 14)/10), 0.2, 1.2)
    hvac_kw *= (0.5 + 0.5*summer) * hour_weight

    dkw = np.diff(np.r_[kw[:1], kw])
    high = kw >= 4.0
    oven_like = high & (dkw > 1.0) & np.isin(hours, [11,12,13,17,18,19])
    dryer = np.zeros_like(kw, dtype=bool); i = 0
    while i < len(kw):
        if high[i]:
            j = i
            while j+1 < len(kw) and high[j+1]: j += 1
            dur_min = (j - i + 1) * inp.sample_rate_min
            if 30 <= dur_min <= 90 and not oven_like[i:j+1].any():
                dryer[i:j+1] = True
            i = j + 1
        else:
            i += 1

    oven_kw = np.where(oven_like, np.maximum(kw - baseline_kw, 0), 0.0)
    dryer_kw = np.where(dryer, np.maximum(kw - baseline_kw, 0), 0.0)
    fridge_kw = base_kw * 0.35
    tv_kw = base_kw * 0.25
    misc_kw = np.clip(base_kw - fridge_kw - tv_kw, 0, None)
    allocated = hvac_kw + oven_kw + dryer_kw + fridge_kw + tv_kw + misc_kw
    other_kw = np.clip(kw - allocated, 0, None)
    devices = {"hvac": hvac_kw, "oven": oven_kw, "dryer": dryer_kw, "fridge": fridge_kw, "tv_elec": tv_kw, "misc": misc_kw, "other": other_kw}
    per_device_kwh = {k: float(np.sum(v*dt_h)) for k, v in devices.items()}
    per_device_kw_ts = {k: v.tolist() for k, v in devices.items()}
    return {"per_device_kwh": per_device_kwh, "per_device_kw_ts": per_device_kw_ts}