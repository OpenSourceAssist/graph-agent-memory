/**
 * Unit tests — snake_case ↔ camelCase translation.
 */

import { describe, it, expect } from "vitest";
import { camelToSnake, snakeToCamel } from "../../src/transport/casing.js";

describe("snakeToCamel", () => {
  it("converts top-level keys", () => {
    expect(snakeToCamel({ user_id: "x" })).toEqual({ userId: "x" });
  });

  it("leaves camelCase unchanged", () => {
    expect(snakeToCamel({ userId: "x" })).toEqual({ userId: "x" });
  });

  it("handles nested objects", () => {
    expect(snakeToCamel({ outer_key: { inner_key: 1 } })).toEqual({
      outerKey: { innerKey: 1 },
    });
  });

  it("handles arrays of objects", () => {
    expect(snakeToCamel([{ a_b: 1 }, { c_d: 2 }])).toEqual([
      { aB: 1 },
      { cD: 2 },
    ]);
  });

  it("returns primitives unchanged", () => {
    expect(snakeToCamel("hello")).toBe("hello");
    expect(snakeToCamel(42)).toBe(42);
    expect(snakeToCamel(null)).toBeNull();
    expect(snakeToCamel(true)).toBe(true);
  });

  it("handles empty objects and arrays", () => {
    expect(snakeToCamel({})).toEqual({});
    expect(snakeToCamel([])).toEqual([]);
  });
});

describe("camelToSnake", () => {
  it("converts top-level keys", () => {
    expect(camelToSnake({ userId: "x" })).toEqual({ user_id: "x" });
  });

  it("leaves snake_case unchanged", () => {
    expect(camelToSnake({ user_id: "x" })).toEqual({ user_id: "x" });
  });

  it("handles nested objects", () => {
    expect(camelToSnake({ outerKey: { innerKey: 1 } })).toEqual({
      outer_key: { inner_key: 1 },
    });
  });

  it("handles arrays", () => {
    expect(camelToSnake([{ aB: 1 }])).toEqual([{ a_b: 1 }]);
  });

  it("roundtrips snake → camel → snake", () => {
    const original = { user_id: "alice", metadata: { is_active: true, tags: ["a", "b"] } };
    expect(camelToSnake(snakeToCamel(original))).toEqual(original);
  });
});

describe("caller data under metadata and properties", () => {
  const data = { namsKind: "tool-call", source_app: "web", nested: { innerKey: 1, outer_key: 2 } };

  it("is sent as written", () => {
    expect(snakeToCamel({ user_id: "u", metadata: data, properties: data })).toEqual({
      userId: "u", metadata: data, properties: data,
    });
    expect(snakeToCamel({ messages: [{ message_id: "m", metadata: data }] })).toEqual({
      messages: [{ messageId: "m", metadata: data }],
    });
  });

  it("is read back as written", () => {
    expect(camelToSnake({ createdAt: "t", metadata: data, properties: data })).toEqual({
      created_at: "t", metadata: data, properties: data,
    });
  });

  it("still converts a properties list, which is wire structure", () => {
    expect(camelToSnake({ properties: [{ isRequired: true }] })).toEqual({
      properties: [{ is_required: true }],
    });
  });
});
