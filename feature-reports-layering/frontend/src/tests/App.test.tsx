import { describe, it, expect, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import { ReportRenderer } from "../components/reports/ReportRenderer";
import { parseHash, routeToHash } from "../hooks/useHashRoute";
import { formatValue, humanize, looksNumeric } from "../components/reports/format";
import type { ReportView } from "../types/reports";

function sampleReport(overrides: Partial<ReportView> = {}): ReportView {
  return {
    slug: "active-policies-by-region",
    title: "Active Policies by Region",
    description: "Count of active policies grouped by region.",
    output_types: ["kpi", "chart", "table"],
    columns: {
      region: { label: "Region" },
      n: { label: "Count", format: "int" },
    },
    chart: { type: "bar", x: "region", y: "n" },
    result_columns: ["region", "n"],
    rows: [
      { region: "West", n: 1200 },
      { region: "East", n: 875 },
      { region: "South", n: 640 },
    ],
    row_count: 3,
    snapshot_at: "2026-07-01T12:00:00Z",
    snapshot_status: "ok",
    stale: false,
    ...overrides,
  };
}

describe("ReportRenderer", () => {
  it("renders table, chart, and KPI surfaces per output_types", () => {
    const { container } = render(<ReportRenderer report={sampleReport()} />);

    expect(container.querySelectorAll(".rl-kpi").length).toBeGreaterThan(0);
    expect(container.querySelectorAll("svg .rl-bar").length).toBe(3);
    expect(container.querySelectorAll(".rl-table tbody tr").length).toBe(3);
    expect(container.textContent).toContain("Region");
    expect(container.textContent).toContain("1,200");
  });

  it("falls back to a table when no output type is set", () => {
    const { container } = render(
      <ReportRenderer report={sampleReport({ output_types: [], chart: null })} />,
    );
    expect(container.querySelector(".rl-table")).not.toBeNull();
  });

  it("renders mobile cards when the viewport is narrow", () => {
    const orig = window.matchMedia;
    window.matchMedia = ((q: string) => ({
      matches: true,
      media: q,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      onchange: null,
      dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia;
    try {
      const { container } = render(<ReportRenderer report={sampleReport()} />);
      expect(container.querySelector(".rl-mcards")).not.toBeNull();
      expect(container.querySelectorAll(".rl-mcard").length).toBe(3);
      expect(container.querySelector(".rl-table")).toBeNull();
    } finally {
      window.matchMedia = orig;
    }
  });
});

describe("formatValue", () => {
  it("formats by declared column format", () => {
    expect(formatValue(1234, { format: "int" })).toBe("1,234");
    expect(formatValue(0.25, { format: "percent" })).toBe("25%");
    expect(formatValue(null)).toBe("—");
  });
});

describe("humanize", () => {
  it("makes readable labels, keeping short acronyms", () => {
    expect(humanize("STORE_NUMBER")).toBe("Store Number");
    expect(humanize("period_week")).toBe("Period Week");
    expect(humanize("RDO")).toBe("RDO");
    expect(humanize("PPLH")).toBe("PPLH");
  });
});

describe("looksNumeric", () => {
  it("uses declared format, else infers from data", () => {
    expect(looksNumeric("currency", [])).toBe(true);
    expect(looksNumeric(undefined, [1200, 875, 640])).toBe(true);
    expect(looksNumeric(undefined, ["West", "East"])).toBe(false);
    expect(looksNumeric(undefined, ["New Store", "$1,564"])).toBe(false);
  });
});

describe("ReportChart", () => {
  it("caps a pie to 6 slices, folding the rest into Other", async () => {
    const { ReportChart } = await import("../components/reports/Charts");
    const rows = Array.from({ length: 20 }, (_, i) => ({ k: `Cat ${i}`, v: 20 - i }));
    const { container } = render(
      <ReportChart chart={{ type: "pie", x: "k", y: "v" }} rows={rows} />,
    );
    expect(container.querySelectorAll("svg path").length).toBe(6);
    expect(container.textContent).toContain("Other");
  });
});

describe("analyzeColumns", () => {
  it("classifies measures vs badges vs identity", async () => {
    const { analyzeColumns } = await import("../components/reports/tableAnalysis");
    const rows = Array.from({ length: 12 }, (_, i) => ({
      store: 3500 + i,
      tier: (i % 3) + 1,
      sales: 1000 + i * 137,
      city: `City ${i}`,
    }));
    const stats = analyzeColumns(["store", "tier", "sales", "city"], rows, {}, "store");
    expect(stats.sales.measure).toBe(true); // many distinct numeric → data bar
    expect(stats.tier.badge).toBe(true); // 3 distinct → pill
    expect(stats.store.measure).toBe(false); // identity column excluded
  });
});

describe("LayoutEditor", () => {
  it("adds a chart block with sensible defaults", async () => {
    const { LayoutEditor } = await import("../components/reports/LayoutEditor");
    const onChange = vi.fn();
    const { getByText } = render(
      <LayoutEditor value={[]} onChange={onChange} columns={["DOW", "PPLH"]} />,
    );
    fireEvent.click(getByText("+ chart"));
    expect(onChange).toHaveBeenCalledWith([
      { type: "chart", span: 6, title: "", chart: { type: "bar", x: "", y: "", agg: "sum" } },
    ]);
  });
});

describe("hash routing", () => {
  it("round-trips slug routes", () => {
    expect(parseHash("#/r/my-report")).toEqual({ view: "report", slug: "my-report" });
    expect(parseHash("#/upload")).toEqual({ view: "upload" });
    expect(parseHash("#/edit/my-report")).toEqual({ view: "edit", slug: "my-report" });
    expect(parseHash("#/")).toEqual({ view: "browse" });
    expect(routeToHash({ view: "report", slug: "a b" })).toBe("#/r/a%20b");
    expect(routeToHash({ view: "edit", slug: "my-report" })).toBe("#/edit/my-report");
  });
});
