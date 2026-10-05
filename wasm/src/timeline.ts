import { query } from "trailbase-wasm/db";
import {
  HttpHandler,
  type HttpRequest,
  HttpResponse,
} from "trailbase-wasm/http";
import { num, type Params, str } from "./values";

/// Timeline API over the unified `events` table.
///
/// GET /timeline            events overlapping a year range
///   from, to      year bounds (default 1900..current year); negative = BCE
///   category      comma-separated categories ("film,baseball")
///   source        comma-separated source slugs ("imdb,lahman")
///   kind          comma-separated event kinds ("life,release")
///   span          "1" for spans only, "0" for instants only
///   q             entity name substring (3+ characters, trigram index)
///   anchor        entity id; every event gets its offset from that entity's
///                 first span (years, and days when both are day-precision)
///   limit/offset  paging (limit max MAX_LIMIT)
///   Point-in-time ("who was alive in 1972") is from=1972&to=1972&span=1.
///
/// GET /timeline/density    event counts per year bucket and category
///   from, to, category, source as above; bucket = years per bucket (1..1000)
///
/// Uses the R*Tree `events_span` for the overlap test, window functions for
/// per-entity ordering and the total count, and the generated Julian-day
/// columns for day offsets.

const DEFAULT_LIMIT = 500;
const MAX_LIMIT = 5000;
const MAX_LIST = 50;
const MIN_YEAR = -100000;
const MAX_YEAR = 9999;

export interface TimelineQuery {
  from: number;
  to: number;
  categories: string[];
  sources: string[];
  kinds: string[];
  span: boolean | null;
  match: string | null;
  limit: number;
  offset: number;
}

export interface TimelineEvent {
  id: number;
  kind: string;
  label: string;
  startDate: string;
  endDate: string | null;
  precision: string;
  startYear: number;
  endYear: number | null;
  span: boolean;
  category: string;
  detail: Record<string, unknown> | null;
  startJulian: number | null;
  endJulian: number | null;
  entity: {
    id: number;
    kind: string;
    name: string;
    wikidataId: string | null;
    url: string | null;
    source: string;
  };
  /// 1-based position of this event among the entity's events.
  seq: number;
  offsetYears?: number;
  offsetDays?: number;
}

export interface Anchor {
  entityId: number;
  name: string;
  startYear: number;
  startJulian: number | null;
}

/// Parse a comma-separated list: trimmed, de-duplicated, capped.
export function parseList(value: string | null): string[] {
  if (!value) {
    return [];
  }
  const out: string[] = [];
  for (const part of value.split(",")) {
    const item = part.trim();
    if (item && !out.includes(item)) {
      out.push(item);
    }
    if (out.length >= MAX_LIST) {
      break;
    }
  }
  return out;
}

/// Parse a year, allowing negatives, clamped to a sane range.
export function parseYear(value: string | null, fallback: number): number {
  const n = Number.parseInt(value ?? "", 10);
  if (!Number.isFinite(n)) {
    return fallback;
  }
  return Math.min(Math.max(n, MIN_YEAR), MAX_YEAR);
}

export function parseBounded(
  value: string | null,
  fallback: number,
  min: number,
  max: number,
): number {
  const n = Number.parseInt(value ?? "", 10);
  if (!Number.isFinite(n)) {
    return fallback;
  }
  return Math.min(Math.max(n, min), max);
}

/// Build a MATCH expression for the trigram-tokenized `entities_fts`.
/// Each term is quoted so FTS5 syntax in user input is inert; terms shorter
/// than three characters cannot match a trigram index and are dropped.
export function buildTrigramMatch(raw: string): string | null {
  const terms = raw
    .split(/\s+/)
    .map((t) => t.trim())
    .filter((t) => t.length >= 3)
    .map((t) => `"${t.replace(/"/g, '""')}"`);
  return terms.length > 0 ? terms.join(" ") : null;
}

function placeholders(n: number): string {
  return Array.from({ length: n }, () => "?").join(", ");
}

/// Compose the events query. Exported so the SQL shape can be unit-tested
/// without a database.
export function buildEventsQuery(q: TimelineQuery): {
  sql: string;
  params: unknown[];
} {
  const where: string[] = [
    "events_span.start_year <= ?",
    "events_span.end_year >= ?",
  ];
  const params: unknown[] = [q.to, q.from];

  if (q.categories.length > 0) {
    where.push(`events.category IN (${placeholders(q.categories.length)})`);
    params.push(...q.categories);
  }
  if (q.sources.length > 0) {
    where.push(`sources.slug IN (${placeholders(q.sources.length)})`);
    params.push(...q.sources);
  }
  if (q.kinds.length > 0) {
    where.push(`events.kind IN (${placeholders(q.kinds.length)})`);
    params.push(...q.kinds);
  }
  if (q.span !== null) {
    where.push("events.span = ?");
    params.push(q.span ? 1 : 0);
  }
  if (q.match !== null) {
    where.push(
      "events.entity_id IN (SELECT rowid FROM entities_fts WHERE entities_fts MATCH ?)",
    );
    params.push(q.match);
  }
  params.push(q.limit, q.offset);

  const sql = `
    SELECT events.id, events.kind, events.label, events.start_date, events.end_date,
           events.precision, events.start_year, events.end_year, events.span,
           events.category, events.detail, events.start_julian, events.end_julian,
           entities.id, entities.kind, entities.name, entities.wikidata_id,
           entities.url, sources.slug,
           row_number() OVER (PARTITION BY events.entity_id
                              ORDER BY events.start_year, events.id) AS seq,
           count(*) OVER () AS total
      FROM events_span
      JOIN events ON events.id = events_span.id
      JOIN entities ON entities.id = events.entity_id
      JOIN sources ON sources.id = events.source_id
     WHERE ${where.join("\n       AND ")}
     ORDER BY events.start_year, events.id
     LIMIT ? OFFSET ?`;
  return { sql, params };
}

/// Year buckets that floor correctly for negative years without math
/// functions: start_year - ((start_year mod b + b) mod b).
export function buildDensityQuery(
  from: number,
  to: number,
  bucket: number,
  categories: string[],
  sources: string[],
): { sql: string; params: unknown[] } {
  const where: string[] = ["events.start_year BETWEEN ? AND ?"];
  const params: unknown[] = [bucket, bucket, bucket, from, to];
  if (categories.length > 0) {
    where.push(`events.category IN (${placeholders(categories.length)})`);
    params.push(...categories);
  }
  if (sources.length > 0) {
    where.push(`sources.slug IN (${placeholders(sources.length)})`);
    params.push(...sources);
  }
  const sql = `
    SELECT events.start_year - (((events.start_year % ?) + ?) % ?) AS bucket,
           events.category, count(*)
      FROM events
      JOIN sources ON sources.id = events.source_id
     WHERE ${where.join(" AND ")}
     GROUP BY 1, 2
     ORDER BY 1, 2`;
  return { sql, params };
}

function parseDetail(v: unknown): Record<string, unknown> | null {
  if (typeof v !== "string") {
    return null;
  }
  try {
    const parsed: unknown = JSON.parse(v);
    return parsed !== null && typeof parsed === "object"
      ? (parsed as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

function rowToEvent(row: unknown[]): TimelineEvent {
  return {
    id: num(row[0]) ?? 0,
    kind: str(row[1]) ?? "",
    label: str(row[2]) ?? "",
    startDate: str(row[3]) ?? "",
    endDate: str(row[4]),
    precision: str(row[5]) ?? "year",
    startYear: num(row[6]) ?? 0,
    endYear: num(row[7]),
    span: num(row[8]) === 1,
    category: str(row[9]) ?? "",
    detail: parseDetail(row[10]),
    startJulian: num(row[11]),
    endJulian: num(row[12]),
    entity: {
      id: num(row[13]) ?? 0,
      kind: str(row[14]) ?? "",
      name: str(row[15]) ?? "",
      wikidataId: str(row[16]),
      url: str(row[17]),
      source: str(row[18]) ?? "",
    },
    seq: num(row[19]) ?? 1,
  };
}

async function loadAnchor(entityId: number): Promise<Anchor | null> {
  // Prefer the entity's span (its life, career or run) over its instants.
  const rows = await query(
    `SELECT entities.name, events.start_year, events.start_julian
       FROM events
       JOIN entities ON entities.id = events.entity_id
      WHERE events.entity_id = ?
      ORDER BY events.span DESC, events.start_year, events.id
      LIMIT 1`,
    [entityId],
  );
  const row = rows[0];
  if (!row) {
    return null;
  }
  return {
    entityId,
    name: str(row[0]) ?? "",
    startYear: num(row[1]) ?? 0,
    startJulian: num(row[2]),
  };
}

/// Annotate events with their distance from the anchor.
export function applyAnchor(events: TimelineEvent[], anchor: Anchor): void {
  for (const e of events) {
    e.offsetYears = e.startYear - anchor.startYear;
    if (e.startJulian !== null && anchor.startJulian !== null) {
      e.offsetDays = Math.round(e.startJulian - anchor.startJulian);
    }
  }
}

export async function timeline(req: HttpRequest): Promise<object> {
  const currentYear = new Date().getUTCFullYear();
  const from = parseYear(req.getQueryParam("from"), 1900);
  const to = Math.max(from, parseYear(req.getQueryParam("to"), currentYear));
  const spanParam = req.getQueryParam("span");
  const q: TimelineQuery = {
    from,
    to,
    categories: parseList(req.getQueryParam("category")),
    sources: parseList(req.getQueryParam("source")),
    kinds: parseList(req.getQueryParam("kind")),
    span: spanParam === "1" ? true : spanParam === "0" ? false : null,
    match: buildTrigramMatch(req.getQueryParam("q") ?? ""),
    limit: parseBounded(
      req.getQueryParam("limit"),
      DEFAULT_LIMIT,
      1,
      MAX_LIMIT,
    ),
    offset: parseBounded(
      req.getQueryParam("offset"),
      0,
      0,
      Number.MAX_SAFE_INTEGER,
    ),
  };

  try {
    const { sql, params } = buildEventsQuery(q);
    const rows = await query(sql, params as Params);
    const events = rows.map(rowToEvent);
    const total = rows.length > 0 ? (num(rows[0]?.[20]) ?? 0) : 0;

    const anchorId = Number.parseInt(req.getQueryParam("anchor") ?? "", 10);
    const anchor = Number.isFinite(anchorId)
      ? await loadAnchor(anchorId)
      : null;
    if (anchor !== null) {
      applyAnchor(events, anchor);
    }

    return {
      from,
      to,
      total,
      limit: q.limit,
      offset: q.offset,
      anchor,
      events,
    };
  } catch (error) {
    console.error("[TIMELINE] query failed:", error);
    return { from, to, total: 0, events: [], error: "Timeline query failed" };
  }
}

export async function density(req: HttpRequest): Promise<object> {
  const currentYear = new Date().getUTCFullYear();
  const from = parseYear(req.getQueryParam("from"), 1900);
  const to = Math.max(from, parseYear(req.getQueryParam("to"), currentYear));
  const bucket = parseBounded(req.getQueryParam("bucket"), 10, 1, 1000);
  const categories = parseList(req.getQueryParam("category"));
  const sources = parseList(req.getQueryParam("source"));

  try {
    const { sql, params } = buildDensityQuery(
      from,
      to,
      bucket,
      categories,
      sources,
    );
    const rows = await query(sql, params as Params);
    return {
      from,
      to,
      bucket,
      buckets: rows.map((r) => ({
        year: num(r[0]) ?? 0,
        category: str(r[1]) ?? "",
        count: num(r[2]) ?? 0,
      })),
    };
  } catch (error) {
    console.error("[TIMELINE] density query failed:", error);
    return { from, to, bucket, buckets: [], error: "Density query failed" };
  }
}

export const timelineHandlers = [
  HttpHandler.get("/timeline", async (req) =>
    HttpResponse.json(await timeline(req)),
  ),
  HttpHandler.get("/timeline/density", async (req) =>
    HttpResponse.json(await density(req)),
  ),
];
