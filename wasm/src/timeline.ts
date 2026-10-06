import { query } from "trailbase-wasm/db";
import {
  HttpHandler,
  type HttpRequest,
  HttpResponse,
} from "trailbase-wasm/http";
import { num, type Params, str } from "./values";

/// Timeline API over the unified `events` table, built to be scanned.
///
/// GET /timeline            one page of a window, in start order
///   from, to      year bounds (default 1900..current year); negative = BCE
///   category      comma-separated categories ("film,baseball")
///   source        comma-separated source slugs ("imdb,lahman")
///   kind          comma-separated event kinds ("life,release")
///   span          "1" for spans only, "0" for instants only
///   q             entity name substring (3+ characters, trigram index)
///   participant   entity id; only events that entity owns or took part in
///   anchor        entity id; every event gets its offset from that entity's
///                 first span (years, and days when both are day-precision)
///   cursor        keyset cursor from the previous page's `next`
///   limit         page size (max MAX_LIMIT)
///   Returns `active` (spans that began before `from` and are still open
///   there; first page only), `events` (those starting inside the window,
///   ordered by start then id, walking an index and stopping at `limit`),
///   `next` (cursor, or null) and a capped `total`.
///
/// GET /timeline/overview   what matters in a window when it is too wide
///   from, to, category, source as above; bucket = 1, 10 or 100 years;
///   per = events per bucket and category (max 20). Served from the
///   precomputed `event_lod` table, so cost does not grow with the data.
///
/// GET /timeline/density        counts per year bucket from `event_density`
/// GET /timeline/participants   who took part in an event (`event=<id>`)
/// GET /timeline/links          the same entity across sources (`entity=<id>`)

const DEFAULT_LIMIT = 500;
const MAX_LIMIT = 5000;
const COUNT_CAP = 10_000;
const MAX_LIST = 50;
const MIN_YEAR = -100000;
const MAX_YEAR = 9999;
const LOD_SIZES = [1, 10, 100];
const LOD_MAX_PER = 20;

export interface Cursor {
  startYear: number;
  id: number;
}

export interface TimelineQuery {
  from: number;
  to: number;
  categories: string[];
  sources: string[];
  kinds: string[];
  span: boolean | null;
  match: string | null;
  participant: number | null;
  cursor: Cursor | null;
  limit: number;
}

export interface TimelineEvent {
  id: number;
  kind: string;
  label: string;
  startDate: string;
  endDate: string | null;
  precision: string;
  certainty: string;
  startYear: number;
  endYear: number | null;
  span: boolean;
  category: string;
  rank: number;
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
    /// The entity this one resolves to when another source has the same
    /// real-world entity; null when it is canonical itself.
    canonicalId: number | null;
  };
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

function parseId(value: string | null): number | null {
  const n = Number.parseInt(value ?? "", 10);
  return Number.isFinite(n) && n > 0 ? n : null;
}

/// Cursors are "startYear:id" of the last event of the previous page.
export function parseCursor(value: string | null): Cursor | null {
  if (!value) {
    return null;
  }
  const m = /^(-?\d+):(\d+)$/.exec(value.trim());
  if (!m) {
    return null;
  }
  return { startYear: Number(m[1]), id: Number(m[2]) };
}

export function formatCursor(e: { startYear: number; id: number }): string {
  return `${e.startYear}:${e.id}`;
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

/// Filter clauses shared by every events query (no time bounds).
function buildFilters(q: TimelineQuery): {
  where: string[];
  params: unknown[];
} {
  const where: string[] = [];
  const params: unknown[] = [];
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
    // The FROM clause (see driver()) joins events to the FTS hits; the MATCH
    // itself has to sit in WHERE.
    where.push("entities_fts MATCH ?");
    params.push(q.match);
  }
  if (q.participant !== null) {
    where.push(
      "(events.entity_id = ? OR events.id IN " +
        "(SELECT event_id FROM event_participants WHERE entity_id = ?))",
    );
    params.push(q.participant, q.participant);
  }
  return { where, params };
}

const EVENT_COLUMNS = `
           events.id, events.kind, events.label, events.start_date, events.end_date,
           events.precision, events.start_year, events.end_year, events.span,
           events.category, events.detail, events.start_julian, events.end_julian,
           entities.id, entities.kind, entities.name, entities.wikidata_id,
           entities.url, sources.slug, entity_links.canonical_id, events.certainty,
           events.rank`;

// CROSS JOIN pins the join order: the driving table (events, or a LOD
// table) stays the outer loop. Left to itself the planner starts from the
// seven-row sources table, which breaks the ordered index walk and sorts
// every event in the window (29 seconds on a wide window of 6M events).
const EVENT_JOINS = `
      CROSS JOIN entities ON entities.id = events.entity_id
      CROSS JOIN sources ON sources.id = events.source_id
      LEFT JOIN entity_links ON entity_links.entity_id = entities.id`;

/// The table that drives an events query. With a name filter the few
/// hundred FTS hits drive the join (events_by_entity does the rest) instead
/// of walking the whole window and checking each row against the hits.
function driver(q: TimelineQuery): string {
  return q.match === null
    ? "FROM events"
    : "FROM entities_fts CROSS JOIN events ON events.entity_id = entities_fts.rowid";
}

/// Bucket size for span_lod given a window width.
export function spanBucketSize(from: number, to: number): number {
  return to - from <= 100 ? 10 : 100;
}

function floorBucket(year: number, size: number): number {
  return year - (((year % size) + size) % size);
}

/// Events that START inside the window, in (start_year, id) order. With a
/// category filter this walks events_by_category; without, events_by_start.
/// Either way SQLite stops after `limit + 1` rows; the extra row tells us
/// whether there is a next page.
export function buildWindowQuery(q: TimelineQuery): {
  sql: string;
  params: unknown[];
} {
  const { where, params } = buildFilters(q);
  const bounds = ["events.start_year BETWEEN ? AND ?"];
  const boundParams: unknown[] = [q.from, q.to];
  if (q.cursor !== null) {
    bounds.push("(events.start_year, events.id) > (?, ?)");
    boundParams.push(q.cursor.startYear, q.cursor.id);
  }
  const sql = `
    SELECT ${EVENT_COLUMNS}
      ${driver(q)}${EVENT_JOINS}
     WHERE ${[...bounds, ...where].join("\n       AND ")}
     ORDER BY events.start_year, events.id
     LIMIT ?`;
  return { sql, params: [...boundParams, ...params, q.limit + 1] };
}

/// Spans that began before the window and are still open at `from`: the
/// lives, careers and runs that frame what starts inside it.
///
/// Everyone alive at `from` is a huge set, so by default the top-ranked
/// spans of the bucket containing `from` come from the precomputed
/// `span_lod` (category rows, or '*' across categories). A name, kind or
/// participant filter cannot be answered from the LOD and falls back to an
/// R*Tree point query ordered by rank.
export function buildActiveQuery(q: TimelineQuery): {
  sql: string;
  params: unknown[];
} {
  const precomputed =
    q.match === null &&
    q.participant === null &&
    q.kinds.length === 0 &&
    q.span !== false;
  if (precomputed) {
    const size = spanBucketSize(q.from, q.to);
    const where = [
      "span_lod.bucket_size = ?",
      "span_lod.bucket = ?",
      "span_lod.pos <= ?",
      "events.start_year < ?",
    ];
    const params: unknown[] = [
      size,
      floorBucket(q.from, size),
      q.limit,
      q.from,
    ];
    if (q.categories.length > 0) {
      where.push(`span_lod.category IN (${placeholders(q.categories.length)})`);
      params.push(...q.categories);
    } else {
      where.push("span_lod.category = '*'");
    }
    if (q.sources.length > 0) {
      where.push(`sources.slug IN (${placeholders(q.sources.length)})`);
      params.push(...q.sources);
    }
    const sql = `
    SELECT ${EVENT_COLUMNS}
      FROM span_lod
      CROSS JOIN events ON events.id = span_lod.event_id${EVENT_JOINS}
     WHERE ${where.join("\n       AND ")}
       AND coalesce(events.end_year, 9999) >= ?
     ORDER BY events.rank DESC, events.id
     LIMIT ?`;
    return { sql, params: [...params, q.from, q.limit] };
  }
  const { where, params } = buildFilters(q);
  if (q.match !== null) {
    // Few entities match a name; their spans come straight off
    // events_by_entity, no R*Tree needed.
    const bounds = [
      "events.span = 1",
      "events.start_year < ?",
      "coalesce(events.end_year, 9999) >= ?",
    ];
    const sql = `
    SELECT ${EVENT_COLUMNS}
      ${driver(q)}${EVENT_JOINS}
     WHERE ${[...bounds, ...where].join("\n       AND ")}
     ORDER BY events.rank DESC, events.id
     LIMIT ?`;
    return { sql, params: [q.from, q.from, ...params, q.limit] };
  }
  const bounds = [
    "events_span.start_year < ?",
    "events_span.end_year >= ?",
    "events.span = 1",
  ];
  const sql = `
    SELECT ${EVENT_COLUMNS}
      FROM events_span
      CROSS JOIN events ON events.id = events_span.id${EVENT_JOINS}
     WHERE ${[...bounds, ...where].join("\n       AND ")}
     ORDER BY events.rank DESC, events.id
     LIMIT ?`;
  return { sql, params: [q.from, q.from, ...params, q.limit] };
}

/// Count events starting inside the window, stopping at `cap`.
export function buildCountQuery(
  q: TimelineQuery,
  cap: number = COUNT_CAP,
): { sql: string; params: unknown[] } {
  const { where, params } = buildFilters(q);
  const sql = `
    SELECT count(*) FROM (
      SELECT 1
        ${driver(q)}
        CROSS JOIN sources ON sources.id = events.source_id
       WHERE ${["events.start_year BETWEEN ? AND ?", ...where].join("\n       AND ")}
       LIMIT ?)`;
  return { sql, params: [q.from, q.to, ...params, cap] };
}

/// Top events per bucket and category from the precomputed LOD table.
export function buildOverviewQuery(
  from: number,
  to: number,
  bucket: number,
  per: number,
  categories: string[],
  sources: string[],
): { sql: string; params: unknown[] } {
  const where = [
    "event_lod.bucket_size = ?",
    "event_lod.bucket BETWEEN ? AND ?",
    "event_lod.pos <= ?",
  ];
  const params: unknown[] = [bucket, floorBucket(from, bucket), to, per];
  if (categories.length > 0) {
    where.push(`event_lod.category IN (${placeholders(categories.length)})`);
    params.push(...categories);
  } else {
    // '*' rows hold the top events per bucket across all categories.
    where.push("event_lod.category = '*'");
  }
  if (sources.length > 0) {
    where.push(`sources.slug IN (${placeholders(sources.length)})`);
    params.push(...sources);
  }
  const sql = `
    SELECT ${EVENT_COLUMNS}, event_lod.bucket
      FROM event_lod
      CROSS JOIN events ON events.id = event_lod.event_id${EVENT_JOINS}
     WHERE ${where.join("\n       AND ")}
     ORDER BY event_lod.bucket, events.rank DESC, events.id`;
  return { sql, params };
}

/// Year buckets that floor correctly for negative years without math
/// functions: year - ((year mod b + b) mod b). Reads the precomputed
/// per-year density, so cost scales with distinct (year, category) pairs,
/// not with events.
export function buildDensityQuery(
  from: number,
  to: number,
  bucket: number,
  categories: string[],
  sources: string[],
): { sql: string; params: unknown[] } {
  const where: string[] = ["event_density.year BETWEEN ? AND ?"];
  const params: unknown[] = [bucket, bucket, bucket, from, to];
  if (categories.length > 0) {
    where.push(
      `event_density.category IN (${placeholders(categories.length)})`,
    );
    params.push(...categories);
  }
  if (sources.length > 0) {
    where.push(`sources.slug IN (${placeholders(sources.length)})`);
    params.push(...sources);
  }
  const sql = `
    SELECT event_density.year - (((event_density.year % ?) + ?) % ?) AS bucket,
           event_density.category, sum(event_density.count)
      FROM event_density
      JOIN sources ON sources.id = event_density.source_id
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
      canonicalId: num(row[19]),
    },
    certainty: str(row[20]) ?? "exact",
    rank: num(row[21]) ?? 0,
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

function yearRange(req: HttpRequest): { from: number; to: number } {
  const currentYear = new Date().getUTCFullYear();
  const from = parseYear(req.getQueryParam("from"), 1900);
  const to = Math.max(from, parseYear(req.getQueryParam("to"), currentYear));
  return { from, to };
}

function readQuery(req: HttpRequest): TimelineQuery {
  const { from, to } = yearRange(req);
  const spanParam = req.getQueryParam("span");
  return {
    from,
    to,
    categories: parseList(req.getQueryParam("category")),
    sources: parseList(req.getQueryParam("source")),
    kinds: parseList(req.getQueryParam("kind")),
    span: spanParam === "1" ? true : spanParam === "0" ? false : null,
    match: buildTrigramMatch(req.getQueryParam("q") ?? ""),
    participant: parseId(req.getQueryParam("participant")),
    cursor: parseCursor(req.getQueryParam("cursor")),
    limit: parseBounded(
      req.getQueryParam("limit"),
      DEFAULT_LIMIT,
      1,
      MAX_LIMIT,
    ),
  };
}

export async function timeline(req: HttpRequest): Promise<object> {
  const q = readQuery(req);
  try {
    const page = buildWindowQuery(q);
    const count = buildCountQuery(q);
    const active = buildActiveQuery(q);
    const [rows, countRows, activeRows] = await Promise.all([
      query(page.sql, page.params as Params),
      q.cursor === null
        ? query(count.sql, count.params as Params)
        : Promise.resolve([] as unknown[][]),
      q.cursor === null
        ? query(active.sql, active.params as Params)
        : Promise.resolve([] as unknown[][]),
    ]);
    const hasMore = rows.length > q.limit;
    const events = rows.slice(0, q.limit).map(rowToEvent);
    const activeEvents = activeRows.map(rowToEvent);
    const last = events[events.length - 1];
    const total = num(countRows[0]?.[0]);

    const anchorId = parseId(req.getQueryParam("anchor"));
    const anchor = anchorId !== null ? await loadAnchor(anchorId) : null;
    if (anchor !== null) {
      applyAnchor(events, anchor);
      applyAnchor(activeEvents, anchor);
    }

    return {
      from: q.from,
      to: q.to,
      limit: q.limit,
      total,
      totalCapped: total !== null && total >= COUNT_CAP,
      next: hasMore && last ? formatCursor(last) : null,
      anchor,
      active: activeEvents,
      events,
    };
  } catch (error) {
    console.error("[TIMELINE] query failed:", error);
    return {
      from: q.from,
      to: q.to,
      active: [],
      events: [],
      next: null,
      error: "Timeline query failed",
    };
  }
}

export async function overview(req: HttpRequest): Promise<object> {
  const { from, to } = yearRange(req);
  const requested = parseBounded(req.getQueryParam("bucket"), 10, 1, 100);
  const bucket = LOD_SIZES.includes(requested)
    ? requested
    : (LOD_SIZES.filter((s) => s <= requested).pop() ?? 1);
  const per = parseBounded(req.getQueryParam("per"), 5, 1, LOD_MAX_PER);
  const categories = parseList(req.getQueryParam("category"));
  const sources = parseList(req.getQueryParam("source"));
  try {
    const { sql, params } = buildOverviewQuery(
      from,
      to,
      bucket,
      per,
      categories,
      sources,
    );
    const rows = await query(sql, params as Params);
    const events = rows.map((r) => ({
      ...rowToEvent(r),
      bucket: num(r[22]) ?? 0,
    }));
    return { from, to, bucket, per, events };
  } catch (error) {
    console.error("[TIMELINE] overview query failed:", error);
    return {
      from,
      to,
      bucket,
      per,
      events: [],
      error: "Overview query failed",
    };
  }
}

export async function density(req: HttpRequest): Promise<object> {
  const { from, to } = yearRange(req);
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

export async function participants(req: HttpRequest): Promise<object> {
  const eventId = parseId(req.getQueryParam("event"));
  if (eventId === null) {
    return { event: null, participants: [], error: "event is required" };
  }
  try {
    const rows = await query(
      `SELECT entities.id, entities.name, entities.kind, event_participants.role,
              sources.slug, entity_links.canonical_id
         FROM event_participants
         JOIN entities ON entities.id = event_participants.entity_id
         JOIN sources ON sources.id = entities.source_id
         LEFT JOIN entity_links ON entity_links.entity_id = entities.id
        WHERE event_participants.event_id = ?
        ORDER BY event_participants.role, entities.name`,
      [eventId],
    );
    return {
      event: eventId,
      participants: rows.map((r) => ({
        entityId: num(r[0]) ?? 0,
        name: str(r[1]) ?? "",
        kind: str(r[2]) ?? "",
        role: str(r[3]) ?? "",
        source: str(r[4]) ?? "",
        canonicalId: num(r[5]),
      })),
    };
  } catch (error) {
    console.error("[TIMELINE] participants query failed:", error);
    return { event: eventId, participants: [], error: "Query failed" };
  }
}

export async function links(req: HttpRequest): Promise<object> {
  const entityId = parseId(req.getQueryParam("entity"));
  if (entityId === null) {
    return { canonical: null, members: [], error: "entity is required" };
  }
  try {
    // Resolve to the canonical entity first, then list everything that
    // resolves to it (including the canonical entity itself).
    const canon = await query(
      "SELECT coalesce((SELECT canonical_id FROM entity_links WHERE entity_id = ?), ?)",
      [entityId, entityId],
    );
    const canonicalId = num(canon[0]?.[0]) ?? entityId;
    const rows = await query(
      `SELECT entities.id, entities.name, entities.kind, entities.wikidata_id,
              entities.url, sources.slug, entity_links.method, entity_links.confidence
         FROM entities
         JOIN sources ON sources.id = entities.source_id
         LEFT JOIN entity_links ON entity_links.entity_id = entities.id
        WHERE entities.id = ? OR entity_links.canonical_id = ?
        ORDER BY entity_links.canonical_id IS NULL DESC, sources.slug`,
      [canonicalId, canonicalId],
    );
    return {
      canonical: canonicalId,
      members: rows.map((r) => ({
        entityId: num(r[0]) ?? 0,
        name: str(r[1]) ?? "",
        kind: str(r[2]) ?? "",
        wikidataId: str(r[3]),
        url: str(r[4]),
        source: str(r[5]) ?? "",
        method: str(r[6]),
        confidence: num(r[7]),
      })),
    };
  } catch (error) {
    console.error("[TIMELINE] links query failed:", error);
    return { canonical: entityId, members: [], error: "Query failed" };
  }
}

export const timelineHandlers = [
  HttpHandler.get("/timeline", async (req) =>
    HttpResponse.json(await timeline(req)),
  ),
  HttpHandler.get("/timeline/overview", async (req) =>
    HttpResponse.json(await overview(req)),
  ),
  HttpHandler.get("/timeline/density", async (req) =>
    HttpResponse.json(await density(req)),
  ),
  HttpHandler.get("/timeline/participants", async (req) =>
    HttpResponse.json(await participants(req)),
  ),
  HttpHandler.get("/timeline/links", async (req) =>
    HttpResponse.json(await links(req)),
  ),
];
