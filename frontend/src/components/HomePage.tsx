import { FilePlus2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import archiveImage from "../assets/life-archive.svg";

type HomePageProps = {
  onCreate: () => void;
  onResume: (lifeId: string) => void;
};

export function HomePage({ onCreate, onResume }: HomePageProps) {
  const savesQuery = useQuery({
    queryKey: ["saves"],
    queryFn: () => apiClient.listSaves(),
  });

  return (
    <main className="home-layout">
      <section className="home-copy">
        <p className="eyebrow">Server-authored life archive</p>
        <h1>Text Life Simulation</h1>
        <p>
          A first playable shell for yearly life progression, event records, family history,
          and inheritance results. Core simulation results come from the backend.
        </p>
        <button className="primary-button" type="button" onClick={onCreate}>
          <FilePlus2 size={18} aria-hidden="true" />
          Create life
        </button>
        {savesQuery.data?.saves?.length ? (
          <div className="change-block save-list-block">
            <h2>已有存档</h2>
            {savesQuery.data.saves.map((item) => (
              <button
                key={item.life_id}
                type="button"
                className="ghost-button save-list-item"
                onClick={() => onResume(item.life_id)}
              >
                <span>
                  {item.is_dead ? "已故" : "进行中"} · {item.current_age}岁 · 第
                  {item.current_generation}代
                </span>
                <span className="muted-text">{item.updated_at}</span>
              </button>
            ))}
          </div>
        ) : null}
      </section>
      <img className="archive-visual" src={archiveImage} alt="Life archive timeline" />
    </main>
  );
}
