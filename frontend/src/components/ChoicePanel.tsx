import { useMemo, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import { useGameStore } from "../store/gameStore";

type ChoicePanelProps = {
  lifeId: string;
  disabled: boolean;
};

export function ChoicePanel({ lifeId, disabled }: ChoicePanelProps) {
  const queryClient = useQueryClient();
  const availableChoices = useGameStore((state) => state.availableChoices);
  const setAvailableChoices = useGameStore((state) => state.setAvailableChoices);
  const setLastResult = useGameStore((state) => state.setLastResult);
  const firstChoice = availableChoices[0]?.id ?? "";
  const [selectedChoice, setSelectedChoice] = useState(firstChoice);

  const selected = useMemo(
    () => selectedChoice || firstChoice,
    [firstChoice, selectedChoice],
  );

  const mutation = useMutation({
    mutationFn: () => apiClient.advanceLife(lifeId, selected),
    onSuccess: (result) => {
      setLastResult(result);
      setAvailableChoices(result.next_available_choices);
      void queryClient.invalidateQueries({ queryKey: ["life", lifeId] });
      void queryClient.invalidateQueries({ queryKey: ["timeline", lifeId] });
      void queryClient.invalidateQueries({ queryKey: ["timeline-entries", lifeId] });
      void queryClient.invalidateQueries({ queryKey: ["family", lifeId] });
      void queryClient.invalidateQueries({ queryKey: ["inheritance", lifeId] });
    },
  });

  return (
    <section className="panel choice-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Annual choice</p>
          <h2>Choose this year</h2>
        </div>
        <button
          className="primary-button"
          type="button"
          onClick={() => mutation.mutate()}
          disabled={disabled || mutation.isPending || !selected}
        >
          {mutation.isPending ? <Loader2 className="spin" size={18} aria-hidden="true" /> : <Play size={18} aria-hidden="true" />}
          Advance
        </button>
      </div>

      <div className="choice-list">
        {availableChoices.map((choice) => (
          <label className="choice-option" key={choice.id}>
            <input
              type="radio"
              name="annual-choice"
              value={choice.id}
              checked={selected === choice.id}
              onChange={() => setSelectedChoice(choice.id)}
              disabled={disabled || mutation.isPending}
            />
            <span>{choice.label}</span>
          </label>
        ))}
      </div>
      {disabled ? <p className="muted-text">This life has ended. Annual choices are closed.</p> : null}
      {mutation.isError ? <p className="error-text">{String(mutation.error.message)}</p> : null}
    </section>
  );
}
