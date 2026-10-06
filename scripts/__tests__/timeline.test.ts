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
  buildCountQuery,
  buildDensityQuery,
  buildEventsQuery,
  buildTrigramMatch,
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
  limit: 100,
  offset: 0,
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

describe("buildTrigramMatch", () => {
  it("quotes terms and drops anything shorter than a trigram", () => {
    expect(buildTrigramMatch("odfath 72 AND")).toBe('"odfath" "AND"');
    expect(buildTrigramMatch("ab")).toBeNull();
    expect(buildTrigramMatch('say"hi')).toBe('"say""hi"');
  });
});

describe("buildEventsQuery", () => {
  it("always applies the R*Tree overlap bounds and paging, without a window count", () => {
    const { sql, params } = buildEventsQuery(base);
    expect(sql).toContain("FROM events_span");
    expect(sql).toContain("events_span.start_year <= ?");
    expect(sql).toContain("events_span.end_year >= ?");
    expect(sql).toContain("LEFT JOIN entity_links");
    expect(sql).toContain("row_number() OVER (PARTITION BY events.entity_id");
    expect(sql).not.toContain("count(*) OVER ()");
    expect(params).toEqual([1980, 1950, 100, 0]);
  });

  it("adds one placeholder per list item and keeps parameter order", () => {
    const { sql, params } = buildEventsQuery({
      ...base,
      categories: ["film", "tv"],
      sources: ["imdb"],
      kinds: ["release"],
      span: false,
      match: '"god"',
      participant: 42,
      limit: 10,
      offset: 20,
    });
    expect(sql).toContain("events.category IN (?, ?)");
    expect(sql).toContain("sources.slug IN (?)");
    expect(sql).toContain("events.kind IN (?)");
    expect(sql).toContain("events.span = ?");
    expect(sql).toContain("entities_fts MATCH ?");
    expect(sql).toContain(
      "SELECT event_id FROM event_participants WHERE entity_id = ?",
    );
    expect(params).toEqual([
      1980,
      1950,
      "film",
      "tv",
      "imdb",
      "release",
      0,
      '"god"',
      42,
      42,
      10,
      20,
    ]);
  });
});

describe("buildCountQuery", () => {
  it("shares the filter and stops counting at the cap", () => {
    const { sql, params } = buildCountQuery(
      { ...base, categories: ["film"] },
      10000,
    );
    expect(sql).toContain("SELECT count(*) FROM (");
    expect(sql).toContain("events.category IN (?)");
    expect(sql).toContain("LIMIT ?)");
    expect(params).toEqual([1980, 1950, "film", 10000]);
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
    seq: 1,
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
