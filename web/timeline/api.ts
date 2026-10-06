/// Typed access to the timeline endpoints with a tile cache, so scrolling
/// back over a stretch of years never refetches it.

export interface Entity {
  id: number;
  kind: string;
  name: string;
  wikidataId: string | null;
  url: string | null;
  source: string;
  canonicalId: number | null;
}

export interface Ev {
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
  entity: Entity;
}

export interface SourceSummary {
  slug: string;
  name: string;
  kind: string;
  homepage: string | null;
  license: string | null;
  description: string | null;
  events: number;
  entities: number | null;
  firstYear: number | null;
  lastYear: number | null;
  categoryCount: number;
  topCategories: { category: string; events: number }[];
  lastSync: { finished: number | null; version: string | null } | null;
}

export interface DensityBar {
  year: number;
  source: string;
  count: number;
}

export interface Participant {
  entityId: number;
  name: string;
  kind: string;
  role: string;
  source: string;
}

export interface Tile {
  events: Ev[];
  /// True when the server capped the page, so zooming in shows more.
  truncated: boolean;
  /// Set when the request failed; the tile is kept empty rather than
  /// refetched on every frame.
  error?: string;
}

export interface TileRequest {
  source: string;
  from: number;
  to: number;
  categories: string[];
  /// Event kinds; only the detail tier can filter by them.
  kinds: string[];
  q: string;
  tier:
    | { kind: "overview"; bucket: number; per: number }
    | { kind: "detail"; limit: number };
}

export interface DomainSummary {
  slug: string;
  name: string;
  blurb: string;
  categories: string[];
  kinds: string[];
  sources: string[];
  planned: string[];
  events: number;
  firstYear: number | null;
  lastYear: number | null;
  categoryCounts: { category: string; events: number }[];
}

function qs(params: Record<string, string | number | null | undefined>) {
  const out = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== "") {
      out.set(k, String(v));
    }
  }
  return out.toString();
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`${url}: HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

export function tileKey(r: TileRequest): string {
  const tier =
    r.tier.kind === "overview"
      ? `o${r.tier.bucket}x${r.tier.per}`
      : `d${r.tier.limit}`;
  return [
    r.source,
    tier,
    r.from,
    r.to,
    r.categories.join(","),
    r.kinds.join(","),
    r.q,
  ].join("|");
}

export class Api {
  private readonly tiles = new Map<string, Promise<Tile>>();
  /// Tiles that have arrived, readable synchronously while rendering.
  private readonly ready = new Map<string, Tile>();

  constructor(private readonly base = "") {}

  sources(): Promise<{ sources: SourceSummary[] }> {
    return getJson(`${this.base}/timeline/sources?top=6`);
  }

  domains(): Promise<{ domains: DomainSummary[] }> {
    return getJson(`${this.base}/timeline/domains`);
  }

  density(
    from: number,
    to: number,
    bucket: number,
    sources: string[],
    categories: string[],
  ): Promise<{ buckets: DensityBar[] }> {
    const q = qs({
      from,
      to,
      bucket,
      by: "source",
      source: sources.join(","),
      category: categories.join(","),
    });
    return getJson(`${this.base}/timeline/density?${q}`);
  }

  participants(eventId: number): Promise<{ participants: Participant[] }> {
    return getJson(`${this.base}/timeline/participants?event=${eventId}`);
  }

  /// Fetch one tile, or return the in-flight/cached promise for it.
  tile(r: TileRequest): Promise<Tile> {
    const key = tileKey(r);
    let p = this.tiles.get(key);
    if (p === undefined) {
      p = this.fetchTile(r)
        .then((tile) => {
          this.ready.set(key, tile);
          return tile;
        })
        .catch((err: unknown) => {
          const tile: Tile = {
            events: [],
            truncated: false,
            error: err instanceof Error ? err.message : String(err),
          };
          this.ready.set(key, tile);
          return tile;
        });
      this.tiles.set(key, p);
    }
    return p;
  }

  /// The tile when it has arrived, or undefined while it is loading or
  /// has not been requested yet.
  peek(r: TileRequest): Tile | undefined {
    return this.ready.get(tileKey(r));
  }

  inFlight(r: TileRequest): boolean {
    return this.tiles.has(tileKey(r));
  }

  clear(): void {
    this.tiles.clear();
    this.ready.clear();
  }

  private async fetchTile(r: TileRequest): Promise<Tile> {
    const common = {
      from: r.from,
      to: r.to,
      source: r.source,
      category: r.categories.join(","),
    };
    if (r.tier.kind === "overview") {
      const data = await getJson<{ events: Ev[] }>(
        `${this.base}/timeline/overview?${qs({
          ...common,
          bucket: r.tier.bucket,
          per: r.tier.per,
        })}`,
      );
      return { events: data.events, truncated: false };
    }
    const data = await getJson<{
      events: Ev[];
      active: Ev[];
      next: string | null;
    }>(
      `${this.base}/timeline?${qs({
        ...common,
        q: r.q,
        kind: r.kinds.join(","),
        limit: r.tier.limit,
      })}`,
    );
    return {
      events: [...data.active, ...data.events],
      truncated: data.next !== null,
    };
  }
}
