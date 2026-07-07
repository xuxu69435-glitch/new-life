import { FilePlus2 } from "lucide-react";

import archiveImage from "../assets/life-archive.svg";

type HomePageProps = {
  onCreate: () => void;
};

export function HomePage({ onCreate }: HomePageProps) {
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
      </section>
      <img className="archive-visual" src={archiveImage} alt="Life archive timeline" />
    </main>
  );
}
