/// A small template engine covering what the templates use: Jinja-style
/// `{% extends "x" %}`, `{% block name %}...{% endblock %}` and `{{ var }}`.
/// Blocks are not nested; a child's block replaces the parent's.

export type Loader = (name: string) => string;

const EXTENDS = /^\s*{%\s*extends\s+["']([^"']+)["']\s*%}/;
const BLOCK = /{%\s*block\s+(\w+)\s*%}([\s\S]*?){%\s*endblock\s*%}/g;
const VARIABLE = /{{\s*(\w+)\s*}}/g;

/// Collect the blocks a template defines, in source order.
export function parseBlocks(text: string): Map<string, string> {
  const blocks = new Map<string, string>();
  for (const m of text.matchAll(BLOCK)) {
    const name = m[1] ?? "";
    const body = m[2] ?? "";
    if (blocks.has(name)) {
      throw new Error(`block "${name}" defined twice`);
    }
    blocks.set(name, body);
  }
  return blocks;
}

/// Render `name`, resolving its inheritance chain through `load`.
export function render(
  name: string,
  load: Loader,
  data: Record<string, string> = {},
): string {
  return substitute(resolve(name, load, new Map(), [name]), data);
}

function resolve(
  name: string,
  load: Loader,
  overrides: Map<string, string>,
  chain: string[],
): string {
  const text = load(name);
  const own = parseBlocks(text);
  // Child definitions win over this template's own.
  const merged = new Map<string, string>(own);
  for (const [k, v] of overrides) {
    merged.set(k, v);
  }

  const parent = text.match(EXTENDS)?.[1];
  if (parent !== undefined) {
    if (chain.includes(parent)) {
      throw new Error(
        `template inheritance cycle: ${[...chain, parent].join(" -> ")}`,
      );
    }
    return resolve(parent, load, merged, [...chain, parent]);
  }

  // Root template: emit each block's final body in place of the block tags.
  return text.replace(
    BLOCK,
    (_m, blockName: string, body: string) => merged.get(blockName) ?? body,
  );
}

function substitute(text: string, data: Record<string, string>): string {
  return text.replace(VARIABLE, (m, key: string) =>
    Object.hasOwn(data, key) ? (data[key] ?? "") : m,
  );
}
