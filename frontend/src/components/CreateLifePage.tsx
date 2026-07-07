import { ArrowLeft, Loader2, PlusCircle } from "lucide-react";
import { useMutation } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import { useGameStore } from "../store/gameStore";

type CreateLifePageProps = {
  onBack: () => void;
  onCreated: () => void;
};

export function CreateLifePage({ onBack, onCreated }: CreateLifePageProps) {
  const setLife = useGameStore((state) => state.setLife);
  const mutation = useMutation({
    mutationFn: () => apiClient.createLife(),
    onSuccess: (response) => {
      setLife(response.state.life_id, response.available_choices);
      onCreated();
    },
  });

  return (
    <main className="create-layout">
      <button className="ghost-button" type="button" onClick={onBack}>
        <ArrowLeft size={18} aria-hidden="true" />
        Back
      </button>
      <section className="create-panel">
        <p className="eyebrow">New life</p>
        <h1>Create a server-side life</h1>
        <p>
          The frontend sends a creation command only. Identity, starting attributes,
          health, assets, and available choices are assigned by the backend.
        </p>
        <button className="primary-button" type="button" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
          {mutation.isPending ? <Loader2 className="spin" size={18} aria-hidden="true" /> : <PlusCircle size={18} aria-hidden="true" />}
          Start
        </button>
        {mutation.isError ? <p className="error-text">{String(mutation.error.message)}</p> : null}
      </section>
    </main>
  );
}
