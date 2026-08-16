import { describe, expect, it } from "vitest"
import { render, screen, within } from "@testing-library/react"
import { RESEARCH } from "../test/fixtures"
import TimelinePanel from "./TimelinePanel"

describe("TimelinePanel", () => {
  it("renders the research status cards", () => {
    render(<TimelinePanel data={RESEARCH} />)

    expect(screen.getByText("Freshness")).toBeInTheDocument()
    expect(screen.getByText("Coverage")).toBeInTheDocument()
    expect(screen.getByText("Quality")).toBeInTheDocument()

    expect(screen.getByText("11")).toBeInTheDocument()
    expect(screen.getByText("No")).toBeInTheDocument()
  })

  it("renders the chronological evidence entries", () => {
    render(<TimelinePanel data={RESEARCH} />)

    const panel = screen.getByText("Company evidence timeline").closest("section")!

    expect(
      within(panel).getByText("TCS board meeting scheduled for June"),
    ).toBeInTheDocument()
    expect(
      within(panel).getByText(
        "TCS ANNUAL financials for the period ending 2026-03-31",
      ),
    ).toBeInTheDocument()
    expect(
      within(panel).getByText("TCS management guidance on AI adoption"),
    ).toBeInTheDocument()
  })

  it("tags entries with their intel category", () => {
    render(<TimelinePanel data={RESEARCH} />)

    expect(screen.getAllByText("Corporate Action").length).toBeGreaterThan(0)
    expect(screen.getByText("Financial Disclosure")).toBeInTheDocument()
    expect(screen.getByText("Management Statement")).toBeInTheDocument()
  })

  it("lists coverage gaps and quality notes", () => {
    render(<TimelinePanel data={RESEARCH} />)

    expect(
      screen.getByText("No evidence available for categories: BUSINESS_NEWS, REGULATORY_LEGAL, OTHER."),
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        "Conflicts are surfaced as-is; the system never resolves which side is correct automatically.",
      ),
    ).toBeInTheDocument()
  })
})
