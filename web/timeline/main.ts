/// Entry point for timeline.html: reads the view state from the URL, wires
/// the toolbar and keeps the URL in sync so any view can be shared.

import { Api, type DomainSummary, type SourceSummary } from "./api";
import { colorFor, formatYear } from "./scale";
import { type Anchor, TimelineView, type ViewState } from "./view";

const DEFAULTS = {
  worldFrom: -500,
  worldTo: 2030,
  pxPerYear: 6,
  center: 1960,
};

interface Controls {
  from: HTMLInputElement;
  to: HTMLInputElement;
  q: HTMLInputElement;
  categories: HTMLInputElement;
  goto: HTMLInputElement;
  sources: HTMLElement;
  anchor: HTMLElement;
  zoomIn: HTMLButtonElement;
  zoomOut: HTMLButtonElement;
}

function num(v: string | null, fallback: number): number {
  const n = Number(v);
  return v !== null && v !== "" && Number.isFinite(n) ? n : fallback;
}

function parseAnchor(v: string | null): Anchor | null {
  if (v === null) {
    return null;
  }
  const m = /^(-?\d+):(.*)$/.exec(v);
  return m ? { year: Number(m[1]), name: m[2] ?? "" } : null;
}

export function stateFromUrl(search: string): ViewState & { center: number } {
  const p = new URLSearchParams(search);
  const worldFrom = num(p.get("from"), DEFAULTS.worldFrom);
  const worldTo = Math.max(worldFrom + 1, num(p.get("to"), DEFAULTS.worldTo));
  return {
    worldFrom,
    worldTo,
    pxPerYear: num(p.get("zoom"), DEFAULTS.pxPerYear),
    sources: (p.get("source") ?? "").split(",").filter(Boolean),
    q: p.get("q") ?? "",
    categories: (p.get("category") ?? "").split(",").filter(Boolean),
    kinds: (p.get("kind") ?? "").split(",").filter(Boolean),
    anchor: parseAnchor(p.get("anchor")),
    center: num(p.get("at"), DEFAULTS.center),
  };
}

export function urlFromState(s: ViewState, center: number): string {
  const p = new URLSearchParams();
  if (s.worldFrom !== DEFAULTS.worldFrom) {
    p.set("from", String(s.worldFrom));
  }
  if (s.worldTo !== DEFAULTS.worldTo) {
    p.set("to", String(s.worldTo));
  }
  p.set("zoom", s.pxPerYear.toPrecision(3));
  p.set("at", String(Math.round(center)));
  if (s.sources.length > 0) {
    p.set("source", s.sources.join(","));
  }
  if (s.q) {
    p.set("q", s.q);
  }
  if (s.categories.length > 0) {
    p.set("category", s.categories.join(","));
  }
  if (s.kinds.length > 0) {
    p.set("kind", s.kinds.join(","));
  }
  if (s.anchor !== null) {
    p.set("anchor", `${s.anchor.year}:${s.anchor.name}`);
  }
  return `?${p.toString()}`;
}

function controls(): Controls | null {
  const get = <T extends HTMLElement>(id: string) =>
    document.getElementById(id) as T | null;
  const from = get<HTMLInputElement>("tl-from");
  const to = get<HTMLInputElement>("tl-to");
  const q = get<HTMLInputElement>("tl-q");
  const categories = get<HTMLInputElement>("tl-category");
  const goto = get<HTMLInputElement>("tl-goto");
  const sources = get<HTMLElement>("tl-sources");
  const anchor = get<HTMLElement>("tl-anchor");
  const zoomIn = get<HTMLButtonElement>("tl-zoom-in");
  const zoomOut = get<HTMLButtonElement>("tl-zoom-out");
  if (
    !from ||
    !to ||
    !q ||
    !categories ||
    !goto ||
    !sources ||
    !anchor ||
    !zoomIn ||
    !zoomOut
  ) {
    return null;
  }
  return { from, to, q, categories, goto, sources, anchor, zoomIn, zoomOut };
}

function renderSourceToggles(
  box: HTMLElement,
  sources: SourceSummary[],
  enabled: string[],
  onChange: (slugs: string[]) => void,
): void {
  box.innerHTML = "";
  sources.forEach((s, i) => {
    const label = document.createElement("label");
    label.className = "tl-toggle";
    label.style.setProperty("--band", colorFor(i));
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = s.slug;
    input.checked = enabled.length === 0 || enabled.includes(s.slug);
    input.addEventListener("change", () => {
      const checked = [...box.querySelectorAll<HTMLInputElement>("input")]
        .filter((c) => c.checked)
        .map((c) => c.value);
      onChange(checked.length === sources.length ? [] : checked);
    });
    label.append(input, ` ${s.name}`);
    const count = document.createElement("small");
    count.textContent = ` ${s.events.toLocaleString()}`;
    label.append(count);
    box.appendChild(label);
  });
}

/// Domain chips: one click sets the domain's categories and kinds as the
/// filter, a second click on the active chip clears it.
function renderDomainChips(
  box: HTMLElement,
  domains: DomainSummary[],
  current: () => ViewState,
  apply: (patch: Partial<ViewState>) => void,
): void {
  box.innerHTML = "";
  const sameSet = (a: string[], b: string[]) =>
    a.length === b.length && a.every((x) => b.includes(x));
  const chips: { chip: HTMLButtonElement; d: DomainSummary }[] = [];
  const refresh = () => {
    const s = current();
    for (const { chip, d } of chips) {
      chip.classList.toggle(
        "active",
        sameSet(s.categories, d.categories) && sameSet(s.kinds, d.kinds),
      );
    }
  };
  for (const d of domains) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = `chip${d.events === 0 ? " muted" : ""}`;
    chip.textContent = d.name;
    chip.title = d.events
      ? `${d.events.toLocaleString()} events`
      : "Planned, no events yet";
    chip.addEventListener("click", () => {
      const active = chip.classList.contains("active");
      apply(
        active
          ? { categories: [], kinds: [] }
          : { categories: d.categories, kinds: d.kinds },
      );
      refresh();
    });
    chips.push({ chip, d });
    box.appendChild(chip);
  }
  refresh();
}

function renderAnchor(
  box: HTMLElement,
  anchor: Anchor | null,
  clear: () => void,
) {
  box.innerHTML = "";
  if (anchor === null) {
    box.hidden = true;
    return;
  }
  box.hidden = false;
  box.append(`Comparing from ${anchor.name} (${formatYear(anchor.year)}) `);
  const btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = "clear";
  btn.addEventListener("click", clear);
  box.appendChild(btn);
}

export async function mountTimeline(root: HTMLElement): Promise<void> {
  const api = new Api();
  const ui = controls();
  const initial = stateFromUrl(window.location.search);
  const { center, ...state } = initial;
  let lastUrl = "";
  const view = new TimelineView(root, api, state, (s) => {
    const url = urlFromState(s, view.centerYear());
    if (url !== lastUrl) {
      lastUrl = url;
      history.replaceState(null, "", url);
    }
    if (ui) {
      renderAnchor(ui.anchor, s.anchor, () => view.setState({ anchor: null }));
    }
  });

  let sources: SourceSummary[] = [];
  try {
    sources = (await api.sources()).sources.filter((s) => s.events > 0);
  } catch (err) {
    root.textContent = "Could not load the data sources.";
    console.error(err);
    return;
  }

  if (ui) {
    ui.from.value = String(state.worldFrom);
    ui.to.value = String(state.worldTo);
    ui.q.value = state.q;
    ui.categories.value = state.categories.join(", ");
    renderSourceToggles(ui.sources, sources, state.sources, (slugs) =>
      view.setState({ sources: slugs }),
    );
    renderAnchor(ui.anchor, state.anchor, () =>
      view.setState({ anchor: null }),
    );

    const applyWorld = () => {
      const worldFrom = num(ui.from.value, DEFAULTS.worldFrom);
      const worldTo = Math.max(
        worldFrom + 1,
        num(ui.to.value, DEFAULTS.worldTo),
      );
      view.setState({ worldFrom, worldTo });
    };
    ui.from.addEventListener("change", applyWorld);
    ui.to.addEventListener("change", applyWorld);
    let debounce = 0;
    ui.q.addEventListener("input", () => {
      window.clearTimeout(debounce);
      debounce = window.setTimeout(() => view.setState({ q: ui.q.value }), 350);
    });
    ui.categories.addEventListener("change", () =>
      view.setState({
        categories: ui.categories.value
          .split(",")
          .map((c) => c.trim())
          .filter(Boolean),
      }),
    );
    const domainBox = document.getElementById("tl-domains");
    if (domainBox !== null) {
      api
        .domains()
        .then(({ domains }) =>
          renderDomainChips(
            domainBox,
            domains,
            () => view.current,
            (patch) => {
              view.setState(patch);
              ui.categories.value = view.current.categories.join(", ");
            },
          ),
        )
        .catch((err: unknown) => console.error("domains failed", err));
    }
    ui.goto.addEventListener("change", () => {
      const year = Number(ui.goto.value);
      if (Number.isFinite(year)) {
        view.scrollToYear(year);
      }
    });
    ui.zoomIn.addEventListener("click", () => view.zoomBy(2));
    ui.zoomOut.addEventListener("click", () => view.zoomBy(0.5));
    document.addEventListener("keydown", (ev) => {
      if ((ev.target as HTMLElement).tagName === "INPUT") {
        return;
      }
      if (ev.key === "+" || ev.key === "=") {
        view.zoomBy(2);
      } else if (ev.key === "-") {
        view.zoomBy(0.5);
      }
    });
  }

  await view.mount(sources, center);
}

const root = document.getElementById("timeline");
if (root !== null) {
  mountTimeline(root).catch((err: unknown) => console.error(err));
}
