/// Pure layout maths for the banded timeline: which data tier a zoom level
/// needs, which tiles cover a year range, axis ticks, and lane packing so
/// labels do not overlap. No DOM here, so Jest can cover it.

export interface OverviewTier {
  kind: "overview";
  /// event_lod bucket size in years.
  bucket: 1 | 10 | 100;
  /// Top events per bucket to show.
  per: number;
  /// Years covered by one request.
  tileYears: number;
}

export interface DetailTier {
  kind: "detail";
  tileYears: number;
  /// Events per tile and band; the API caps pages at 5000.
  limit: number;
}

export type Tier = OverviewTier | DetailTier;

/// Smallest and largest pixels-per-year the view allows. The upper bound
/// keeps a 3000-year world under the browsers' layout width limit.
export const MIN_PX_PER_YEAR = 0.25;
export const MAX_PX_PER_YEAR = 2000;

/// Pick the data tier for a zoom level: coarse LOD rows when a pixel is
/// years wide, the full event stream once a year is wide enough to read.
export function tierFor(pxPerYear: number): Tier {
  if (pxPerYear < 1.5) {
    return { kind: "overview", bucket: 100, per: 6, tileYears: 5000 };
  }
  if (pxPerYear < 12) {
    return { kind: "overview", bucket: 10, per: 8, tileYears: 500 };
  }
  if (pxPerYear < 100) {
    return { kind: "overview", bucket: 1, per: 12, tileYears: 50 };
  }
  return { kind: "detail", tileYears: 10, limit: 1000 };
}

/// Floor a year to a multiple of `size`, correct for negative years.
export function floorTo(year: number, size: number): number {
  return year - (((year % size) + size) % size);
}

/// Tile start years whose [start, start + tileYears) intersects the range.
export function tilesFor(
  from: number,
  to: number,
  tileYears: number,
): number[] {
  const out: number[] = [];
  for (let t = floorTo(from, tileYears); t <= to; t += tileYears) {
    out.push(t);
  }
  return out;
}

export interface Tick {
  year: number;
  major: boolean;
  label: string | null;
}

const STEPS = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000];

/// The year step between labelled ticks so labels sit at least `minPx`
/// apart.
export function majorStep(pxPerYear: number, minPx = 90): number {
  for (const s of STEPS) {
    if (s * pxPerYear >= minPx) {
      return s;
    }
  }
  return STEPS[STEPS.length - 1] ?? 5000;
}

/// Astronomical years: 0 and below are BCE. Year 0 is shown as 1 BCE.
export function formatYear(year: number): string {
  return year <= 0 ? `${1 - year} BCE` : String(year);
}

/// Axis ticks for a visible range at a zoom level: labelled major ticks and
/// unlabelled minor ticks between them.
export function ticksFor(from: number, to: number, pxPerYear: number): Tick[] {
  const major = majorStep(pxPerYear);
  const minor = major % 5 === 0 ? major / 5 : major / 2;
  const out: Tick[] = [];
  for (let y = floorTo(from, minor); y <= to; y += minor) {
    const isMajor = ((y % major) + major) % major === 0;
    out.push({
      year: y,
      major: isMajor,
      label: isMajor ? formatYear(y) : null,
    });
  }
  return out;
}

export interface Placed<T> {
  item: T;
  lane: number;
}

/// Greedy lane packing. Items are intervals in pixels, already sorted by
/// `x0`; each goes to the first lane that is free at its start, up to
/// `maxLanes`. Items that fit nowhere are returned in `hidden` so the band
/// can say how many it is not showing at this zoom.
export function packLanes<T>(
  items: { item: T; x0: number; x1: number }[],
  maxLanes: number,
  gap = 4,
): { placed: Placed<T>[]; hidden: number } {
  const laneEnds: number[] = [];
  const placed: Placed<T>[] = [];
  let hidden = 0;
  for (const it of items) {
    let lane = laneEnds.findIndex((end) => end + gap <= it.x0);
    if (lane === -1) {
      if (laneEnds.length >= maxLanes) {
        hidden += 1;
        continue;
      }
      lane = laneEnds.length;
      laneEnds.push(it.x1);
    } else {
      laneEnds[lane] = it.x1;
    }
    placed.push({ item: it.item, lane });
  }
  return { placed, hidden };
}

/// Rough label width so lanes can be packed before the text is measured.
export function labelWidth(text: string, charPx = 6.4, padding = 12): number {
  return Math.min(text.length, 48) * charPx + padding;
}

/// Fractional year for a date string so day-precision events spread out
/// inside their year at high zoom. Falls back to the integer year.
export function fractionalYear(date: string, year: number): number {
  const m = /^(-?\d+)-(\d\d)-(\d\d)$/.exec(date);
  if (!m) {
    return year;
  }
  const month = Number(m[2]);
  const day = Number(m[3]);
  if (month < 1 || month > 12 || day < 1) {
    return year;
  }
  return year + (month - 1) / 12 + (day - 1) / 365;
}

/// Density histogram bucket for a world span so the minimap has at most
/// `maxBars` bars.
export function densityBucket(years: number, maxBars = 400): number {
  for (const b of [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]) {
    if (years / b <= maxBars) {
      return b;
    }
  }
  return 1000;
}

/// Band colours, assigned in source order so a legend stays stable.
export const PALETTE = [
  "#bb86fc",
  "#03dac6",
  "#ffb74d",
  "#4fc3f7",
  "#f06292",
  "#aed581",
  "#ff8a65",
  "#90a4ae",
  "#fff176",
  "#ce93d8",
];

export function colorFor(index: number): string {
  return PALETTE[index % PALETTE.length] ?? PALETTE[0] ?? "#bb86fc";
}
