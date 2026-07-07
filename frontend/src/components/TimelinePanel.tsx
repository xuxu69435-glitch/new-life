import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../api/client";

type TimelinePanelProps = {
  lifeId: string;
};

export function TimelinePanel({ lifeId }: TimelinePanelProps) {
  const timelineQuery = useQuery({
    queryKey: ["timeline", lifeId],
    queryFn: () => apiClient.getTimeline(lifeId),
  });

  return (
    <section className="panel timeline-panel">
      <p className="eyebrow">Timeline</p>
      <h2>Life records</h2>
      {timelineQuery.isLoading ? <p className="muted-text">Loading records...</p> : null}
      {timelineQuery.isError ? <p className="error-text">{String(timelineQuery.error.message)}</p> : null}
      {timelineQuery.data?.length === 0 ? <p className="muted-text">No records yet.</p> : null}
      <ol className="timeline-list">
        {timelineQuery.data?.map((item) => (
          <li key={`${item.life_id}-${item.age_after}`}>
            <span>Age {item.age_after}</span>
            <p>{item.narrative_text}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
