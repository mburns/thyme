// The package only ships ESM `import` exports, which Jest's CommonJS resolver
// cannot see, hence the virtual mocks.
jest.mock(
  "trailbase-wasm/db",
  () => ({ query: jest.fn(), execute: jest.fn() }),
  { virtual: true },
);
jest.mock(
  "trailbase-wasm/http",
  () => ({
    HttpHandler: {
      get: (path: string, handler: unknown) => ({ path, handler }),
    },
    HttpResponse: { json: (v: object) => v },
  }),
  { virtual: true },
);

import {
  applyAnchor,
  buildActiveQuery,
  buildCountQuery,
  buildDensityQuery,
  buildOverviewQuery,
  buildTrigramMatch,
  buildWindowQuery,
  formatCursor,
  parseCursor,
  parseList,
  parseYear,
  type TimelineEvent,
  type TimelineQuery,
} from "../../wasm/src/timeline";
import { num } from "../../wasm/src/values";

const base: TimelineQuery = {
  from: 1950,
  to: 1980,
  categories: [],
  sources: [],
  kinds: [],
  span: null,
  match: null,
  participant: null,
  cursor: null,
  limit: 100,
};

describe("num", () => {
  it("accepts numbers and bigints from the SQLite bindings", () => {
    expect(num(5)).toBe(5);
    expect(num(5n)).toBe(5);
    expect(num("5")).toBeNull();
    expect(num(null)).toBeNull();
  });
});

describe("parseList", () => {
  it("splits, trims and de-duplicates", () => {
    expect(parseList(" film, baseball ,film,,")).toEqual(["film", "baseball"]);
    expect(parseList(null)).toEqual([]);
  });
});

describe("parseYear", () => {
  it("accepts negative years and clamps the extremes", () => {
    expect(parseYear("-384", 1900)).toBe(-384);
    expect(parseYear("abc", 1900)).toBe(1900);
    expect(parseYear("99999", 1900)).toBe(9999);
  });
});

describe("cursors", () => {
  it("round-trip and reject garbage", () => {
    expect(parseCursor("1972:4150")).toEqual({ startYear: 1972, id: 4150 });
    expect(parseCursor("-384:7")).toEqual({ startYear: -384, id: 7 });
    expect(parseCursor("abc")).toBeNull();
    expect(parseCursor(null)).toBeNull();
    expect(formatCursor({ startYear: 1972, id: 4150 })).toBe("1972:4150");
  });
});

describe("buildTrigramMatch", () => {
  it("quotes terms and drops anything shorter than a trigram", () => {
    expect(buildTrigramMatch("odfath 72 AND")).toBe('"odfath" "AND"');
    expect(buildTrigramMatch("ab")).toBeNull();
    expect(buildTrigramMatch('say"hi')).toBe('"say""hi"');
  });
});

describe("buildWindowQuery", () => {
  it("scans events starting in the window in (start_year, id) order with one extra row", () => {
    const { sql, params } = buildWindowQuery(base);
    expect(sql).toContain("FROM events");
    expect(sql).not.toContain("events_span");
    expect(sql).toContain("events.start_year BETWEEN ? AND ?");
    expect(sql).toContain("ORDER BY events.start_year, events.id");
    expect(sql).toContain("LEFT JOIN entity_links");
    expect(params).toEqual([1950, 1980, 101]);
  });

  it("continues from a keyset cursor and keeps parameter order with filters", () => {
    const { sql, params } = buildWindowQuery({
      ...base,
      categories: ["film", "tv"],
      sources: ["imdb"],
      kinds: ["release"],
      span: false,
      match: '"god"',
      participant: 42,
      cursor: { startYear: 1960, id: 777 },
      limit: 10,
    });
    expect(sql).toContain("(events.start_year, events.id) > (?, ?)");
    expect(sql).toContain("events.category IN (?, ?)");
    expect(sql).toContain("sources.slug IN (?)");
    expect(sql).toContain("events.kind IN (?)");
    expect(sql).toContain("events.span = ?");
    expect(sql).toContain("entities_fts MATCH ?");
    expect(sql).toContain(
      "SELECT event_id FROM event_participants WHERE entity_id = ?",
    );
    expect(params).toEqual([
      1950,
      1980,
      1960,
      777,
      "film",
      "tv",
      "imdb",
      "release",
      0,
      '"god"',
      42,
      42,
      11,
    ]);
  });
});

describe("buildActiveQuery", () => {
  it("serves notable spans from span_lod for plain windows, '*' without a category", () => {
    const { sql, params } = buildActiveQuery(base);
    expect(sql).toContain("FROM span_lod");
    expect(sql).toContain("span_lod.category = '*'");
    expect(sql).toContain("ORDER BY events.rank DESC");
    // 31-year window -> 10-year buckets, 1950 floors to 1950.
    expect(params).toEqual([10, 1950, 100, 1950, 1950, 100]);
  });

  it("uses the category rows and 100-year buckets for wide windows", () => {
    const { sql, params } = buildActiveQuery({
      ...base,
      from: 1555,
      to: 1980,
      categories: ["baseball"],
    });
    expect(sql).toContain("span_lod.category IN (?)");
    expect(params.slice(0, 2)).toEqual([100, 1500]);
  });

  it("falls back to the R*Tree point query when a filter needs it", () => {
    const { sql, params } = buildActiveQuery({ ...base, match: '"aar"' });
    expect(sql).toContain("FROM events_span");
    expect(sql).toContain("events_span.start_year < ?");
    expect(sql).toContain("events_span.end_year >= ?");
    expect(sql).toContain("events.span = 1");
    expect(sql).toContain("ORDER BY events.rank DESC");
    expect(params).toEqual([1950, 1950, '"aar"', 100]);
  });
});

describe("join order", () => {
  it("pins events as the outer loop so ordered index walks survive the planner", () => {
    const { sql } = buildWindowQuery(base);
    expect(sql).toContain("CROSS JOIN entities");
    expect(sql).toContain("CROSS JOIN sources");
    expect(sql).not.toMatch(/\n\s+JOIN sources/);
  });
});

describe("buildCountQuery", () => {
  it("counts window starts with the shared filter and stops at the cap", () => {
    const { sql, params } = buildCountQuery(
      { ...base, categories: ["film"] },
      10000,
    );
    expect(sql).toContain("SELECT count(*) FROM (");
    expect(sql).toContain("events.category IN (?)");
    expect(sql).toContain("LIMIT ?)");
    expect(params).toEqual([1950, 1980, "film", 10000]);
  });
});

describe("buildOverviewQuery", () => {
  it("reads the LOD table for the bucket size, flooring the start bucket", () => {
    const { sql, params } = buildOverviewQuery(1955, 1980, 10, 5, ["film"], []);
    expect(sql).toContain("FROM event_lod");
    expect(sql).toContain("event_lod.bucket_size = ?");
    expect(sql).toContain("event_lod.pos <= ?");
    expect(sql).toContain("ORDER BY event_lod.bucket, events.rank DESC");
    expect(params).toEqual([10, 1950, 1980, 5, "film"]);
  });

  it("floors negative years and uses the '*' rows without a category", () => {
    const { sql, params } = buildOverviewQuery(-384, -300, 100, 3, [], []);
    expect(params.slice(0, 3)).toEqual([100, -400, -300]);
    expect(sql).toContain("event_lod.category = '*'");
  });
});

describe("buildDensityQuery", () => {
  it("reads the precomputed table and floors buckets safely for negatives", () => {
    const { sql, params } = buildDensityQuery(
      -500,
      100,
      50,
      ["philosopher"],
      [],
    );
    expect(sql).toContain("FROM event_density");
    expect(sql).toContain("sum(event_density.count)");
    expect(sql).toContain("(((event_density.year % ?) + ?) % ?)");
    expect(params).toEqual([50, 50, 50, -500, 100, "philosopher"]);
  });
});

describe("applyAnchor", () => {
  const event = (
    startYear: number,
    startJulian: number | null,
  ): TimelineEvent => ({
    id: 1,
    kind: "release",
    label: "x",
    startDate: String(startYear),
    endDate: null,
    precision: startJulian === null ? "year" : "day",
    certainty: "exact",
    startYear,
    endYear: null,
    span: false,
    category: "film",
    rank: 0,
    detail: null,
    startJulian,
    endJulian: null,
    entity: {
      id: 1,
      kind: "title",
      name: "x",
      wikidataId: null,
      url: null,
      source: "imdb",
      canonicalId: null,
    },
  });

  it("computes year offsets always and day offsets only at day precision", () => {
    const events = [event(1972, 2441317.5), event(1954, null)];
    applyAnchor(events, {
      entityId: 9,
      name: "a",
      startYear: 1934,
      startJulian: 2427473.5,
    });
    expect(events[0]?.offsetYears).toBe(38);
    expect(events[0]?.offsetDays).toBe(13844);
    expect(events[1]?.offsetYears).toBe(20);
    expect(events[1]?.offsetDays).toBeUndefined();
  });
});
