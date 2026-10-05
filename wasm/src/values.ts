import type { query } from "trailbase-wasm/db";

/// The parameter list type `query()`/`execute()` accept.
export type Params = Parameters<typeof query>[1];

/// SQLite INTEGER values arrive as number or bigint depending on size; the
/// API returns plain JSON numbers.
export function num(v: unknown): number | null {
  if (typeof v === "number") {
    return v;
  }
  if (typeof v === "bigint") {
    return Number(v);
  }
  return null;
}

export function str(v: unknown): string | null {
  return typeof v === "string" ? v : null;
}
