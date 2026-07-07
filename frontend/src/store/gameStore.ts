import { create } from "zustand";

import type { AvailableChoice, YearResult } from "../api/types";

type GameStore = {
  lifeId: string | null;
  availableChoices: AvailableChoice[];
  lastResult: YearResult | null;
  setLife: (lifeId: string, choices: AvailableChoice[]) => void;
  setAvailableChoices: (choices: AvailableChoice[]) => void;
  setLastResult: (result: YearResult | null) => void;
  reset: () => void;
};

export const useGameStore = create<GameStore>((set) => ({
  lifeId: null,
  availableChoices: [],
  lastResult: null,
  setLife: (lifeId, availableChoices) => set({ lifeId, availableChoices, lastResult: null }),
  setAvailableChoices: (availableChoices) => set({ availableChoices }),
  setLastResult: (lastResult) => set({ lastResult }),
  reset: () => set({ lifeId: null, availableChoices: [], lastResult: null }),
}));
