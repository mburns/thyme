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
  buildWindowQuery,
  sparseSources,
  type TimelineQuery,
} from "../../wasm/src/timeline";

const mockedQuery = query as jest.MockedFunction<typeof query>;

const base: TimelineQuery = {
  from: 1980,
  to: 1989,
  categories: [],
  sources: ["imdb"],
  kinds: [],
  span: null,
  match: null,
  participant: null,
  cursor: null,
  limit: 100,
};

describe("buildWindowQuery by source", () => {
  it("pages on the source index and joins only the page", () => {
    const { sql, params } = buildWindowQuery(base, true);
    expect(sql).toContain("INDEXED BY events_by_source_year");
    expect(sql).toContain("CROSS JOIN events ON events.id = page.id");
    expect(sql).toContain("LIMIT ?) page");
    expect(params).toEqual([1980, 1989, "imdb", 101]);
  });

  it("keeps the ordered index walk without a source filter", () => {
    const { sql } = buildWindowQuery({ ...base, sources: [] }, true);
    expect(sql).not.toContain("INDEXED BY");
    expect(sql).toContain("FROM events");
  });

  it("never overrides the FTS driver", () => {
    const { sql } = buildWindowQuery({ ...base, match: '"god"' }, true);
    expect(sql).not.toContain("INDEXED BY");
    expect(sql).toContain("FROM entities_fts CROSS JOIN events");
  });
});

describe("sparseSources", () => {
  beforeEach(() => mockedQuery.mockReset());

  it("is false without a source filter, with categories, or with a name", async () => {
    expect(await sparseSources({ ...base, sources: [] })).toBe(false);
    expect(await sparseSources({ ...base, categories: ["film"] })).toBe(false);
    expect(await sparseSources({ ...base, match: '"x"' })).toBe(false);
    expect(mockedQuery).not.toHaveBeenCalled();
  });

  it("reads the window's density for the sources", async () => {
    mockedQuery.mockResolvedValueOnce([[159n]]);
    expect(await sparseSources(base)).toBe(true);
    expect(mockedQuery.mock.calls[0]?.[1]).toEqual(["imdb", 1980, 1989]);
    mockedQuery.mockResolvedValueOnce([[500_000]]);
    expect(await sparseSources({ ...base, sources: ["musicbrainz"] })).toBe(
      false,
    );
  });
});
