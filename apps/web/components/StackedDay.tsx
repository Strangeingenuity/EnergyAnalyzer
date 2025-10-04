"use client";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import React from "react";
import type { AnalyzeResponse } from "../lib/types";

// Define the shape of each hourly record
type HourlyProfile = {
  hour: number;
  kWh_per_hour: number;
};

export default function StackedDay({ data }: { data: AnalyzeResponse }) {
  const baseline = data.summary.baseload_kwh_per_day / 24;

  // Explicitly type 'h' to remove implicit-any error
  const rows = data.series.hourly_profile.map((h: HourlyProfile) => ({
    hour: h.hour,
    Baseload: baseline,
    HVAC: Math.max(0, h.kWh_per_hour - baseline) * 0.4,
    Cooking: Math.max(0, h.kWh_per_hour - baseline) * 0.2,
    Other: Math.max(0, h.kWh_per_hour - baseline) * 0.4,
  }));

  return (
    <div className="card">
      <div className="font-semibold mb-2">Over the Day (Stacked Estimate)</div>
      <BarChart width={800} height={260} data={rows}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="hour" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="Baseload" stackId="a" />
        <Bar dataKey="HVAC" stackId="a" />
        <Bar dataKey="Cooking" stackId="a" />
        <Bar dataKey="Other" stackId="a" />
      </BarChart>
    </div>
  );
}
