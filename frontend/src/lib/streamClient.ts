import { AgentEvent } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Connects to the SSE endpoint and yields parsed AgentEvent objects.
 * Handles the native chunking from fetch/ReadableStream.
 */
export async function* streamAgentQuery(query: string): AsyncGenerator<AgentEvent, void, unknown> {
  const encodedQuery = encodeURIComponent(query);
  const url = `${API_BASE_URL}/api/agent/query?q=${encodedQuery}`;

  const response = await fetch(url, {
    method: "GET",
    headers: {
      Accept: "text/event-stream",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to connect to agent stream: ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error("ReadableStream not supported by this browser/environment.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      
      // SSE messages are separated by double newlines
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || ""; // The last element is the incomplete chunk
      
      for (const part of parts) {
        if (part.trim().startsWith("data:")) {
          // Remove the "data: " prefix and parse
          const dataStr = part.replace(/^data:\s*/, "");
          if (dataStr) {
            try {
              const event = JSON.parse(dataStr) as AgentEvent;
              yield event;
            } catch (err) {
              console.error("Failed to parse SSE JSON chunk:", err, "Raw data:", dataStr);
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
