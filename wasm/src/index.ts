/// TrailBase WASM component: every custom HTTP endpoint of the app.
///
/// Built with `yarn wasm:build` (Vite bundle, then `jco componentize`) into
/// `traildepot/wasm/component.wasm`, which TrailBase loads at startup. Adding
/// or removing routes needs a server restart; changing a handler body only
/// needs a rebuild plus SIGHUP.

import { defineConfig } from "trailbase-wasm";
import { domainHandlers } from "./domains";
import { searchHandlers } from "./search";
import { timelineHandlers } from "./timeline";

export const { initEndpoint, incomingHandler, sqliteFunctionEndpoint } =
  defineConfig({
    httpHandlers: [...searchHandlers, ...timelineHandlers, ...domainHandlers],
  });
