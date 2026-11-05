import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it } from "vitest"
import LandingPage from "./LandingPage"

describe("QRQuant landing page", () => {
  it("explains the product and directs visitors to Markets", () => {
    render(<MemoryRouter><LandingPage /></MemoryRouter>)

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Understand the markets. Investigate the business. Verify the numbers.",
    )
    expect(screen.getAllByRole("link", { name: /explore markets|explore qrquant/i })[0]).toHaveAttribute(
      "href",
      "/market-intelligence",
    )
    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Every number deserves a trail." })).toBeInTheDocument()
  })

  it("labels the product preview as illustrative", () => {
    render(<MemoryRouter><LandingPage /></MemoryRouter>)
    expect(screen.getByLabelText("Illustrative QRQuant research interface")).toBeInTheDocument()
    expect(screen.getByText("CONCEPT PREVIEW")).toBeInTheDocument()
  })
})
