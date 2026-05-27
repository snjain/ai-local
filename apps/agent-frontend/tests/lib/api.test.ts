import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

describe("getArchitectureEndpoint", () => {
  beforeEach(async () => {
    import.meta.env.VITE_AGENT_ENDPOINT = "http://localhost:8009/api/pydantic-agent";
  });

  afterEach(() => {
    vi.resetModules();
  });

  it("returns default endpoint for unknown architecture", async () => {
    const { getArchitectureEndpoint } = await import("@/lib/api");
    expect(getArchitectureEndpoint("unknown")).toBe("http://localhost:8009/api/pydantic-agent");
  });

  it("returns routing endpoint", async () => {
    const { getArchitectureEndpoint } = await import("@/lib/api");
    expect(getArchitectureEndpoint("routing")).toBe("http://localhost:8009/api/agent-routing");
  });

  it("returns parallel endpoint", async () => {
    const { getArchitectureEndpoint } = await import("@/lib/api");
    expect(getArchitectureEndpoint("parallel")).toBe("http://localhost:8009/api/agent-parallel");
  });

  it("returns supervisor endpoint", async () => {
    const { getArchitectureEndpoint } = await import("@/lib/api");
    expect(getArchitectureEndpoint("supervisor")).toBe("http://localhost:8009/api/agent-supervisor");
  });

  it("returns guardrail endpoint", async () => {
    const { getArchitectureEndpoint } = await import("@/lib/api");
    expect(getArchitectureEndpoint("guardrail")).toBe("http://localhost:8009/api/agent-guardrail");
  });
});

describe("sendMessage", () => {
  let sendMessage: typeof import("@/lib/api").sendMessage;

  beforeEach(async () => {
    import.meta.env.VITE_AGENT_ENDPOINT = "http://localhost:8009/api/pydantic-agent";
    import.meta.env.VITE_ENABLE_STREAMING = "false";
    vi.stubGlobal("fetch", vi.fn());
    vi.resetModules();
    const api = await import("@/lib/api");
    sendMessage = api.sendMessage;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it("sends a message and returns parsed JSON response", async () => {
    const mockResponse = {
      output: "Hello, world!",
      session_id: "test-session",
      title: "Test Conversation",
    };

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      text: async () => JSON.stringify(mockResponse),
    } as Response);

    const result = await sendMessage("Hi", "user-123", "session-456");

    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8009/api/pydantic-agent",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      })
    );

    expect(result).toEqual(mockResponse);
  });

  it("throws on API error response", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: async () => "Internal Server Error",
    } as Response);

    await expect(sendMessage("Hi", "user-123")).rejects.toThrow("API error: 500");
  });

  it("throws on empty response", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      text: async () => "",
    } as Response);

    await expect(sendMessage("Hi", "user-123")).rejects.toThrow("Empty response");
  });

  it("handles array response format", async () => {
    const mockArrayResponse = [
      {
        output: "Array response",
        session_id: "session-789",
        conversation_title: "Array Title",
      },
    ];

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      text: async () => JSON.stringify(mockArrayResponse),
    } as Response);

    const result = await sendMessage("Hi", "user-123");
    expect(result.output).toBe("Array response");
    expect(result.title).toBe("Array Title");
  });

  it("includes access token in Authorization header when provided", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      text: async () => JSON.stringify({ output: "OK" }),
    } as Response);

    await sendMessage("Hi", "user-123", "", "my-access-token");

    const callArgs = vi.mocked(fetch).mock.calls[0][1] as RequestInit;
    expect(callArgs.headers).toMatchObject({
      Authorization: "Bearer my-access-token",
    });
  });
});
