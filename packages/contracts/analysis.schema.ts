import { z } from "zod";
export const SummarySchema = z.object({
  total_kwh: z.number(),
  days: z.number(),
  avg_daily_kwh: z.number(),
  peak_kw: z.number(),
  peak_time_local: z.string(),
  baseload_kwh_per_day: z.number(),
  cooling_kwh: z.number(),
  heating_kwh: z.number(),
  top4_share_pct: z.number(),
  top4_start_mode_weekday: z.string(),
  top4_start_mode_weekend: z.string(),
  evening_share_pct: z.number(),
});
export const DeviceSchema = z.object({
  cooling_kwh: z.number(),
  oven_kwh: z.number(),
  dryer_kwh: z.number(),
  baseload_total_kwh: z.number(),
  fridge_kwh_est: z.number(),
  tv_elec_kwh_est: z.number(),
  misc_kwh_est: z.number(),
  other_kwh: z.number(),
});
export const TimingSchema = z.object({
  top4_start_distribution: z.record(z.string(), z.number()),
  top10_demand: z.array(z.object({
    timestamp: z.string(),
    kW: z.number(),
    kWh: z.number(),
  })),
});
export const SeriesSchema = z.object({
  daily: z.array(z.object({ date: z.string(), kWh: z.number() })),
  monthly: z.array(z.object({ month: z.string(), kWh: z.number() })),
  hourly_profile: z.array(z.object({ hour: z.number(), kWh_per_hour: z.number() })),
});
export const CompositionTop4Schema = z.array(z.object({
  component: z.enum(["baseload","hvac","oven","dryer","other"]),
  kWh: z.number(),
  pct: z.number()
}));
export const RecommendationsSchema = z.object({
  cards: z.array(z.object({
    title: z.string(),
    impact: z.enum(["high","medium","low"]),
    why: z.string(),
    actions: z.array(z.string())
  })),
  narrative: z.string()
});
export const AnalyzeResponseSchema = z.object({
  summary: SummarySchema,
  devices: DeviceSchema,
  timing: TimingSchema,
  series: SeriesSchema,
  composition_top4_avg: CompositionTop4Schema,
  recommendations: RecommendationsSchema,
  notes: z.array(z.string())
});
export type AnalyzeResponse = z.infer<typeof AnalyzeResponseSchema>;