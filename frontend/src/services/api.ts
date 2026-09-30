import type { AnalyzeResult, CompareResult, HistoryItem } from "../types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_URL}${path}`, options);
  } catch {
    throw new Error("Cannot reach the QueryDoctor server. Is the backend running?");
  }

  if (!response.ok) {
    let message = "Something went wrong.";
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (response.status === 422) {
        message = "The request was not valid. Please check your input.";
      }
    } catch {
      // No JSON body, so keep the default message.
    }
    throw new Error(message);
  }

  return response.json();
}

export function analyzeQuery(query: string): Promise<AnalyzeResult> {
  return request<AnalyzeResult>("/api/queries/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
}

export function compareQueries(beforeQuery: string, afterQuery: string): Promise<CompareResult> {
  return request<CompareResult>("/api/queries/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ before_query: beforeQuery, after_query: afterQuery }),
  });
}

export function getHistory(limit = 50): Promise<HistoryItem[]> {
  return request<HistoryItem[]>(`/api/history?limit=${limit}`);
}

export function getAnalysis(id: number): Promise<AnalyzeResult> {
  return request<AnalyzeResult>(`/api/history/${id}`);
}
