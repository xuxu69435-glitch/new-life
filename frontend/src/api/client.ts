import type {
  InheritanceResult,
  LegalChoiceResponse,
  LegalStateResponse,
  LifeStateResponse,
  PendingRandomEventResponse,
  PlayableHeirsResponse,
  RandomEventChoiceResponse,
  YearResult,
} from "./types";

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

  getPendingRandomEvent(lifeId: string): Promise<PendingRandomEventResponse> {
    return request<PendingRandomEventResponse>(`/games/${lifeId}/pending-random-event`);
  },

  submitRandomEventChoice(lifeId: string, choiceId: string): Promise<RandomEventChoiceResponse> {
    return request<RandomEventChoiceResponse>(`/games/${lifeId}/random-event-choice`, {
      method: "POST",
      body: JSON.stringify({ choice_id: choiceId }),
    });
  },

  getLegalState(lifeId: string): Promise<LegalStateResponse> {
    return request<LegalStateResponse>(`/games/${lifeId}/legal-state`);
  },

  submitLegalChoice(lifeId: string, choiceId: string): Promise<LegalChoiceResponse> {
    return request<LegalChoiceResponse>(`/games/${lifeId}/legal-choice`, {
      method: "POST",
      body: JSON.stringify({ choice_id: choiceId }),
    });
  },

  getTimeline(lifeId: string): Promise<YearResult[]> {
    return request<YearResult[]>(`/timelines/${lifeId}`);
  },

  getFamily(lifeId: string): Promise<Record<string, unknown>> {
    return request<Record<string, unknown>>(`/families/${lifeId}`);
  },

  getInheritance(lifeId: string): Promise<InheritanceResult> {
    return request<InheritanceResult>(`/inheritance/${lifeId}`);
  },

  getPlayableHeirs(lifeId: string): Promise<PlayableHeirsResponse> {
    return request<PlayableHeirsResponse>(`/inheritance/${lifeId}/playable-heirs`);
  },

  continueAsHeir(lifeId: string, heirPersonId: string): Promise<Record<string, unknown>> {
    return request<Record<string, unknown>>(`/inheritance/${lifeId}/continue-as-heir`, {
      method: "POST",
      body: JSON.stringify({ heir_person_id: heirPersonId }),
    });
  },
};
