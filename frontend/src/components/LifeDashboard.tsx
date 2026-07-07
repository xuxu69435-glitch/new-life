import { useEffect } from "react";
import { LogOut } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import { useGameStore } from "../store/gameStore";
import { ChoicePanel } from "./ChoicePanel";
import { FamilyPanel } from "./FamilyPanel";
import { InheritancePanel } from "./InheritancePanel";
import { StatusPanel } from "./StatusPanel";
import { TimelinePanel } from "./TimelinePanel";
import { YearResultPanel } from "./YearResultPanel";

type LifeDashboardProps = {
  onExit: () => void;
};

export function LifeDashboard({ onExit }: LifeDashboardProps) {
  const lifeId = useGameStore((state) => state.lifeId);
  const setAvailableChoices = useGameStore((state) => state.setAvailableChoices);
  const reset = useGameStore((state) => state.reset);

  const lifeQuery = useQuery({
    queryKey: ["life", lifeId],
    queryFn: () => apiClient.getLife(lifeId!),
    enabled: Boolean(lifeId),
  });

  useEffect(() => {
    if (lifeQuery.data) {
      setAvailableChoices(lifeQuery.data.available_choices);
    }
  }, [lifeQuery.data, setAvailableChoices]);

  if (!lifeId) {
    return null;
  }

  function exitToHome() {
    reset();
    onExit();
  }

  return (
    <main className="dashboard-layout">
      <header className="topbar">
        <div>
          <p className="eyebrow">Life dashboard</p>
          <h1>Annual record</h1>
        </div>
        <button className="ghost-button" type="button" onClick={exitToHome}>
          <LogOut size={18} aria-hidden="true" />
          Exit
        </button>
      </header>

      {lifeQuery.isLoading ? <p className="muted-text">Loading life state...</p> : null}
      {lifeQuery.isError ? <p className="error-text">{String(lifeQuery.error.message)}</p> : null}

      {lifeQuery.data ? (
        <div className="dashboard-grid">
          <StatusPanel state={lifeQuery.data.state} />
          <section className="main-column">
            <ChoicePanel lifeId={lifeId} disabled={lifeQuery.data.state.is_dead} />
            <YearResultPanel />
            <TimelinePanel lifeId={lifeId} />
          </section>
          <aside className="side-column">
            <FamilyPanel lifeId={lifeId} />
            <InheritancePanel lifeId={lifeId} />
          </aside>
        </div>
      ) : null}
    </main>
  );
}
