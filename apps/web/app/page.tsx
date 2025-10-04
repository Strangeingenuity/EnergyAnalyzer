"use client";

import "./../styles/globals.css";
import Upload from "../components/Upload";
import MaxUsage from "../components/MaxUsage";
import DevicePie from "../components/DevicePie";
import StackedDay from "../components/StackedDay";
import Actions from "../components/Actions";
import type { AnalyzeResponse } from "../lib/types";
import { useState } from "react";

export default function Page() {
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  return (
    <main className="max-w-6xl mx-auto p-6 space-y-6">
      <header className="flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Home Energy Snapshot</h1>
          <p className="text-slate-600">
            A clear, action-ready summary any household can use
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn" onClick={() => window.print()}>
            Export PDF
          </button>
        </div>
      </header>
      <Upload onResult={setData} />
      {data && (
        <section className="space-y-6">
          <div className="grid md:grid-cols-5 gap-4">
            <div className="kpi col-span-1">
              <div className="label">TOTAL (kWh)</div>
              <div className="val">
                {data.summary.total_kwh.toLocaleString()}
              </div>
            </div>
            <div className="kpi col-span-1">
              <div className="label">AVG / DAY</div>
              <div className="val">{data.summary.avg_daily_kwh}</div>
            </div>
            <div className="kpi col-span-1">
              <div className="label">PEAK (kW)</div>
              <div className="val">{data.summary.peak_kw}</div>
              <div className="text-xs text-slate-500">
                {data.summary.peak_time_local}
              </div>
            </div>
            <div className="kpi col-span-1">
              <div className="label">BASELOAD / DAY</div>
              <div className="val">{data.summary.baseload_kwh_per_day} kWh</div>
            </div>
            <div className="kpi col-span-1">
              <div className="label">DAYS OF DATA</div>
              <div className="val">{data.summary.days}</div>
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <MaxUsage data={data} />
            <DevicePie data={data} />
          </div>
          <StackedDay data={data} />
          <div className="card">
            <div className="font-semibold mb-2">Top Actions (30-Day Plan)</div>
            <Actions data={data} />
            <p className="mt-3 text-sm text-slate-500">
              Plan tip: You currently place ~{data.summary.top4_share_pct}% in
              your top-4 hours and ~{data.summary.evening_share_pct}% in 7–11
              pm.
            </p>
          </div>
        </section>
      )}
    </main>
  );
}
