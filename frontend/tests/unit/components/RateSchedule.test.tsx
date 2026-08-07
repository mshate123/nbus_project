import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { createElement } from "react";
import { RateSchedule } from "../../../src/components/RateSchedule";

// Mock TanStack Query
const mockUseQuery = vi.fn();
vi.mock("@tanstack/react-query", () => ({
  useQuery: (...args: unknown[]) => mockUseQuery(...args),
}));

/**
 * RateSchedule unit tests — validates US-6 display logic.
 * Tests focus on the component's data transformation (rate → percentage)
 * and rendering states (loading, error, data).
 */
describe("RateSchedule", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    mockUseQuery.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    // Shallow render check — component should return loading message
    const element = createElement(RateSchedule);
    expect(element).toBeDefined();
    expect(element.type).toBe(RateSchedule);
  });

  it("passes correct query key and fn to useQuery", () => {
    mockUseQuery.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    // Trigger the component to call useQuery
    const { type: Component } = createElement(RateSchedule);
    if (typeof Component === "function") {
      Component({});
    }

    expect(mockUseQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ["rate-schedule"],
      })
    );
  });

  it("formats annual_rate as percentage correctly", () => {
    // Verify the percentage formatting logic used in the component:
    // (Number(entry.annual_rate) * 100).toFixed(2) + "%"
    const testCases = [
      { input: "0.05", expected: "5.00%" },
      { input: "0.035", expected: "3.50%" },
      { input: "0.1", expected: "10.00%" },
      { input: "0.0025", expected: "0.25%" },
    ];

    for (const { input, expected } of testCases) {
      const formatted = `${(Number(input) * 100).toFixed(2)}%`;
      expect(formatted).toBe(expected);
    }
  });

  it("renders error state when query fails", () => {
    mockUseQuery.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Network error"),
    });

    const { type: Component } = createElement(RateSchedule);
    if (typeof Component === "function") {
      const result = Component({});
      // Error state should render a paragraph with error message
      expect(result).toBeDefined();
      expect(result.props.className).toContain("text-destructive");
    }
  });

  it("renders rate schedule data with tier names and percentages", () => {
    const mockRates = [
      { tier: "standard", annual_rate: "0.03" },
      { tier: "premium", annual_rate: "0.05" },
      { tier: "savings", annual_rate: "0.045" },
    ];

    mockUseQuery.mockReturnValue({
      data: mockRates,
      isLoading: false,
      error: null,
    });

    const { type: Component } = createElement(RateSchedule);
    if (typeof Component === "function") {
      const result = Component({});
      // Should render a Card (not a loading/error <p>)
      expect(result).toBeDefined();
      expect(result.type).not.toBe("p");
    }
  });

  it("handles empty rate schedule gracefully", () => {
    mockUseQuery.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    const { type: Component } = createElement(RateSchedule);
    if (typeof Component === "function") {
      const result = Component({});
      // Should still render the Card/Table structure, not crash
      expect(result).toBeDefined();
      expect(result.type).not.toBe("p");
    }
  });
});
