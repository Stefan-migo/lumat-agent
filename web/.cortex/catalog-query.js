// CA-001 catalog query (DC-004 canonical shape). Pure, no deps.
// Filters components by visualContext AND OR-moodTags; returns an empty array
// (never throws) when a visualContext no component declares is queried.
// One canonical source for the query used by component-adapter/design-agent
// skills and catalog consumers (CP-003).

/**
 * @param {object} catalog DC-004 catalog { version, components[] }
 * @param {{ visualContext?: string, moodTags?: string[] }} query
 * @returns {object[]} matching component objects
 */
export function queryComponents(catalog, query = {}) {
  if (!catalog || !Array.isArray(catalog.components)) return [];
  const context = query.visualContext;
  const tags = (query.moodTags || []).filter((t) => typeof t === 'string');
  return catalog.components.filter((comp) => {
    // visualContext must be declared by the component to match (CA-001).
    if (context && !(comp.visualContext || []).includes(context)) return false;
    // moodTags OR semantics within the set (CA-001: any matching tag suffices).
    if (tags.length && !(comp.moodTags || []).some((t) => tags.includes(t))) return false;
    return true;
  });
}
