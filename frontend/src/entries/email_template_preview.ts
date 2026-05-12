/**
 * Email template preview entry (H.1.2).
 *
 * Used by the platform-console email preview screens. Email templates
 * are server-rendered HTML; this entry exists so previews can include
 * the same base styles when reviewed in a browser.
 *
 * Note: real email rendering (the bytes sent to clients) MUST NOT depend
 * on this bundle. Email is always inlined/static.
 */

import "../styles/_base.css";

// Intentionally empty body — preview pages need only the stylesheet.