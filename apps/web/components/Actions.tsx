"use client";
import React from "react";
import type { AnalyzeResponse } from "../lib/types";

type RecommendationCard = {
  title: string;
  impact: string;
  why: string;
  actions: string[];
};

export default function Actions({ data }: { data: AnalyzeResponse }) {
  // Safely handle missing or empty cards
  const cards: RecommendationCard[] = data.recommendations?.cards ?? [];

  return (
    <div className="grid md:grid-cols-2 gap-4">
      {cards.map((c: RecommendationCard, i: number) => (
        <div key={i} className="card">
          <div className="flex items-center justify-between mb-2">
            <div className="font-semibold">{c.title}</div>
            <span className="badge">{c.impact} impact</span>
          </div>
          <p className="text-sm text-slate-600 mb-2">{c.why}</p>
          <ul className="list-disc ml-5 text-sm">
            {c.actions.map((a: string, j: number) => (
              <li key={j}>{a}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
