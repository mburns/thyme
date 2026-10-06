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

import { query } from "trailbase-wasm/db";
import {
  buildDomainCategoriesQuery,
  buildDomainKindsQuery,
  DOMAINS,
  summarize,
} from "../../wasm/src/domains";

const mockedQuery = query as jest.MockedFunction<typeof query>;

describe("DOMAINS", () => {
  it("has unique slugs and lists the API can filter by", () => {
    const slugs = DOMAINS.map((d) => d.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
    for (const d of DOMAINS) {
      // parseList caps comma-separated filters at 50 entries.
      expect(d.categories.length).toBeLessThanOrEqual(50);
      expect(new Set(d.categories).size).toBe(d.categories.length);
      expect(d.categories.length + d.kinds.length).toBeGreaterThan(0);
      expect(d.planned.length).toBeGreaterThan(0);
    }
  });

  it("covers the categories the ingested sources produce", () => {
    const all = new Set(DOMAINS.flatMap((d) => d.categories));
    for (const c of ["film", "music", "baseball", "basketball", "politician"]) {
      expect(all.has(c)).toBe(true);
    }
  });
});

describe("query builders", () => {
  it("bind one placeholder per category or kind", () => {
    const c = buildDomainCategoriesQuery(["a", "b"]);
    expect(c.sql).toContain("category IN (?, ?)");
    expect(c.params).toEqual(["a", "b"]);
    const k = buildDomainKindsQuery(["award"]);
    expect(k.sql).toContain("kind IN (?)");
    expect(k.params).toEqual(["award"]);
  });
});

describe("summarize", () => {
  it("keeps stub categories at zero and merges kind counts", async () => {
    mockedQuery
      .mockResolvedValueOnce([["baseball", 100n, 1871n, 2025n]])
      .mockResolvedValueOnce([[12n, 1900n, 2024n]]);
    const s = await summarize({
      slug: "t",
      name: "T",
      blurb: "",
      categories: ["baseball", "cricket"],
      kinds: ["award"],
      sources: [],
      planned: ["x"],
    });
    expect(s.events).toBe(112);
    expect(s.firstYear).toBe(1871);
    expect(s.lastYear).toBe(2025);
    expect(s.categoryCounts).toEqual([
      { category: "baseball", events: 100 },
      { category: "cricket", events: 0 },
    ]);
  });
});
