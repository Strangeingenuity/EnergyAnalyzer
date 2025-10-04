from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class SummaryIn(BaseModel):
    top4_share_pct: float
    evening_share_pct: float
    baseload_kwh_per_day: Optional[float] = None

class DevicesIn(BaseModel):
    cooling_kwh: Optional[float] = None
    baseload_total_kwh: Optional[float] = None

class CoachIn(BaseModel):
    summary: SummaryIn
    devices: DevicesIn
    preferences: Dict[str, str] = Field(default_factory=dict)

class Card(BaseModel):
    title: str
    impact: str
    why: str
    actions: List[str]

class CoachOut(BaseModel):
    cards: List[Card]
    narrative: str

app = FastAPI(title="EnergyCoach (Dummy LLM)", version="1.0")

@app.post("/coach", response_model=CoachOut)
def coach(inp: CoachIn):
    s = inp.summary
    cards: List[Card] = []
    if s.top4_share_pct >= 28 or s.evening_share_pct >= 18:
        cards.append(Card(
            title="Set thermostat to pre‑cool 3–6 pm, then +2°F from 6–10 pm",
            impact="high",
            why="Usage concentrates midday/evening; shifting HVAC reduces on‑peak cooling.",
            actions=["Keep upstairs cooler overnight; let downstairs float higher",
                     "Replace filters monthly; seal ducts & shade sun‑facing windows"]
        ))
    if (s.baseload_kwh_per_day or 0) >= 10:
        cards.append(Card(
            title="Cut baseload ~20% with smart‑plug schedules",
            impact="high",
            why="Always‑on devices (TV/office/gaming/routers) run all day.",
            actions=["Schedule power strips OFF overnight",
                     "Aggressive sleep on TVs/monitors",
                     "Set fridge to 37–40°F; clean coils"]
        ))
    cards.append(Card(
        title="Cook earlier; use convection/air‑fryer for small meals",
        impact="medium",
        why="Cooking overlaps with cooling and laundry to create short peaks.",
        actions=["Batch‑cook before 6 pm or after 8 pm",
                 "Run dishwasher & laundry after 9 pm"]
    ))
    if s.evening_share_pct >= 18:
        cards.append(Card(
            title="Compare fixed‑rate vs free‑nights plan",
            impact="medium",
            why="Shifting more load to nights can make TOU/free‑nights cheaper.",
            actions=["Review last 12 months usage shape",
                     "Nudge dishwasher/laundry to nights"]
        ))
    if not cards:
        cards.append(Card(
            title="Nice work — usage is balanced",
            impact="low",
            why="No strong load concentration detected.",
            actions=["Keep filters fresh; use smart thermostats",
                     "Review plan annually"]
        ))
    narrative = (f"Your biggest 4‑hour window holds ~{s.top4_share_pct:.1f}% of a day; "
                 f"evenings (7–11 pm) are ~{s.evening_share_pct:.1f}%. "
                 "Focus on pre‑cooling and moving flexible loads later at night.")
    return CoachOut(cards=cards[:4], narrative=narrative)