import { query } from "trailbase-wasm/db";
import { HttpHandler, HttpResponse } from "trailbase-wasm/http";
import { num, type Params, str } from "./values";

/// Domains: the handful of top-level views the site navigates by.
///
/// Event categories are fine-grained (a MusicBrainz release is "music", a
/// Wikidata life is one of nine thousand occupations), so the pages group
/// them into domains defined here. A domain lists the categories and event
/// kinds that belong to it, the sources it draws on, and what is planned but
/// not ingested yet. `GET /timeline/domains` returns every domain with live
/// counts from `event_density`, so a category with no data yet shows up as a
/// stub rather than disappearing.

export interface Domain {
  slug: string;
  name: string;
  blurb: string;
  /// Event categories (`events.category`) that belong here.
  categories: string[];
  /// Event kinds (`events.kind`) that belong here regardless of category.
  kinds: string[];
  /// Source slugs that feed this domain today.
  sources: string[];
  /// Data that would fill the domain, not ingested yet.
  planned: string[];
}

export const DOMAINS: Domain[] = [
  {
    slug: "film",
    name: "Film, TV & games",
    blurb:
      "Film and series releases from IMDB, game releases from Steam, and the lives of the people who made them.",
    categories: [
      "film",
      "television",
      "short",
      "video",
      "videogame",
      "actor",
      "actress",
      "director",
      "producer",
      "writer",
      "cinematographer",
      "composer",
      "editor",
      "film director",
      "film producer",
      "film actor",
      "television actor",
      "television presenter",
      "animator",
      "screenwriter",
    ],
    kinds: [],
    sources: ["imdb", "steam"],
    planned: [
      "Full IMDB import: TV series, mini-series and episodes (make import-data)",
      "Wikidata films and series with publication dates (P577)",
    ],
  },
  {
    slug: "music",
    name: "Music",
    blurb:
      "Every official release in MusicBrainz, placed on the day it came out, plus the lives of musicians.",
    categories: [
      "music",
      "musician",
      "singer",
      "composer",
      "pianist",
      "conductor",
      "songwriter",
      "guitarist",
      "drummer",
      "violinist",
      "organist",
      "opera singer",
      "rapper",
      "disc jockey",
      "record producer",
      "jazz musician",
      "singer-songwriter",
      "bandleader",
    ],
    kinds: [],
    sources: ["musicbrainz"],
    planned: [
      "Billboard and UK chart entries",
      "Concerts and tours (setlist.fm)",
      "Wikidata musical works and albums",
    ],
  },
  {
    slug: "sports",
    name: "Sports",
    blurb:
      "Games, seasons, drafts and careers: baseball since 1871, the NBA, MLS, international cricket and every Olympic Games.",
    categories: [
      "baseball",
      "basketball",
      "athlete",
      "olympics",
      "soccer",
      "cricket",
      "football",
      "association football player",
      "American football player",
      "cricketer",
      "swimmer",
      "boxer",
      "cyclist",
      "tennis player",
      "racing driver",
      "sport shooter",
      "gymnast",
      "ice hockey player",
      "rower",
      "fencer",
      "amateur wrestler",
      "sprinter",
      "golfer",
      "rugby union player",
      "chess player",
    ],
    kinds: ["game", "draft", "all_star", "championship", "medal", "competed"],
    sources: ["lahman", "nba", "olympics", "cricket", "mls"],
    planned: [
      "Tennis, Formula 1 and football league results",
      "World Cups and championships from Wikidata",
    ],
  },
  {
    slug: "books",
    name: "Books & writing",
    blurb:
      "Books and articles with their year of publication, from the Book-Crossing catalogue and Wikipedia bibliographies, and the writers behind them.",
    categories: [
      "book",
      "article",
      "publication",
      "author",
      "novelist",
      "writer",
      "poet",
      "playwright",
      "essayist",
      "literary critic",
      "translator",
      "publisher",
      "librarian",
      "historian",
      "journalist",
      "children's writer",
      "science fiction writer",
    ],
    kinds: ["publication"],
    sources: ["bx_books", "wikipedia_lists"],
    planned: [
      "More Wikipedia bibliographies (make wikipedia-lists SEEDS=...)",
      "Wikidata written works with publication dates (P577)",
      "Open Library editions",
    ],
  },
  {
    slug: "awards",
    name: "Awards & honours",
    blurb:
      "Prizes, all-star selections, hall of fame inductions and championships across every domain.",
    categories: ["award", "prize"],
    kinds: ["award", "hall_of_fame", "all_star", "championship"],
    sources: ["lahman", "nba"],
    planned: [
      "Wikidata awards received (P166): Nobel Prizes, Academy Awards, Grammys",
      "Hall of fame inductions outside baseball",
    ],
  },
  {
    slug: "science",
    name: "Science & medicine",
    blurb:
      "Researchers, physicians, engineers and inventors, with discoveries and publications to come.",
    categories: [
      "researcher",
      "astronomer",
      "physician",
      "engineer",
      "surgeon",
      "inventor",
      "psychologist",
      "psychiatrist",
      "geographer",
      "biologist",
      "mathematician",
      "physicist",
      "chemist",
      "botanist",
      "zoologist",
      "geologist",
      "computer scientist",
      "economist",
      "archaeologist",
      "linguist",
      "philosopher",
      "scientist",
      "pharmacist",
      "university teacher",
    ],
    kinds: [],
    sources: ["wikidata_age"],
    planned: [
      "Discoveries, inventions and expeditions with dates (Wikidata inception, P575 time of discovery)",
      "Scientific instruments and missions (telescopes, spacecraft)",
    ],
  },
  {
    slug: "politics",
    name: "Politics & government",
    blurb:
      "Politicians, judges, ministers and monarchs; terms of office and elections are planned.",
    categories: [
      "politician",
      "diplomat",
      "judge",
      "jurist",
      "lawyer",
      "minister",
      "monarch",
      "head of state",
      "mayor",
      "governor",
      "senator",
      "revolutionary",
      "civil servant",
      "official",
      "trade unionist",
      "activist",
      "political scientist",
    ],
    kinds: [],
    sources: ["wikidata_age"],
    planned: [
      "Positions held with start and end dates (Wikidata P39)",
      "Elections, treaties and constitutions",
      "Countries, empires and states with inception and dissolution",
    ],
  },
  {
    slug: "conflict",
    name: "Wars & conflicts",
    blurb:
      "Wars, battles and the people who fought them. Conflicts themselves arrive with the Wikidata dump.",
    categories: [
      "war",
      "battle",
      "conflict",
      "military personnel",
      "naval officer",
      "soldier",
      "military officer",
      "general",
      "admiral",
      "resistance fighter",
      "aviator",
      "spy",
    ],
    kinds: [],
    sources: ["wikidata_age"],
    planned: [
      "Wars, battles, sieges and revolutions (wikidata adapter, classes Q198, Q178561, …)",
      "Participants of each conflict (Wikidata P710, P607)",
    ],
  },
  {
    slug: "religion",
    name: "Religion",
    blurb: "Clergy, scholars and founders across traditions.",
    categories: [
      "religious figure",
      "pastor",
      "priest",
      "rabbi",
      "bishop",
      "theologian",
      "missionary",
      "cardinal",
      "pope",
      "imam",
      "monk",
      "nun",
      "saint",
      "Catholic priest",
    ],
    kinds: [],
    sources: ["wikidata_age"],
    planned: ["Councils, schisms and foundations of religious orders"],
  },
  {
    slug: "business",
    name: "Business & economy",
    blurb:
      "Entrepreneurs, merchants and bankers; companies and products are planned.",
    categories: [
      "businessperson",
      "entrepreneur",
      "merchant",
      "banker",
      "industrialist",
      "economist",
      "publisher",
      "manager",
      "business executive",
    ],
    kinds: [],
    sources: ["wikidata_age"],
    planned: [
      "Company foundings and dissolutions (Wikidata inception)",
      "Product launches and stock listings",
    ],
  },
  {
    slug: "arts",
    name: "Art & architecture",
    blurb:
      "Painters, sculptors, architects and photographers, starting with the lives of 421 famous painters.",
    categories: [
      "artist",
      "painter",
      "sculptor",
      "architect",
      "photographer",
      "illustrator",
      "designer",
      "graphic artist",
      "printmaker",
      "ceramicist",
      "art historian",
      "fashion designer",
      "cartoonist",
    ],
    kinds: [],
    sources: ["wikidata_age", "paintings"],
    planned: [
      "Artworks and buildings with completion dates (Wikidata inception)",
      "Exhibitions and museum foundings",
    ],
  },
  {
    slug: "exploration",
    name: "Exploration & space",
    blurb:
      "Explorers, aviators and astronauts; expeditions and launches to come.",
    categories: [
      "explorer",
      "astronaut",
      "aviator",
      "mountaineer",
      "navigator",
      "sailor",
      "cosmonaut",
      "test pilot",
      "polar explorer",
    ],
    kinds: [],
    sources: ["wikidata_age"],
    planned: [
      "Spaceflight launches and missions",
      "Voyages and expeditions with departure and return dates",
    ],
  },
  {
    slug: "lives",
    name: "Lives",
    blurb:
      "Everyone else: 1.2 million notable people from Wikidata with birth and death years.",
    categories: [
      "person",
      "aristocrat",
      "teacher",
      "farmer",
      "police officer",
      "model",
      "chef",
      "nurse",
      "social worker",
    ],
    kinds: [],
    sources: ["wikidata_age"],
    planned: ["Every human in the Wikidata dump (wikidata adapter)"],
  },
  {
    slug: "lists",
    name: "Wikipedia lists",
    blurb:
      "Every dated line of a Wikipedia list page that is not a publication: a stub event per entry, to be refined list by list.",
    categories: ["list entry", "dated"],
    kinds: ["listed"],
    sources: ["wikipedia_lists"],
    planned: [
      'More list pages (make wikipedia-lists SEEDS="List of treaties" ...)',
      "Every Wikidata item with a calendar date (wikidata_extract.py --all-dated)",
      "Per-list parsers that turn stub entries into typed events",
    ],
  },
];

export interface DomainSummary extends Domain {
  events: number;
  firstYear: number | null;
  lastYear: number | null;
  /// Each of the domain's categories with its event count, zero for stubs.
  categoryCounts: { category: string; events: number }[];
}

function placeholders(n: number): string {
  return Array.from({ length: n }, () => "?").join(", ");
}

/// Counts per category for one domain, from the small density table.
export function buildDomainCategoriesQuery(categories: string[]): {
  sql: string;
  params: unknown[];
} {
  const sql = `
    SELECT category, sum(count), min(year), max(year)
      FROM event_density
     WHERE category IN (${placeholders(categories.length)})
     GROUP BY category
     ORDER BY 2 DESC`;
  return { sql, params: [...categories] };
}

/// Kind-based membership (an award in the baseball category) walks the
/// `events_by_kind` index; the kinds listed here are rare ones, so this
/// stays cheap.
export function buildDomainKindsQuery(kinds: string[]): {
  sql: string;
  params: unknown[];
} {
  const sql = `
    SELECT count(*), min(start_year), max(start_year)
      FROM events
     WHERE kind IN (${placeholders(kinds.length)})`;
  return { sql, params: [...kinds] };
}

function minYear(a: number | null, b: number | null): number | null {
  return a === null ? b : b === null ? a : Math.min(a, b);
}

function maxYear(a: number | null, b: number | null): number | null {
  return a === null ? b : b === null ? a : Math.max(a, b);
}

export async function summarize(domain: Domain): Promise<DomainSummary> {
  const counts = new Map<string, number>();
  let events = 0;
  let firstYear: number | null = null;
  let lastYear: number | null = null;
  if (domain.categories.length > 0) {
    const q = buildDomainCategoriesQuery(domain.categories);
    for (const r of await query(q.sql, q.params as Params)) {
      const n = num(r[1]) ?? 0;
      counts.set(str(r[0]) ?? "", n);
      events += n;
      firstYear = minYear(firstYear, num(r[2]));
      lastYear = maxYear(lastYear, num(r[3]));
    }
  }
  // Kind rows may overlap category rows (a baseball award is both), so the
  // total is a ceiling, which is fine for a card.
  if (domain.kinds.length > 0) {
    const q = buildDomainKindsQuery(domain.kinds);
    const r = (await query(q.sql, q.params as Params))[0];
    if (r) {
      events += num(r[0]) ?? 0;
      firstYear = minYear(firstYear, num(r[1]));
      lastYear = maxYear(lastYear, num(r[2]));
    }
  }
  return {
    ...domain,
    events,
    firstYear,
    lastYear,
    categoryCounts: domain.categories.map((category) => ({
      category,
      events: counts.get(category) ?? 0,
    })),
  };
}

export async function domains(): Promise<object> {
  try {
    const out: DomainSummary[] = [];
    for (const d of DOMAINS) {
      out.push(await summarize(d));
    }
    return { domains: out };
  } catch (error) {
    console.error("[DOMAINS] query failed:", error);
    return { domains: [], error: "Domains query failed" };
  }
}

export const domainHandlers = [
  HttpHandler.get("/timeline/domains", async () =>
    HttpResponse.json(await domains()),
  ),
];
