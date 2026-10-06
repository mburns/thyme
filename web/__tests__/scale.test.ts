import {
  densityBucket,
  floorTo,
  formatYear,
  fractionalYear,
  labelWidth,
  majorStep,
  packLanes,
  ticksFor,
  tierFor,
  tilesFor,
} from "../timeline/scale";

describe("tierFor", () => {
  it("coarsens the LOD bucket as pixels per year shrink", () => {
    expect(tierFor(0.5)).toMatchObject({ kind: "overview", bucket: 100 });
    expect(tierFor(4)).toMatchObject({ kind: "overview", bucket: 10 });
    expect(tierFor(40)).toMatchObject({ kind: "overview", bucket: 1 });
    expect(tierFor(200)).toMatchObject({ kind: "detail", tileYears: 10 });
  });
});

describe("floorTo and tilesFor", () => {
  it("floors negative years towards minus infinity", () => {
    expect(floorTo(-1, 10)).toBe(-10);
    expect(floorTo(-10, 10)).toBe(-10);
    expect(floorTo(1999, 100)).toBe(1900);
  });

  it("covers the range with aligned tiles", () => {
    expect(tilesFor(1995, 2012, 10)).toEqual([1990, 2000, 2010]);
    expect(tilesFor(-5, 5, 10)).toEqual([-10, 0]);
  });
});

describe("ticks", () => {
  it("spaces labelled ticks at least 90px apart", () => {
    expect(majorStep(1)).toBe(100);
    expect(majorStep(10)).toBe(10);
    expect(majorStep(50)).toBe(2);
  });

  it("labels major ticks and formats BCE years", () => {
    const ticks = ticksFor(-20, 20, 10);
    const labelled = ticks.filter((t) => t.major).map((t) => t.label);
    expect(labelled).toEqual(["21 BCE", "11 BCE", "1 BCE", "10", "20"]);
    expect(ticks.filter((t) => !t.major).length).toBeGreaterThan(0);
    expect(formatYear(-720)).toBe("721 BCE");
  });
});

describe("packLanes", () => {
  it("reuses a lane once the previous item has ended", () => {
    const { placed, hidden } = packLanes(
      [
        { item: "a", x0: 0, x1: 50 },
        { item: "b", x0: 10, x1: 30 },
        { item: "c", x0: 60, x1: 80 },
      ],
      4,
    );
    expect(placed).toEqual([
      { item: "a", lane: 0 },
      { item: "b", lane: 1 },
      { item: "c", lane: 0 },
    ]);
    expect(hidden).toBe(0);
  });

  it("hides what does not fit in the lane budget", () => {
    const items = [0, 1, 2, 3].map((i) => ({ item: i, x0: 0, x1: 100 }));
    const { placed, hidden } = packLanes(items, 2);
    expect(placed.map((p) => p.item)).toEqual([0, 1]);
    expect(hidden).toBe(2);
  });
});

describe("helpers", () => {
  it("estimates label width and caps long labels", () => {
    expect(labelWidth("abc")).toBeCloseTo(3 * 6.4 + 12);
    expect(labelWidth("x".repeat(200))).toBe(labelWidth("x".repeat(48)));
  });

  it("spreads day-precision dates inside the year", () => {
    expect(fractionalYear("1969-07-20", 1969)).toBeCloseTo(1969.552, 2);
    expect(fractionalYear("1969", 1969)).toBe(1969);
    expect(fractionalYear("-0044-03-15", -44)).toBeCloseTo(-43.795, 2);
  });

  it("picks a density bucket that keeps the bar count bounded", () => {
    expect(densityBucket(300)).toBe(1);
    expect(densityBucket(2530)).toBe(10);
    expect(densityBucket(100000)).toBe(500);
  });
});
