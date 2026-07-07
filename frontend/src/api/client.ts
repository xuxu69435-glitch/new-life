import type { LifeStateResponse, YearResult } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  createLife(): Promise<LifeStateResponse> {
    return request<LifeStateResponse>("/games", {
      method: "POST",
      body: JSON.stringify({ rule_version: "v1" }),
    });
  },

  getLife(lifeId: string): Promise<LifeStateResponse> {
    return request<LifeStateResponse>(`/games/${lifeId}`);
  },

  advanceLife(lifeId: string, annualFocus: string): Promise<YearResult> {
    return request<YearResult>(`/games/${lifeId}/advance`, {
      method: "POST",
      body: JSON.stringify({ player_choices: { annual_focus: annualFocus } }),
    });
  },

  getTimeline(lifeId: string): Promise<YearResult[]> {
    return request<YearResult[]>(`/timelines/${lifeId}`);
  },

  getFamily(lifeId: string): Promise<Record<string, unknown>> {
    return request<Record<string, unknown>>(`/families/${lifeId}`);
  },

  getInheritance(lifeId: string): Promise<Record<string, unknown>> {
    return request<Record<string, unknown>>(`/inheritance/${lifeId}`);
  },
};
