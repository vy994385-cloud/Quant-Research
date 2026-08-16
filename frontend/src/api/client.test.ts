import { afterEach, describe, expect, it, vi } from "vitest"
import { ApiError, fetchDiscovery, fetchResearch } from "./client"

afterEach(() => {
  vi.unstubAllGlobals()
})

function stubFetch(response: Partial<Response>) {
  vi.stubGlobal("fetch", vi.fn(async () => response as Response))
}

describe("ApiError", () => {
  it("carries the structured contract error fields", () => {
    const error = new ApiError("nope", "unknown_company", 404, {
      symbol: "TCS",
    })

    expect(error.message).toBe("nope")
    expect(error.code).toBe("unknown_company")
    expect(error.status).toBe(404)
    expect(error.details).toEqual({ symbol: "TCS" })
  })
})

describe("client request normalization", () => {
  it("surfaces structured error bodies", async () => {
    stubFetch({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({
        error: {
          code: "unknown_company",
          message: "Unsupported company",
          details: { symbol: "ZZZ" },
        },
      }),
    })

    await expect(fetchResearch("ZZZ")).rejects.toMatchObject({
      code: "unknown_company",
      message: "Unsupported company",
      status: 404,
      details: { symbol: "ZZZ" },
    })
  })

  it("falls back to request_failed for non-contract failures", async () => {
    stubFetch({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: async () => {
        throw new Error("not json")
      },
    })

    await expect(fetchResearch("TCS")).rejects.toMatchObject({
      code: "request_failed",
      status: 500,
    })
  })

  it("maps network failures to a structured network error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch")
      }),
    )

    await expect(fetchResearch("TCS")).rejects.toMatchObject({
      code: "network_error",
    })
  })

  it("returns parsed discovery payloads", async () => {
    stubFetch({
      ok: true,
      status: 200,
      json: async () => ({ count: 1, results: [] }),
    })

    const discovery = await fetchDiscovery()

    expect(discovery.count).toBe(1)
  })

  it("passes as_of into the query string", async () => {
    const fetchMock = vi.fn(
      async (_input: URL | string | Request, _init?: RequestInit) => ({
        ok: true,
        status: 200,
        json: async () => ({}),
      }),
    )

    vi.stubGlobal("fetch", fetchMock)

    await fetchResearch("TCS", "2026-04-01")

    const url = new URL(fetchMock.mock.calls[0][0] as string | URL)

    expect(url.searchParams.get("as_of")).toBe("2026-04-01")
  })
})
