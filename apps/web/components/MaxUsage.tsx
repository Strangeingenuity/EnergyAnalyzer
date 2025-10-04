"use client";
import { Area, AreaChart, CartesianGrid, ReferenceArea, Tooltip, XAxis, YAxis } from "recharts";
import React from "react";
import type { AnalyzeResponse } from "../lib/types";
export default function MaxUsage({ data }: { data: AnalyzeResponse }) {
  const hourly = data.series.hourly_profile;
  const wkStart = parseInt(data.summary.top4_start_mode_weekday.split(":")[0],10);
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-2">
        <div className="font-semibold">Max Usage Timings</div>
        <div className="text-sm text-slate-500">Top-4h holds about {data.summary.top4_share_pct}% of a typical day.</div>
      </div>
      <AreaChart width={800} height={260} data={hourly}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="hour" />
        <YAxis />
        <Tooltip />
        <Area type="monotone" dataKey="kWh_per_hour" />
        <ReferenceArea x1={wkStart} x2={(wkStart+4)} />
      </AreaChart>
      <p className="mt-3 text-sm text-slate-600">
        Biggest block usually starts at <b>{data.summary.top4_start_mode_weekday}</b> on weekdays (<b>{data.summary.top4_start_mode_weekend}</b> weekends). 
        Evenings (7–11 pm) ≈ <b>{data.summary.evening_share_pct}%</b>.
      </p>
    </div>
  );
}