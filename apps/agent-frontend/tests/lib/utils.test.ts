import { describe, it, expect } from "vitest";
import { cn } from "@/lib/utils";

describe("cn utility", () => {
  it("merges tailwind classes correctly", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("handles conditional classes", () => {
    const isActive = true;
    expect(cn("base", isActive && "active")).toBe("base active");
  });

  it("filters out falsy values", () => {
    expect(cn("base", false && "hidden", null, undefined, "show")).toBe("base show");
  });

  it("handles arrays of classes", () => {
    expect(cn(["a", "b"], "c")).toBe("a b c");
  });

  it("handles objects for conditional classes", () => {
    expect(cn({ "text-red-500": true, "text-blue-500": false })).toBe("text-red-500");
  });
});
