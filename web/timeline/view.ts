/// The banded timeline: one horizontal band per data source, a year axis
/// that stays put while the bands scroll, and a density minimap of the
/// whole world range. Zooming swaps data tiers (LOD rows when zoomed out,
/// the full event stream when zoomed in) so the DOM never holds more than a
/// few thousand items.

import type { Api, Ev, SourceSummary, TileRequest } from "./api";
import {
  colorFor,
  densityBucket,
  floorTo,
  formatYear,
  fractionalYear,
  labelWidth,
  MAX_PX_PER_YEAR,
  MIN_PX_PER_YEAR,
  majorStep,
  packLanes,
  type Tier,
  ticksFor,
  tierFor,
  tilesFor,
} from "./scale";

export interface Anchor {
  name: string;
  year: number;
}

export interface ViewState {
  worldFrom: number;
  worldTo: number;
  pxPerYear: number;
  /// Enabled source slugs; empty means every source.
  sources: string[];
  q: string;
  categories: string[];
  /// Event kinds; forces the detail tier since LOD rows are per category.
  kinds: string[];
  anchor: Anchor | null;
}

const ROW_PX = 22;
const BAND_PAD_PX = 28;
const MAX_LANES_OVERVIEW = 8;
const MAX_LANES_DETAIL = 16;
const MAX_CANVAS_PX = 8_000_000;
const Q_LIMIT = 2000;

function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className: string,
  parent?: HTMLElement,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  node.className = className;
  parent?.appendChild(node);
  return node;
}

function dateText(e: Ev): string {
  const start = e.precision === "year" ? formatYear(e.startYear) : e.startDate;
  if (!e.span) {
    return e.certainty === "circa" ? `c. ${start}` : start;
  }
  const end =
    e.endYear === null
      ? "present"
      : e.precision === "year" || e.endDate === null
        ? formatYear(e.endYear)
        : e.endDate;
  return `${start} – ${end}`;
}

interface Band {
  source: SourceSummary;
  color: string;
  root: HTMLElement;
  header: HTMLElement;
  items: HTMLElement;
  shown: number;
  hidden: number;
  truncated: boolean;
}

export class TimelineView {
  private readonly scroll: HTMLElement;
  private readonly canvas: HTMLElement;
  private readonly axis: HTMLElement;
  private readonly relAxis: HTMLElement;
  private readonly grid: HTMLElement;
  private readonly bandsBox: HTMLElement;
  private readonly minimap: HTMLCanvasElement;
  private readonly minimapView: HTMLElement;
  private readonly detail: HTMLElement;
  private readonly status: HTMLElement;
  private readonly bands = new Map<string, Band>();
  private readonly byId = new Map<number, Ev>();
  private sources: SourceSummary[] = [];
  private frame = 0;
  private renderedKey = "";
  private densityKey = "";
  private pendingTiles = 0;

  constructor(
    root: HTMLElement,
    private readonly api: Api,
    private state: ViewState,
    private readonly onState: (s: ViewState) => void,
  ) {
    root.classList.add("tl");
    const mini = el("div", "tl-minimap", root);
    this.minimap = el("canvas", "tl-minimap-canvas", mini);
    this.minimapView = el("div", "tl-minimap-view", mini);
    mini.addEventListener("click", (ev) => this.onMinimapClick(ev));

    const body = el("div", "tl-body", root);
    this.scroll = el("div", "tl-scroll", body);
    this.canvas = el("div", "tl-canvas", this.scroll);
    this.axis = el("div", "tl-axis", this.canvas);
    this.relAxis = el("div", "tl-axis tl-axis-rel", this.canvas);
    this.grid = el("div", "tl-grid", this.canvas);
    this.bandsBox = el("div", "tl-bands", this.canvas);
    this.detail = el("aside", "tl-detail", body);
    this.detail.hidden = true;
    this.status = el("div", "tl-status", root);

    this.scroll.addEventListener("scroll", () => this.schedule(), {
      passive: true,
    });
    this.scroll.addEventListener(
      "wheel",
      (ev) => {
        if (ev.ctrlKey || ev.metaKey) {
          ev.preventDefault();
          this.zoomBy(ev.deltaY < 0 ? 1.25 : 0.8, ev.clientX);
        }
      },
      { passive: false },
    );
    this.bandsBox.addEventListener("click", (ev) => this.onItemClick(ev));
    window.addEventListener("resize", () => this.schedule());
  }

  get current(): ViewState {
    return this.state;
  }

  /// Build the bands and show the initial window.
  async mount(sources: SourceSummary[], centerYear?: number): Promise<void> {
    this.sources = sources;
    sources.forEach((s, i) => this.addBand(s, colorFor(i)));
    this.applyEnabled();
    this.layoutCanvas();
    if (centerYear !== undefined) {
      this.scrollToYear(centerYear);
    }
    this.schedule();
  }

  /// The source slugs with a band, in display order.
  get sourceSlugs(): string[] {
    return this.sources.map((s) => s.slug);
  }

  setState(patch: Partial<ViewState>): void {
    const before = this.state;
    this.state = { ...before, ...patch };
    const worldChanged =
      before.worldFrom !== this.state.worldFrom ||
      before.worldTo !== this.state.worldTo;
    if (worldChanged || before.pxPerYear !== this.state.pxPerYear) {
      const keep = this.centerYear();
      this.layoutCanvas();
      this.scrollToYear(keep);
    }
    if (before.sources !== this.state.sources) {
      this.applyEnabled();
    }
    if (
      before.q !== this.state.q ||
      before.categories !== this.state.categories ||
      before.kinds !== this.state.kinds ||
      before.anchor !== this.state.anchor
    ) {
      this.renderedKey = "";
    }
    this.schedule();
  }

  /// True when the filters can only be answered from the event stream.
  private needsDetail(): boolean {
    return this.state.q.trim().length >= 3 || this.state.kinds.length > 0;
  }

  /// Years visible in the viewport.
  visibleRange(): { from: number; to: number } {
    const { worldFrom, pxPerYear } = this.state;
    const from = worldFrom + this.scroll.scrollLeft / pxPerYear;
    return { from, to: from + this.scroll.clientWidth / pxPerYear };
  }

  centerYear(): number {
    const v = this.visibleRange();
    return (v.from + v.to) / 2;
  }

  scrollToYear(year: number, align: "center" | "left" = "center"): void {
    const { worldFrom, pxPerYear } = this.state;
    const offset = align === "center" ? this.scroll.clientWidth / 2 : 0;
    this.scroll.scrollLeft = (year - worldFrom) * pxPerYear - offset;
    this.schedule();
  }

  zoomBy(factor: number, clientX?: number): void {
    const next = Math.min(
      Math.max(this.state.pxPerYear * factor, MIN_PX_PER_YEAR),
      this.maxPxPerYear(),
    );
    if (next === this.state.pxPerYear) {
      return;
    }
    const rect = this.scroll.getBoundingClientRect();
    const px = clientX === undefined ? rect.width / 2 : clientX - rect.left;
    const yearAt =
      this.state.worldFrom +
      (this.scroll.scrollLeft + px) / this.state.pxPerYear;
    this.state = { ...this.state, pxPerYear: next };
    this.layoutCanvas();
    this.scroll.scrollLeft = (yearAt - this.state.worldFrom) * next - px;
    this.renderedKey = "";
    this.schedule();
    this.onState(this.state);
  }

  private maxPxPerYear(): number {
    const years = Math.max(1, this.state.worldTo - this.state.worldFrom);
    return Math.min(MAX_PX_PER_YEAR, MAX_CANVAS_PX / years);
  }

  private layoutCanvas(): void {
    const { worldFrom, worldTo } = this.state;
    const p = Math.min(this.state.pxPerYear, this.maxPxPerYear());
    this.state = { ...this.state, pxPerYear: p };
    this.canvas.style.width = `${Math.ceil((worldTo - worldFrom) * p)}px`;
    this.renderedKey = "";
    this.densityKey = "";
  }

  private addBand(source: SourceSummary, color: string): void {
    const root = el("section", "tl-band", this.bandsBox);
    root.setAttribute("data-source", source.slug);
    root.style.setProperty("--band", color);
    const header = el("header", "tl-band-header", root);
    const items = el("div", "tl-band-items", root);
    this.bands.set(source.slug, {
      source,
      color,
      root,
      header,
      items,
      shown: 0,
      hidden: 0,
      truncated: false,
    });
    this.renderBandHeader(source.slug);
  }

  private enabledSlugs(): string[] {
    const wanted = this.state.sources;
    return this.sources
      .map((s) => s.slug)
      .filter((slug) => wanted.length === 0 || wanted.includes(slug));
  }

  private applyEnabled(): void {
    const enabled = new Set(this.enabledSlugs());
    for (const [slug, band] of this.bands) {
      band.root.hidden = !enabled.has(slug);
    }
    this.renderedKey = "";
    this.densityKey = "";
  }

  private schedule(): void {
    if (this.frame !== 0) {
      return;
    }
    this.frame = requestAnimationFrame(() => {
      this.frame = 0;
      this.update();
    });
  }

  /// The tier for the current zoom; a name or kind filter always reads the
  /// event stream, since the LOD tables cannot answer it, in one
  /// world-sized tile.
  private tier(): Tier {
    if (this.needsDetail()) {
      return {
        kind: "detail",
        tileYears: this.state.worldTo - this.state.worldFrom + 1,
        limit: Q_LIMIT,
      };
    }
    return tierFor(this.state.pxPerYear);
  }

  private tileRequests(
    slug: string,
    tier: Tier,
    from: number,
    to: number,
  ): TileRequest[] {
    const { worldFrom, worldTo, categories, kinds, q } = this.state;
    const apiTier =
      tier.kind === "overview"
        ? { kind: "overview" as const, bucket: tier.bucket, per: tier.per }
        : { kind: "detail" as const, limit: tier.limit };
    if (tier.kind === "detail" && this.needsDetail()) {
      return [
        {
          source: slug,
          from: worldFrom,
          to: worldTo,
          categories,
          kinds,
          q: q.trim().length >= 3 ? q.trim() : "",
          tier: apiTier,
        },
      ];
    }
    return tilesFor(
      Math.max(from, worldFrom),
      Math.min(to, worldTo),
      tier.tileYears,
    ).map((start) => ({
      source: slug,
      from: start,
      to: start + tier.tileYears - 1,
      categories,
      kinds: [],
      q: "",
      tier: apiTier,
    }));
  }

  private update(): void {
    const visible = this.visibleRange();
    const span = Math.max(1, visible.to - visible.from);
    const from = visible.from - span;
    const to = visible.to + span;
    const tier = this.tier();
    this.renderAxis(from, to);
    this.updateMinimapView(visible);
    this.loadDensity();

    const tierKey =
      tier.kind === "overview" ? `o${tier.bucket}` : `d${tier.tileYears}`;
    const bands = this.enabledSlugs();
    const collected = new Map<string, { events: Ev[]; truncated: boolean }>();
    let loadedTiles = 0;
    for (const slug of bands) {
      const events: Ev[] = [];
      let truncated = false;
      for (const req of this.tileRequests(slug, tier, from, to)) {
        const tile = this.api.peek(req);
        if (tile === undefined) {
          if (!this.api.inFlight(req)) {
            this.fetchTile(req);
          }
          continue;
        }
        loadedTiles += 1;
        events.push(...tile.events);
        truncated = truncated || tile.truncated;
      }
      collected.set(slug, { events, truncated });
    }
    const step = span / 2;
    const key = [
      tierKey,
      floorTo(Math.round(visible.from), Math.max(1, Math.round(step))),
      Math.round(this.state.pxPerYear * 1000),
      loadedTiles,
      bands.join(","),
      this.state.q,
      this.state.categories.join(","),
      this.state.kinds.join(","),
      this.state.anchor?.year ?? "",
    ].join("|");
    if (key === this.renderedKey) {
      this.renderStatus();
      return;
    }
    this.renderedKey = key;
    this.byId.clear();
    for (const slug of bands) {
      const got = collected.get(slug);
      this.renderBand(
        slug,
        got?.events ?? [],
        got?.truncated ?? false,
        tier,
        from,
        to,
      );
    }
    this.renderStatus();
    this.onState(this.state);
  }

  private fetchTile(req: TileRequest): void {
    this.pendingTiles += 1;
    this.api
      .tile(req)
      .then(() => {
        this.renderedKey = "";
        this.schedule();
      })
      .catch((err: unknown) => {
        console.error("tile failed", req, err);
        this.status.textContent = "Some events failed to load.";
      })
      .finally(() => {
        this.pendingTiles -= 1;
        this.renderStatus();
      });
  }

  private renderStatus(): void {
    const v = this.visibleRange();
    const tier = this.tier();
    const detail =
      tier.kind === "detail"
        ? "every event"
        : `top ${tier.per} per ${tier.bucket === 1 ? "year" : `${tier.bucket} years`}`;
    const loading = this.pendingTiles > 0 ? " · loading…" : "";
    this.status.textContent = `${formatYear(Math.floor(v.from))} – ${formatYear(Math.ceil(v.to))} · ${detail}${loading}`;
  }

  private renderAxis(from: number, to: number): void {
    const { worldFrom, pxPerYear, anchor } = this.state;
    const ticks = ticksFor(Math.floor(from), Math.ceil(to), pxPerYear);
    const parts: string[] = [];
    const lines: string[] = [];
    for (const t of ticks) {
      const x = (t.year - worldFrom) * pxPerYear;
      parts.push(
        `<span class="tl-tick${t.major ? " tl-tick-major" : ""}" style="left:${x}px">${t.label === null ? "" : `<b>${esc(t.label)}</b>`}</span>`,
      );
      if (t.major) {
        lines.push(`<i style="left:${x}px"></i>`);
      }
    }
    const now = new Date().getFullYear();
    if (now >= from && now <= to) {
      lines.push(
        `<i class="tl-now" style="left:${(now - worldFrom) * pxPerYear}px"></i>`,
      );
    }
    this.axis.innerHTML = parts.join("");
    this.grid.innerHTML = lines.join("");

    if (anchor === null) {
      this.relAxis.hidden = true;
      return;
    }
    this.relAxis.hidden = false;
    const step = majorStep(pxPerYear);
    const rel: string[] = [];
    const first = anchor.year + Math.floor((from - anchor.year) / step) * step;
    for (let y = first; y <= to; y += step) {
      const d = y - anchor.year;
      const label =
        d === 0 ? esc(anchor.name) : `${d > 0 ? "+" : "−"}${Math.abs(d)}`;
      rel.push(
        `<span class="tl-tick tl-tick-major${d === 0 ? " tl-tick-anchor" : ""}" style="left:${(y - worldFrom) * pxPerYear}px"><b>${label}</b></span>`,
      );
    }
    lines.push(
      `<i class="tl-anchor-line" style="left:${(anchor.year - worldFrom) * pxPerYear}px"></i>`,
    );
    this.grid.innerHTML = lines.join("");
    this.relAxis.innerHTML = rel.join("");
  }

  private renderBand(
    slug: string,
    events: Ev[],
    truncated: boolean,
    tier: Tier,
    from: number,
    to: number,
  ): void {
    const band = this.bands.get(slug);
    if (band === undefined) {
      return;
    }
    const { worldFrom, pxPerYear, anchor } = this.state;
    const now = new Date().getFullYear();
    const seen = new Set<number>();
    const boxes: { item: Ev; x0: number; x1: number }[] = [];
    for (const e of events) {
      if (seen.has(e.id)) {
        continue;
      }
      seen.add(e.id);
      const endYear = e.span ? (e.endYear ?? now) : e.startYear;
      if (endYear < from || e.startYear > to) {
        continue;
      }
      const start = fractionalYear(e.startDate, e.startYear);
      const x0 = (start - worldFrom) * pxPerYear;
      const xEnd = e.span ? (endYear + 1 - worldFrom) * pxPerYear : x0;
      boxes.push({
        item: e,
        x0,
        x1: Math.max(xEnd, x0 + labelWidth(e.label) + (e.span ? 0 : 10)),
      });
    }
    boxes.sort((a, b) => a.x0 - b.x0 || b.item.rank - a.item.rank);
    const maxLanes =
      tier.kind === "detail" ? MAX_LANES_DETAIL : MAX_LANES_OVERVIEW;
    const { placed, hidden } = packLanes(boxes, maxLanes);
    const lanes = Math.max(1, ...placed.map((p) => p.lane + 1));
    const html: string[] = [];
    for (const { item: e, lane } of placed) {
      this.byId.set(e.id, e);
      const start = fractionalYear(e.startDate, e.startYear);
      const x0 = (start - worldFrom) * pxPerYear;
      const endYear = e.span ? (e.endYear ?? now) : e.startYear;
      const width = e.span ? Math.max(2, (endYear + 1 - start) * pxPerYear) : 0;
      const classes = ["tl-item", e.span ? "tl-span" : "tl-instant"];
      if (e.span && e.endYear === null) {
        classes.push("tl-open");
      }
      if (e.certainty !== "exact") {
        classes.push("tl-circa");
      }
      const offset =
        anchor === null
          ? ""
          : ` · ${e.startYear - anchor.year >= 0 ? "+" : ""}${e.startYear - anchor.year} yrs from ${anchor.name}`;
      const title = `${e.label} (${dateText(e)}) · ${e.entity.name} · ${e.category}${offset}`;
      html.push(
        `<div class="${classes.join(" ")}" data-id="${e.id}" style="left:${x0.toFixed(1)}px;top:${lane * ROW_PX}px;${e.span ? `width:${width.toFixed(1)}px` : ""}" title="${esc(title)}"><span class="tl-label">${esc(e.label)}</span></div>`,
      );
    }
    band.items.style.height = `${lanes * ROW_PX + 6}px`;
    band.items.innerHTML = html.join("");
    band.shown = placed.length;
    band.hidden = hidden;
    band.truncated = truncated;
    band.root.style.minHeight = `${lanes * ROW_PX + BAND_PAD_PX}px`;
    this.renderBandHeader(slug);
  }

  private renderBandHeader(slug: string): void {
    const band = this.bands.get(slug);
    if (band === undefined) {
      return;
    }
    const notes: string[] = [];
    if (band.hidden > 0) {
      notes.push(`+${band.hidden.toLocaleString()} hidden, zoom in`);
    }
    if (band.truncated) {
      notes.push("page capped");
    }
    band.header.innerHTML = `<span class="tl-swatch"></span><a href="/sources.html#${esc(slug)}">${esc(band.source.name)}</a><small>${esc(notes.join(" · "))}</small>`;
  }

  private onItemClick(ev: MouseEvent): void {
    const target = (ev.target as HTMLElement).closest<HTMLElement>(".tl-item");
    if (target === null) {
      return;
    }
    const id = Number(target.getAttribute("data-id"));
    const e = this.byId.get(id);
    if (e !== undefined) {
      this.showDetail(e);
    }
  }

  showDetail(e: Ev): void {
    const d = this.detail;
    d.hidden = false;
    const details = Object.entries(e.detail ?? {})
      .filter(([, v]) => v !== null && v !== "" && typeof v !== "object")
      .map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(String(v))}</dd>`)
      .join("");
    const anchorYear = this.state.anchor?.year;
    const offset =
      anchorYear === undefined
        ? ""
        : `<p class="tl-offset">${e.startYear - anchorYear >= 0 ? "+" : ""}${e.startYear - anchorYear} years from ${esc(this.state.anchor?.name ?? "")}</p>`;
    d.innerHTML = `
      <button class="tl-close" type="button" aria-label="Close">×</button>
      <h3>${esc(e.label)}</h3>
      <p class="tl-dates">${esc(dateText(e))}</p>
      ${offset}
      <p><a href="/entity.html#${e.entity.id}">${esc(e.entity.name)}</a> <small>${esc(e.entity.kind)} · ${esc(e.entity.source)}</small></p>
      <p><small>${esc(e.category)} · ${esc(e.kind)}${e.certainty !== "exact" ? ` · ${esc(e.certainty)}` : ""}</small></p>
      ${details ? `<dl>${details}</dl>` : ""}
      <div class="tl-participants"></div>
      <p class="tl-actions">
        <button type="button" data-act="center">Center</button>
        <button type="button" data-act="anchor">Compare from here</button>
        <button type="button" data-act="filter">Only “${esc(e.entity.name)}”</button>
        ${e.entity.url ? `<a href="${esc(e.entity.url)}" target="_blank" rel="noopener">Source page</a>` : ""}
      </p>`;
    d.querySelector(".tl-close")?.addEventListener("click", () => {
      d.hidden = true;
    });
    d.querySelector('[data-act="center"]')?.addEventListener("click", () => {
      this.scrollToYear(e.startYear);
    });
    d.querySelector('[data-act="anchor"]')?.addEventListener("click", () => {
      this.setState({ anchor: { name: e.label, year: e.startYear } });
      this.onState(this.state);
    });
    d.querySelector('[data-act="filter"]')?.addEventListener("click", () => {
      this.setState({ q: e.entity.name });
      this.onState(this.state);
    });
    const box = d.querySelector<HTMLElement>(".tl-participants");
    if (box !== null && !e.span) {
      this.api
        .participants(e.id)
        .then(({ participants }) => {
          if (participants.length === 0) {
            return;
          }
          box.innerHTML = `<h4>Participants</h4><ul>${participants
            .map(
              (p) =>
                `<li><a href="/entity.html#${p.entityId}">${esc(p.name)}</a> <small>${esc(p.role)}</small></li>`,
            )
            .join("")}</ul>`;
        })
        .catch(() => undefined);
    }
  }

  private loadDensity(): void {
    const { worldFrom, worldTo, categories } = this.state;
    const slugs = this.enabledSlugs();
    const key = [
      worldFrom,
      worldTo,
      slugs.join(","),
      categories.join(","),
    ].join("|");
    if (key === this.densityKey) {
      return;
    }
    this.densityKey = key;
    const bucket = densityBucket(worldTo - worldFrom);
    this.api
      .density(worldFrom, worldTo, bucket, slugs, categories)
      .then(({ buckets }) => {
        if (this.densityKey === key) {
          this.drawMinimap(buckets, bucket);
        }
      })
      .catch((err: unknown) => console.error("density failed", err));
  }

  private drawMinimap(
    bars: { year: number; source: string; count: number }[],
    bucket: number,
  ): void {
    const c = this.minimap;
    const width = c.clientWidth || 800;
    const height = c.clientHeight || 48;
    c.width = width * devicePixelRatio;
    c.height = height * devicePixelRatio;
    const ctx = c.getContext("2d");
    if (ctx === null) {
      return;
    }
    ctx.scale(devicePixelRatio, devicePixelRatio);
    ctx.clearRect(0, 0, width, height);
    const { worldFrom, worldTo } = this.state;
    const years = Math.max(1, worldTo - worldFrom);
    const totals = new Map<number, number>();
    for (const b of bars) {
      totals.set(b.year, (totals.get(b.year) ?? 0) + b.count);
    }
    const max = Math.max(1, ...totals.values());
    const stacked = new Map<number, number>();
    const barW = Math.max(1, (bucket / years) * width);
    for (const b of bars) {
      const band = this.bands.get(b.source);
      ctx.fillStyle = band?.color ?? "#888";
      // Square root keeps a 5M-event source from flattening a 60k one.
      const h = (Math.sqrt(b.count) / Math.sqrt(max)) * (height - 2);
      const base = stacked.get(b.year) ?? 0;
      const x = ((b.year - worldFrom) / years) * width;
      ctx.fillRect(x, height - base - h, barW, h);
      stacked.set(b.year, base + h);
    }
  }

  private updateMinimapView(visible: { from: number; to: number }): void {
    const { worldFrom, worldTo } = this.state;
    const years = Math.max(1, worldTo - worldFrom);
    const left = ((visible.from - worldFrom) / years) * 100;
    const width = ((visible.to - visible.from) / years) * 100;
    this.minimapView.style.left = `${Math.max(0, left)}%`;
    this.minimapView.style.width = `${Math.max(0.3, Math.min(100, width))}%`;
  }

  private onMinimapClick(ev: MouseEvent): void {
    const rect = this.minimap.getBoundingClientRect();
    const frac = (ev.clientX - rect.left) / rect.width;
    const { worldFrom, worldTo } = this.state;
    this.scrollToYear(worldFrom + frac * (worldTo - worldFrom));
    this.onState(this.state);
  }
}
