"use client";
import React, { useState } from "react";
import { AnalyzeResponseZ, type AnalyzeResponse } from "../lib/types";
export default function Upload({ onResult }: { onResult: (d: AnalyzeResponse)=>void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string|null>(null);
  async function handleFile(file: File) {
    setBusy(true); setError(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("has_gas_heat", "true");
      const url = process.env.NEXT_PUBLIC_AI_URL || "http://localhost:8000/v1/energy/analyze";
      const res = await fetch(url, { method: "POST", body: fd });
      const json = await res.json();
      const data = AnalyzeResponseZ.parse(json);
      onResult(data);
    } catch(e:any) { setError(e.message || "Upload failed"); }
    finally { setBusy(false); }
  }
  return (
    <div className="card">
      <label className="block text-sm font-medium mb-2">Upload Smart Meter Texas CSV</label>
      <input type="file" accept=".csv" onChange={(e)=>{ const f=e.target.files?.[0]; if(f) handleFile(f); }} />
      {busy && <p className="mt-3 text-sm text-slate-500">Analyzing…</p>}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  );
}