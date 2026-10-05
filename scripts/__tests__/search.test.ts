// The handler modules import the TrailBase host bindings, which only exist
// inside the WASM runtime; the pure functions under test never touch them.
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
  buildMatchExpression,
  parseBounded,
  restrictToColumns,
} from "../../wasm/src/search";

describe("buildMatchExpression", () => {
  it("returns null for blank input", () => {
    expect(buildMatchExpression("")).toBeNull();
    expect(buildMatchExpression("   ")).toBeNull();
    expect(buildMatchExpression('""')).toBeNull();
  });

  it("quotes every term and prefix-matches the last one", () => {
    expect(buildMatchExpression("tom hanks")).toBe('"tom" "hanks"*');
    expect(buildMatchExpression("  god ")).toBe('"god"*');
  });

  it("keeps quoted phrases intact without a prefix wildcard", () => {
    expect(buildMatchExpression('"the godfather"')).toBe('"the godfather"');
    expect(buildMatchExpression('"the godfather" part')).toBe(
      '"the godfather" "part"*',
    );
  });

  it("neutralises FTS5 operators and syntax in user input", () => {
    expect(buildMatchExpression("a AND b OR NOT c")).toBe(
      '"a" "AND" "b" "OR" "NOT" "c"*',
    );
    expect(buildMatchExpression("title:foo (bar) ^baz*")).toBe(
      '"title:foo" "(bar)" "^baz*"*',
    );
    // An unbalanced quote is a literal character, escaped by doubling it.
    expect(buildMatchExpression('say "hi')).toBe('"say" """hi"*');
  });
});

describe("restrictToColumns", () => {
  it("wraps the expression in a column filter", () => {
    expect(restrictToColumns('"god"*', ["primaryTitle", "genres"])).toBe(
      '{primaryTitle genres} : ("god"*)',
    );
  });
});

describe("parseBounded", () => {
  it("falls back for missing, invalid, zero or negative values", () => {
    expect(parseBounded(null, 20, 100)).toBe(20);
    expect(parseBounded("abc", 20, 100)).toBe(20);
    expect(parseBounded("0", 20, 100)).toBe(20);
    expect(parseBounded("-5", 20, 100)).toBe(20);
  });

  it("parses and clamps valid values", () => {
    expect(parseBounded("7", 20, 100)).toBe(7);
    expect(parseBounded("99999", 20, 100)).toBe(100);
  });
});
