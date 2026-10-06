import { parseBlocks, render } from "../templates";

const files: Record<string, string> = {
  "_base.html": `<title>{% block title %}Default{% endblock %}</title>
<main>{% block content %}{% endblock %}</main>
{% block scripts %}{% endblock %}`,
  "page.html": `{% extends "_base.html" %}
{% block title %}Page{% endblock %}
{% block content %}<p>Hello {{ name }}</p>{% endblock %}`,
  "grandchild.html": `{% extends "page.html" %}
{% block scripts %}<script></script>{% endblock %}`,
  "loop.html": `{% extends "loop.html" %}`,
};

const load = (name: string): string => {
  const text = files[name];
  if (text === undefined) {
    throw new Error(`missing ${name}`);
  }
  return text;
};

describe("render", () => {
  it("fills parent blocks with the child's and keeps parent defaults", () => {
    const html = render("page.html", load, { name: "World" });
    expect(html).toBe(`<title>Page</title>
<main><p>Hello World</p></main>
`);
  });

  it("resolves multi-level inheritance with the nearest definition winning", () => {
    const html = render("grandchild.html", load);
    expect(html).toContain("<title>Page</title>");
    expect(html).toContain("<script></script>");
    expect(html).toContain("<p>Hello {{ name }}</p>");
  });

  it("leaves no template tags behind", () => {
    const html = render("grandchild.html", load, { name: "x" });
    expect(html).not.toMatch(/{%|%}/);
  });

  it("rejects inheritance cycles", () => {
    expect(() => render("loop.html", load)).toThrow(/cycle/);
  });
});

describe("parseBlocks", () => {
  it("collects blocks by name and rejects duplicates", () => {
    expect([...parseBlocks(files["_base.html"] ?? "").keys()]).toEqual([
      "title",
      "content",
      "scripts",
    ]);
    expect(() =>
      parseBlocks("{% block a %}{% endblock %}{% block a %}{% endblock %}"),
    ).toThrow(/twice/);
  });
});
