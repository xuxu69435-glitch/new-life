import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/client";

type RandomEventPanelProps = {
  lifeId: string;
  disabled?: boolean;
};

export function RandomEventPanel({ lifeId, disabled = false }: RandomEventPanelProps) {
  const queryClient = useQueryClient();
  const pendingQuery = useQuery({
    queryKey: ["pending-random-event", lifeId],
    queryFn: () => apiClient.getPendingRandomEvent(lifeId),
    enabled: Boolean(lifeId) && !disabled,
  });

  const submitMutation = useMutation({
    mutationFn: (choiceId: string) => apiClient.submitRandomEventChoice(lifeId, choiceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["life", lifeId] });
      queryClient.invalidateQueries({ queryKey: ["pending-random-event", lifeId] });
    },
  });

  const pending = pendingQuery.data?.pending_random_event;
  if (!pending) {
    return null;
  }

  return (
    <section className="panel">
      <p className="eyebrow">Random event</p>
      <h2>{pending.name}</h2>
      <p className="narrative-text">{pending.event_text}</p>
      <div className="choice-list">
        {pending.choices.map((choice) => (
          <button
            key={choice.choice_id}
            className="primary-button"
            type="button"
            disabled={disabled || submitMutation.isPending}
            onClick={() => submitMutation.mutate(choice.choice_id)}
          >
            {choice.label}: {choice.choice_text}
          </button>
        ))}
      </div>
      {submitMutation.data?.choice_result ? (
        <p className="muted-text">Result: {submitMutation.data.choice_result.effects_text}</p>
      ) : null}
      {submitMutation.isError ? (
        <p className="error-text">{String(submitMutation.error.message)}</p>
      ) : null}
    </section>
  );
}
