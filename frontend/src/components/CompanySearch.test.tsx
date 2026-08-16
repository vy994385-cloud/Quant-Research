import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { fetchDiscovery } from "../api/client"
import { DISCOVERY } from "../test/fixtures"
import CompanySearch from "./CompanySearch"

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>()
  return {
    ...actual,
    fetchDiscovery: vi.fn(),
  }
})

const mockedFetchDiscovery = vi.mocked(fetchDiscovery)

describe("CompanySearch", () => {
  it("shows matching companies as the query narrows", async () => {
    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)

    const user = userEvent.setup()
    render(<CompanySearch onSelect={() => {}} />)

    const input = screen.getByLabelText("Company search")

    await user.type(input, "infosys")

    expect(await screen.findByText("INFY")).toBeInTheDocument()
    expect(screen.queryByText("TCS")).not.toBeInTheDocument()
    expect(screen.queryByText("HDFCBANK")).not.toBeInTheDocument()
  })

  it("selects a company from the dropdown", async () => {
    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)

    const onSelect = vi.fn()
    const user = userEvent.setup()
    render(<CompanySearch onSelect={onSelect} />)

    const input = screen.getByLabelText("Company search")

    await user.type(input, "tcs")
    await user.click(await screen.findByText("TCS"))

    expect(onSelect).toHaveBeenCalledWith("TCS")
  })

  it("submits the first match on Enter", async () => {
    mockedFetchDiscovery.mockResolvedValue(DISCOVERY)

    const onSelect = vi.fn()
    const user = userEvent.setup()
    render(<CompanySearch onSelect={onSelect} />)

    const input = screen.getByLabelText("Company search")

    await user.type(input, "tcs{enter}")

    expect(onSelect).toHaveBeenCalledWith("TCS")
  })

  it("shows a structured message when discovery fails", async () => {
    mockedFetchDiscovery.mockRejectedValue(
      new Error("Discovery API is unavailable."),
    )

    render(<CompanySearch onSelect={() => {}} />)

    const input = screen.getByLabelText("Company search")
    await userEvent.click(input)

    expect(
      await screen.findByText(/Discovery API is unavailable/),
    ).toBeInTheDocument()
  })
})
