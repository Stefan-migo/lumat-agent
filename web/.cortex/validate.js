'use strict';

// Cortex canonical validator (AD-7: one validator at write AND bootstrap).
// Node stdlib only (AD-2). Throws Error naming the offending field; never writes
// an invalid artifact (DC-001). Object-form variants required (DC-004/DC-005).
const fs = require('node:fs');
const path = require('node:path');

// Shape -> required field -> expected JS type. Missing or mistyped field is
// reported by name. `id` is required on every contract (DC-001).
const CONTRACT_FIELDS = {
  profile: {
    id: 'string', stack: 'string', presentColors: 'object',
    presentTypography: 'array', existingTokens: 'object', notes: 'array'
  },
  intent: {
    id: 'string', brief: 'string', derivedTokens: 'array',
    constraints: 'array', notes: 'array'
  },
  matrix: {
    id: 'string', preservedTokens: 'array', preservedColors: 'array',
    preservedBehaviors: 'array', dropped: 'array'
  },
  visual: { id: 'string', notes: 'array' }
};

// Pick the contract shape by its discriminating fields (mutually exclusive).
function contractShape(data) {
  if ('preservedTokens' in data || 'dropped' in data) return 'matrix';
  if ('brief' in data || 'derivedTokens' in data) return 'intent';
  if ('presentColors' in data || 'stack' in data) return 'profile';
  return 'visual';
}

function typeOf(v) {
  if (Array.isArray(v)) return 'array';
  return typeof v;
}

function validate(data) {
  if (data === null || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error('not a valid Cortex artifact: must be an object');
  }
  // Catalog (DC-004): version + components[]; each component needs id + adaptationRules.
  if ('components' in data || 'version' in data) {
    if (typeof data.version !== 'string') throw new Error('version must be a string');
    if (!Array.isArray(data.components)) throw new Error('components must be an array');
    for (const comp of data.components) validateComponent(comp);
    return;
  }
  // Domain contract (DC-001..DC-003).
  const shape = contractShape(data);
  const rules = CONTRACT_FIELDS[shape];
  for (const [field, type] of Object.entries(rules)) {
    if (!(field in data)) throw new Error(`${field} is required (missing field)`);
    if (type !== 'object' && typeOf(data[field]) !== type) {
      throw new Error(`${field} must be a ${type}`);
    }
  }
  if (shape === 'matrix') {
    for (const d of data.dropped) {
      if (d === null || typeof d !== 'object' || typeof d.reason !== 'string') {
        throw new Error('dropped must be an array of objects with a reason string (CP-005)');
      }
    }
  }
}

function validateComponent(comp) {
  if (comp === null || typeof comp !== 'object') throw new Error('component must be an object');
  if (typeof comp.id !== 'string') throw new Error('component.id is required');
  if (comp.storyFile !== undefined && comp.storyFile !== null && typeof comp.storyFile !== 'string') {
    throw new Error('storyFile must be a string or null');
  }
  const ar = comp.adaptationRules;
  if (ar === null || typeof ar !== 'object') {
    throw new Error('component.adaptationRules is required (missing field)');
  }
  if (Array.isArray(ar.variants)) {
    throw new Error('variants must be an object map of variant name to prop override, not an array (DC-004)');
  }
  if (ar.variants !== undefined && ar.variants !== null && typeof ar.variants !== 'object') {
    throw new Error('variants must be an object map of variant name to prop override (DC-004)');
  }
  for (const [f, type] of [['tokenSlots', 'array'], ['defaultProps', 'object'], ['defaults', 'object']]) {
    if (ar[f] !== undefined && typeOf(ar[f]) !== type) throw new Error(`adaptationRules.${f} must be a ${type}`);
  }
}

// Write-time entry (DC-001): only writes when valid; throws named-field error.
function write(contractPath, data) {
  validate(data);
  fs.mkdirSync(path.dirname(contractPath), { recursive: true });
  fs.writeFileSync(contractPath, `${JSON.stringify(data, null, 2)}\n`);
}

module.exports = { validate, write, validateComponent };
