import { addRoute, jsonHandler, parsePath, query } from "../trailbase.js";

/// Full-text search over titles and persons, served at `GET /search`.
///
/// Query parameters:
///   q        search text (required). Bare words are AND-ed and the last one
///            is prefix-matched, so "god" finds "The Godfather". Double quotes
///            keep a phrase together.
///   page     1-based page number (default 1)
///   limit    results per page and per type, 1..MAX_LIMIT (default 20)
///   titles   "false" to skip titles
///   persons  "false" to skip persons
///   years    "false" to stop matching title years, so "1999" only finds
///            titles with 1999 in their name

const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 100;

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

export interface SearchResponse {
  results: (TitleResult | PersonResult)[];
  totalPages: number;
  currentPage: number;
  totalResults: number;
  query: string;
  filters: { titles: boolean; persons: boolean; years: boolean };
  error?: string;
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

function optionalNumber(v: unknown): number | null {
  return typeof v === "number" ? v : null;
}

function optionalString(v: unknown): string | null {
  return typeof v === "string" ? v : null;
}

async function count(table: string, match: string): Promise<number> {
  const rows = await query(
    `SELECT COUNT(*) FROM ${table} WHERE ${table} MATCH ?`,
    [match],
  );
  return optionalNumber(rows[0]?.[0]) ?? 0;
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
    [match, limit, offset],
  );

  const results: TitleResult[] = rows.map((row) => ({
    type: "title",
    id: optionalNumber(row[0]) ?? 0,
    tconst: optionalString(row[1]) ?? "",
    titleType: optionalString(row[2]),
    primaryTitle: optionalString(row[3]),
    originalTitle: optionalString(row[4]),
    startYear: optionalNumber(row[5]),
    endYear: optionalNumber(row[6]),
    genres: optionalString(row[7]),
    averageRating: optionalNumber(row[8]),
    numVotes: optionalNumber(row[9]),
    highlight: optionalString(row[10]),
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
    [match, limit, offset],
  );

  const results: PersonResult[] = rows.map((row) => ({
    type: "person",
    id: optionalNumber(row[0]) ?? 0,
    nconst: optionalString(row[1]) ?? "",
    primaryName: optionalString(row[2]),
    birthYear: optionalNumber(row[3]),
    deathYear: optionalNumber(row[4]),
    primaryProfession: optionalString(row[5]),
    highlight: optionalString(row[6]),
  }));

  return { results, total: await count("persons_fts", match) };
}

addRoute(
  "GET",
  "/search",
  jsonHandler(async (req): Promise<SearchResponse> => {
    const params = parsePath(req.uri).query;
    const searchQuery = params.get("q") ?? "";
    const page = parseBounded(params.get("page"), 1, Number.MAX_SAFE_INTEGER);
    const limit = parseBounded(params.get("limit"), DEFAULT_LIMIT, MAX_LIMIT);
    const offset = (page - 1) * limit;

    const filters = {
      titles: params.get("titles") !== "false",
      persons: params.get("persons") !== "false",
      years: params.get("years") !== "false",
    };

    const empty: SearchResponse = {
      results: [],
      totalPages: 0,
      currentPage: page,
      totalResults: 0,
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

      const [titles, persons] = await Promise.all([
        filters.titles
          ? searchTitles(titleMatch, limit, offset)
          : Promise.resolve({ results: [], total: 0 }),
        filters.persons
          ? searchPersons(match, limit, offset)
          : Promise.resolve({ results: [], total: 0 }),
      ]);

      // Each type is paginated independently with the same page/limit, so the
      // page count is whichever type has more pages.
      const totalPages = Math.max(
        Math.ceil(titles.total / limit),
        Math.ceil(persons.total / limit),
      );

      return {
        results: [...titles.results, ...persons.results],
        totalPages,
        currentPage: page,
        totalResults: titles.total + persons.total,
        query: searchQuery,
        filters,
      };
    } catch (error) {
      console.error("[SEARCH] query failed:", error);
      return { ...empty, error: "Search failed" };
    }
  }),
);
