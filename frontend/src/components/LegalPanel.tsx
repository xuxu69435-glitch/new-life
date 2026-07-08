import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/client";

type LegalPanelProps = {
  lifeId: string;
  disabled?: boolean;
};

export function LegalPanel({ lifeId, disabled = false }: LegalPanelProps) {
  const queryClient = useQueryClient();
  const legalQuery = useQuery({
    queryKey: ["legal-state", lifeId],
    queryFn: () => apiClient.getLegalState(lifeId),
    enabled: Boolean(lifeId) && !disabled,
  });

  const submitMutation = useMutation({
    mutationFn: (choiceId: string) => apiClient.submitLegalChoice(lifeId, choiceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["life", lifeId] });
      queryClient.invalidateQueries({ queryKey: ["legal-state", lifeId] });
    },
  });

  const legal = legalQuery.data?.legal;
  const pending = legalQuery.data?.pending_legal_event;
  const restrictions = legalQuery.data?.restrictions;

  if (!legal && !pending) {
    return null;
  }

  const showLegalSummary =
    legal?.is_in_prison ||
    legal?.is_fugitive ||
    legal?.has_criminal_record ||
    legal?.is_under_supervision;

  if (!showLegalSummary && !pending) {
    return null;
  }

  return (
    <section className="panel">
      <p className="eyebrow">Legal status</p>
      <h2>司法与服刑</h2>
      {showLegalSummary ? (
        <ul className="status-list">
          <li>入狱：{legal?.is_in_prison ? "是" : "否"}</li>
          <li>剩余刑期：{legal?.sentence_remaining_years ?? 0} 年</li>
          <li>总刑期：{legal?.sentence_total_years ?? 0} 年</li>
          <li>已服刑：{legal?.years_served ?? 0} 年</li>
          <li>改造进度：{legal?.rehabilitation_progress ?? 0}</li>
          <li>连续积极改造：{legal?.consecutive_rehabilitation_years ?? 0} 年</li>
          <li>潜逃：{legal?.is_fugitive ? "是" : "否"}</li>
          <li>犯罪记录：{legal?.has_criminal_record ? "有" : "无"}</li>
          <li>监管期：{legal?.is_under_supervision ? "是" : "否"}</li>
          <li>监管期剩余：{legal?.supervision_remaining_years ?? 0} 年</li>
          <li>研发禁令剩余：{legal?.research_job_ban_remaining_years ?? 0} 年</li>
          <li>就业惩罚年份：{legal?.post_release_employment_penalty_year ?? 0}</li>
          <li>考公禁止：{legal?.civil_service_banned ? "是" : "否"}</li>
        </ul>
      ) : null}
      {restrictions ? (
        <p className="muted-text">
          就业惩罚率：{Math.round((restrictions.employment_penalty_rate ?? 0) * 100)}%
        </p>
      ) : null}
      {pending ? (
        <>
          <h3>{pending.name}</h3>
          <p className="narrative-text">{pending.event_text}</p>
          <div className="choice-list">
            {pending.choices
              ?.filter((choice) => choice.implementation_status !== "planned")
              .map((choice) => (
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
        </>
      ) : null}
      {submitMutation.isError ? (
        <p className="error-text">{String(submitMutation.error.message)}</p>
      ) : null}
    </section>
  );
}
