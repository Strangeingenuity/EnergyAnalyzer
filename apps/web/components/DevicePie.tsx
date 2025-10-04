"use client";
import { Pie, PieChart, Tooltip, Legend } from "recharts";
import React from "react";
import type { AnalyzeResponse } from "../lib/types";
export default function DevicePie({ data }: { data: AnalyzeResponse }) {
  const d = data.devices;
  const items = [
    { name: "HVAC cooling", value: d.cooling_kwh },
    { name: "Oven", value: d.oven_kwh },
    { name: "Dryer", value: d.dryer_kwh },
    { name: "Fridge (est)", value: d.fridge_kwh_est },
    { name: "TVs & electronics (est)", value: d.tv_elec_kwh_est },
    { name: "Always-on misc (est)", value: d.misc_kwh_est },
    { name: "Other", value: d.other_kwh },
  ];
  return (
    <div className="card">
      <div className="font-semibold mb-2">Where Your Electricity Goes</div>
      <PieChart width={420} height={300}>
        <Pie dataKey="value" nameKey="name" data={items} outerRadius={120} />
        <Tooltip /><Legend />
      </PieChart>
      <p className="mt-3 text-sm text-slate-600">What to do: schedule smart-plugs to cut night baseload; cook earlier; avoid overlapping heavy loads.</p>
    </div>
  );
}