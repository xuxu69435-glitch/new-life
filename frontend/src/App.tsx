import { useState } from "react";

import { apiClient } from "./api/client";
import { CreateLifePage } from "./components/CreateLifePage";
import { HomePage } from "./components/HomePage";
import { LifeDashboard } from "./components/LifeDashboard";
import { useGameStore } from "./store/gameStore";

type Screen = "home" | "create" | "game";

export default function App() {
  const lifeId = useGameStore((state) => state.lifeId);
  const setLife = useGameStore((state) => state.setLife);
  const [screen, setScreen] = useState<Screen>(lifeId ? "game" : "home");

  async function resumeLife(targetLifeId: string) {
    const payload = await apiClient.getLife(targetLifeId);
    setLife(targetLifeId, payload.available_choices);
    setScreen("game");
  }

  if (screen === "create") {
    return <CreateLifePage onBack={() => setScreen("home")} onCreated={() => setScreen("game")} />;
  }

  if (screen === "game" && lifeId) {
    return <LifeDashboard onExit={() => setScreen("home")} />;
  }

  return <HomePage onCreate={() => setScreen("create")} onResume={(id) => void resumeLife(id)} />;
}
