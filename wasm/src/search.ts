import { query } from "trailbase-wasm/db";
import {
  HttpHandler,
  type HttpRequest,
  HttpResponse,
} from "trailbase-wasm/http";
import { buildTrigramMatch } from "./timeline";
import { num, type Params, str } from "./values";

/// Full-text search over IMDB titles and persons and over timeline entities
/// from every source, served at `GET /search`.
///
/// Query parameters:
///   q        search text (required). Bare words are AND-ed and the last one
///            is prefix-matched, so "god" finds "The Godfather". Double quotes
///            keep a phrase together.
///   page     1-based page number (default 1)
///   limit    results per page and per type, 1..MAX_LIMIT (default 20)
///   titles   "false" to skip titles
///   persons  "false" to skip persons
///   entities "false" to skip timeline entities (people, teams, artists...)
///   years    "false" to stop matching title years, so "1999" only finds
///            titles with 1999 in their name

const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 100;
/// Trigram hits considered before ranking; "the" alone matches millions.
const ENTITY_HIT_CAP = 400;

export interface TitleResult {
  type: "title";
  id: number;
  tconst: string;
  titleType: string | null;
  primaryTitle: string | null;
  originalTitle: string | null;
  startYear: number | null;
  endYear: number | null;
  genres: string | null;
  averageRating: number | null;
  numVotes: number | null;
  /// primaryTitle with matched terms wrapped in <mark>.
  highlight: string | null;
}

export interface PersonResult {
  type: "person";
  id: number;
  nconst: string;
  primaryName: string | null;
  birthYear: number | null;
  deathYear: number | null;
  primaryProfession: string | null;
  /// primaryName with matched terms wrapped in <mark>.
  highlight: string | null;
}

/// A timeline entity from any source, with the span (life, career, run)
/// that best places it in time.
export interface EntityResult {
  type: "entity";
  id: number;
  name: string;
  kind: string;
  source: string;
  wikidataId: string | null;
  url: string | null;
  category: string | null;
  label: string | null;
  startYear: number | null;
  endYear: number | null;
  rank: number;
}

export interface SearchResponse {
  results: (TitleResult | PersonResult | EntityResult)[];
  totalPages: number;
  currentPage: number;
  totalResults: number;
  /// Entity hits stop at ENTITY_HIT_CAP, so the total is a lower bound.
  entitiesCapped: boolean;
  query: string;
  filters: {
    titles: boolean;
    persons: boolean;
    entities: boolean;
    years: boolean;
  };
  error?: string;
}

/// Entities whose name matches every term, best-ranked first. The trigram
/// index cannot rank, so the first ENTITY_HIT_CAP hits are taken and then
/// ordered by the rank of each entity's top event.
export function buildEntitySearchQuery(
  match: string,
  limit: number,
  offset: number,
  cap: number = ENTITY_HIT_CAP,
): { sql: string; params: unknown[] } {
  const sql = `
    SELECT entities.id, entities.name, entities.kind, sources.slug,
           entities.wikidata_id, entities.url, top.category, top.label,
           top.start_year, top.end_year, top.rank, hits.n
      FROM (SELECT rowid, count(*) OVER () AS n
              FROM (SELECT rowid FROM entities_fts WHERE entities_fts MATCH ? LIMIT ?)) hits
      CROSS JOIN entities ON entities.id = hits.rowid
      CROSS JOIN sources ON sources.id = entities.source_id
      LEFT JOIN events top ON top.id = (
             SELECT id FROM events WHERE entity_id = entities.id
              ORDER BY span DESC, rank DESC, start_year LIMIT 1)
     ORDER BY coalesce(top.rank, -1) DESC, entities.name
     LIMIT ? OFFSET ?`;
  return { sql, params: [match, cap, limit, offset] };
}

async function searchEntities(
  raw: string,
  limit: number,
  offset: number,
): Promise<{ results: EntityResult[]; total: number }> {
  const match = buildTrigramMatch(raw);
  if (match === null) {
    return { results: [], total: 0 };
  }
  const { sql, params } = buildEntitySearchQuery(match, limit, offset);
  const rows = await query(sql, params as Params);
  const results: EntityResult[] = rows.map((row) => ({
    type: "entity",
    id: num(row[0]) ?? 0,
    name: str(row[1]) ?? "",
    kind: str(row[2]) ?? "",
    source: str(row[3]) ?? "",
    wikidataId: str(row[4]),
    url: str(row[5]),
    category: str(row[6]),
    label: str(row[7]),
    startYear: num(row[8]),
    endYear: num(row[9]),
    rank: num(row[10]) ?? 0,
  }));
  return { results, total: num(rows[0]?.[11]) ?? 0 };
}

/// Turn free text into a safe FTS5 MATCH expression, or null if there is
/// nothing to search for.
///
/// Every term is wrapped in double quotes so FTS5 operators (AND, OR, NOT,
/// NEAR, `:`, `^`, `*`, parentheses) in user input are treated literally and
/// cannot produce a syntax error. Quoted input stays a phrase; the last bare
/// term gets a prefix `*` for search-as-you-type.
export function buildMatchExpression(raw: string): string | null {
  const tokens: { text: string; phrase: boolean }[] = [];
  const re = /"([^"]*)"|(\S+)/g;
  for (const m of raw.matchAll(re)) {
    const phrase = m[1] !== undefined;
    const text = (phrase ? m[1] : m[2])?.trim() ?? "";
    if (text.length > 0) {
      tokens.push({ text, phrase });
    }
  }
  if (tokens.length === 0) {
    return null;
  }

  return tokens
    .map((t, i) => {
      const quoted = `"${t.text.replace(/"/g, '""')}"`;
      const last = i === tokens.length - 1;
      return !t.phrase && last ? `${quoted}*` : quoted;
    })
    .join(" ");
}

/// Restrict a MATCH expression to the given FTS5 columns.
export function restrictToColumns(match: string, columns: string[]): string {
  return `{${columns.join(" ")}} : (${match})`;
}

/// Parse a positive integer query parameter, falling back to a default and
/// clamping to a maximum.
export function parseBounded(
  value: string | null,
  fallback: number,
  max: number,
): number {
  const n = Number.parseInt(value ?? "", 10);
  if (!Number.isFinite(n) || n < 1) {
    return fallback;
  }
  return Math.min(n, max);
}

async function count(table: string, match: string): Promise<number> {
  const rows = await query(
    `SELECT COUNT(*) FROM ${table} WHERE ${table} MATCH ?`,
    [match],
  );
  return num(rows[0]?.[0]) ?? 0;
}

async function searchTitles(
  match: string,
  limit: number,
  offset: number,
): Promise<{ results: TitleResult[]; total: number }> {
  // Most-voted first so popular titles beat obscure ones that happen to score
  // a marginally better bm25; bm25 weights favour primaryTitle over the rest.
  // highlight() wraps the matched terms of primaryTitle (FTS column 0).
  const rows = await query(
    `SELECT t.id, t.tconst, t.titleType, t.primaryTitle, t.originalTitle,
            t.startYear, t.endYear, t.genres, r.averageRating, r.numVotes,
            highlight(titles_fts, 0, '<mark>', '</mark>')
       FROM titles_fts
       JOIN titles t ON t.id = titles_fts.rowid
       LEFT JOIN ratings r ON r.title_id = t.id
      WHERE titles_fts MATCH ?
      ORDER BY COALESCE(r.numVotes, 0) DESC,
               bm25(titles_fts, 10.0, 5.0, 1.0, 1.0)
      LIMIT ? OFFSET ?`,
    [match, limit, offset] as Params,
  );

  const results: TitleResult[] = rows.map((row) => ({
    type: "title",
    id: num(row[0]) ?? 0,
    tconst: str(row[1]) ?? "",
    titleType: str(row[2]),
    primaryTitle: str(row[3]),
    originalTitle: str(row[4]),
    startYear: num(row[5]),
    endYear: num(row[6]),
    genres: str(row[7]),
    averageRating: num(row[8]),
    numVotes: num(row[9]),
    highlight: str(row[10]),
  }));

  return { results, total: await count("titles_fts", match) };
}

async function searchPersons(
  match: string,
  limit: number,
  offset: number,
): Promise<{ results: PersonResult[]; total: number }> {
  const rows = await query(
    `SELECT p.id, p.nconst, p.primaryName, p.birthYear, p.deathYear,
            p.primaryProfession, highlight(persons_fts, 0, '<mark>', '</mark>')
       FROM persons_fts
       JOIN persons p ON p.id = persons_fts.rowid
      WHERE persons_fts MATCH ?
      ORDER BY bm25(persons_fts, 10.0, 1.0)
      LIMIT ? OFFSET ?`,
    [match, limit, offset] as Params,
  );

  const results: PersonResult[] = rows.map((row) => ({
    type: "person",
    id: num(row[0]) ?? 0,
    nconst: str(row[1]) ?? "",
    primaryName: str(row[2]),
    birthYear: num(row[3]),
    deathYear: num(row[4]),
    primaryProfession: str(row[5]),
    highlight: str(row[6]),
  }));

  return { results, total: await count("persons_fts", match) };
}

export async function search(req: HttpRequest): Promise<SearchResponse> {
  const searchQuery = req.getQueryParam("q") ?? "";
  const page = parseBounded(
    req.getQueryParam("page"),
    1,
    Number.MAX_SAFE_INTEGER,
  );
  const limit = parseBounded(
    req.getQueryParam("limit"),
    DEFAULT_LIMIT,
    MAX_LIMIT,
  );
  const offset = (page - 1) * limit;

  const filters = {
    titles: req.getQueryParam("titles") !== "false",
    persons: req.getQueryParam("persons") !== "false",
    entities: req.getQueryParam("entities") !== "false",
    years: req.getQueryParam("years") !== "false",
  };

  const empty: SearchResponse = {
    results: [],
    totalPages: 0,
    currentPage: page,
    totalResults: 0,
    entitiesCapped: false,
    query: searchQuery,
    filters,
  };

  const match = buildMatchExpression(searchQuery);
  if (match === null) {
    return empty;
  }

  try {
    const titleMatch = filters.years
      ? match
      : restrictToColumns(match, ["primaryTitle", "originalTitle", "genres"]);

    const none = Promise.resolve({ results: [], total: 0 });
    const [titles, persons, entities] = await Promise.all([
      filters.titles ? searchTitles(titleMatch, limit, offset) : none,
      filters.persons ? searchPersons(match, limit, offset) : none,
      filters.entities ? searchEntities(searchQuery, limit, offset) : none,
    ]);

    // Each type is paginated independently with the same page/limit, so the
    // page count is whichever type has more pages.
    const totalPages = Math.max(
      Math.ceil(titles.total / limit),
      Math.ceil(persons.total / limit),
      Math.ceil(entities.total / limit),
    );

    return {
      results: [...entities.results, ...titles.results, ...persons.results],
      totalPages,
      currentPage: page,
      totalResults: titles.total + persons.total + entities.total,
      entitiesCapped: entities.total >= ENTITY_HIT_CAP,
      query: searchQuery,
      filters,
    };
  } catch (error) {
    console.error("[SEARCH] query failed:", error);
    return { ...empty, error: "Search failed" };
  }
}

export const searchHandlers = [
  HttpHandler.get("/search", async (req) =>
    HttpResponse.json(await search(req)),
  ),
];
