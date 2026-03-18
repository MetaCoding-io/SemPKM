/**
 * Page data extractor — runs in the page's DOM context.
 *
 * This function is passed to chrome.scripting.executeScript({func: extractPageData}).
 * It MUST be completely self-contained: no imports, no closures, no references
 * to extension code. Chrome serializes/deserializes the function body.
 *
 * @returns {{ title: string|null, url: string, selectedText: string, author: string|null, description: string|null, schemaOrg: Array<Object> }}
 */
function extractPageData() {
  // ── Meta tag helpers ──────────────────────────────────────────

  function getMeta(nameOrProp) {
    const byName = document.querySelector(`meta[name="${nameOrProp}"]`);
    if (byName) return byName.getAttribute('content') || null;

    const byProp = document.querySelector(`meta[property="${nameOrProp}"]`);
    if (byProp) return byProp.getAttribute('content') || null;

    return null;
  }

  // ── Title ─────────────────────────────────────────────────────

  var title = getMeta('og:title')
    || getMeta('twitter:title')
    || document.title
    || null;

  // ── URL ───────────────────────────────────────────────────────

  var url = window.location.href;

  // ── Selected text ─────────────────────────────────────────────

  var sel = window.getSelection();
  var selectedText = sel ? sel.toString().trim() : '';

  // ── Author ────────────────────────────────────────────────────

  var author = getMeta('author') || getMeta('article:author') || null;

  // ── Description ───────────────────────────────────────────────

  var description = getMeta('description') || getMeta('og:description') || null;

  // ── Schema.org JSON-LD ────────────────────────────────────────

  function normalizeType(rawType) {
    if (!rawType) return null;
    if (Array.isArray(rawType)) {
      for (var i = 0; i < rawType.length; i++) {
        var t = normalizeType(rawType[i]);
        if (t) return t;
      }
      return null;
    }
    var s = String(rawType);
    s = s.replace('https://schema.org/', '')
         .replace('http://schema.org/', '')
         .replace('schema:', '');
    return s || null;
  }

  function extractEntities(obj, out) {
    if (!obj || typeof obj !== 'object') return;

    // Handle @graph arrays
    if (Array.isArray(obj)) {
      for (var i = 0; i < obj.length; i++) {
        extractEntities(obj[i], out);
      }
      return;
    }

    if (obj['@graph'] && Array.isArray(obj['@graph'])) {
      for (var g = 0; g < obj['@graph'].length; g++) {
        extractEntities(obj['@graph'][g], out);
      }
      return;
    }

    // This object is an entity if it has @type
    if (obj['@type']) {
      var normalized = Object.assign({}, obj);
      normalized['@type'] = normalizeType(obj['@type']);
      out.push(normalized);

      // Extract nested entities from property values
      var keys = Object.keys(obj);
      for (var k = 0; k < keys.length; k++) {
        var key = keys[k];
        if (key.charAt(0) === '@') continue; // skip @type, @id, @context
        var val = obj[key];
        if (val && typeof val === 'object' && !Array.isArray(val) && val['@type']) {
          extractEntities(val, out);
        }
        if (Array.isArray(val)) {
          for (var a = 0; a < val.length; a++) {
            if (val[a] && typeof val[a] === 'object' && val[a]['@type']) {
              extractEntities(val[a], out);
            }
          }
        }
      }
    }
  }

  var schemaOrg = [];
  var scripts = document.querySelectorAll('script[type="application/ld+json"]');

  for (var s = 0; s < scripts.length; s++) {
    try {
      var parsed = JSON.parse(scripts[s].textContent);
      extractEntities(parsed, schemaOrg);
    } catch (e) {
      // Skip invalid JSON-LD — caller logs this
    }
  }

  return {
    title: title,
    url: url,
    selectedText: selectedText,
    author: author,
    description: description,
    schemaOrg: schemaOrg,
  };
}
