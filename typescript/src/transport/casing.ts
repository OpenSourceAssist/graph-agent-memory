/**
 * snake_case ↔ camelCase translation for wire payloads.
 *
 * Keep deeply nested structures (arrays, objects, primitives) intact.
 * Pure helpers — no transport dependencies.
 */

const SNAKE_RE = /_([a-z0-9])/g;
const CAMEL_RE = /([A-Z])/g;

/**
 * Keys whose object value is the caller's own data, passed through as written.
 */
const KEYS = new Set(["metadata", "properties"]);

function snakeKey(key: string): string {
  return key.replace(CAMEL_RE, (_, c) => `_${(c as string).toLowerCase()}`);
}

function camelKey(key: string): string {
  return key.replace(SNAKE_RE, (_, c) => (c as string).toUpperCase());
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function convertKeys(value: unknown, convertKey: (key: string) => string): unknown {
  if (Array.isArray(value)) {
    return value.map((v) => convertKeys(v, convertKey));
  }
  if (isPlainObject(value)) {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
      out[convertKey(k)] = KEYS.has(k) && isPlainObject(v) ? v : convertKeys(v, convertKey);
    }
    return out;
  }
  return value;
}

export function snakeToCamel<T = unknown>(value: unknown): T {
  return convertKeys(value, camelKey) as T;
}

export function camelToSnake<T = unknown>(value: unknown): T {
  return convertKeys(value, snakeKey) as T;
}
