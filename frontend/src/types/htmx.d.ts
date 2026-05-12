/**
 * Minimal ambient types for htmx.org's window-level surface area.
 *
 * htmx is loaded as an ES module side-effect and pins itself to `window.htmx`.
 * The official htmx.org package ships only minimal types, so we declare the
 * surface we actually use.
 */

declare module "htmx.org";

interface HtmxConfig {
  defaultSwapStyle: string;
  includeIndicatorStyles: boolean;
  scrollIntoViewOnBoost: boolean;
  historyCacheSize: number;
  allowEval: boolean;
  allowScriptTags: boolean;
}

interface HtmxApi {
  config: HtmxConfig;
}

interface Window {
  htmx: HtmxApi;
}

interface HtmxConfigRequestEvent extends CustomEvent {
  detail: {
    verb: string;
    headers: Record<string, string>;
  };
}

interface HtmxResponseErrorEvent extends CustomEvent {
  detail: {
    xhr: XMLHttpRequest;
  };
}