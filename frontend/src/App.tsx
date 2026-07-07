import { useState } from "react";

import { CreateLifePage } from "./components/CreateLifePage";
import { HomePage } from "./components/HomePage";
import { LifeDashboard } from "./components/LifeDashboard";
import { useGameStore } from "./store/gameStore";

type Screen = "home" | "create" | "game";

export default function App() {
  const lifeId = useGameStore((state) => state.lifeId);
  const [screen, setScreen] = useState<Screen>(lifeId ? "game" : "home");

  if (screen === "create") {
    return <CreateLifePage onBack={() => setScreen("home")} onCreated={() => setScreen("game")} />;
  }

  if (screen === "game" && lifeId) {
    return <LifeDashboard onExit={() => setScreen("home")} />;
  }

  return <HomePage onCreate={() => setScreen("create")} />;
}
