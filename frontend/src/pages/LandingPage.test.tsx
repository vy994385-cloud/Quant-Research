import { fireEvent, render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it } from "vitest"
import LandingPage from "./LandingPage"

describe("QRQuant landing page", () => {
  it("explains the product and directs visitors to Markets", () => {
    render(<MemoryRouter><LandingPage /></MemoryRouter>)

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Understand the markets. Investigate the business. Verify the numbers.",
    )
    expect(screen.getAllByRole("link", { name: /explore markets|explore market intelligence/i })[0]).toHaveAttribute(
      "href",
      "/market-intelligence",
    )
    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Every number deserves a trail." })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "One research journey. Different ways to investigate." })).toBeInTheDocument()
    expect(screen.getByText(/Coverage is not uniform/)).toBeInTheDocument()
    expect(screen.getByText(/not a broker, portfolio manager or source of personalized investment advice/)).toBeInTheDocument()
  })

  it("labels the product preview as illustrative and not live market data", () => {
    render(<MemoryRouter><LandingPage /></MemoryRouter>)
    expect(screen.getByLabelText("Illustrative QRQuant research interface, not live market data")).toBeInTheDocument()
    expect(screen.getByText("ILLUSTRATIVE PREVIEW")).toBeInTheDocument()
    expect(screen.getByText(/does not display live prices or current market conditions/)).toBeInTheDocument()
  })

  it("provides accessible mobile navigation and closes it with Escape", () => {
    const { container } = render(<MemoryRouter><LandingPage /></MemoryRouter>)
    const toggle = container.querySelector<HTMLButtonElement>(".landing-menu-toggle")
    expect(toggle).not.toBeNull()

    fireEvent.click(toggle!)
    expect(toggle).toHaveAttribute("aria-expanded", "true")
    expect(screen.getByRole("navigation", { name: "Mobile navigation" })).toBeInTheDocument()

    const mobileNavLink = container.querySelector<HTMLAnchorElement>("#landing-mobile-navigation a[href=\"#methodology\"]")
    expect(mobileNavLink).not.toBeNull()
    fireEvent.keyDown(mobileNavLink!, { key: "Escape" })

    expect(screen.queryByRole("navigation", { name: "Mobile navigation" })).not.toBeInTheDocument()
    expect(toggle).toHaveAttribute("aria-expanded", "false")
    expect(toggle).toHaveFocus()
  })
})
