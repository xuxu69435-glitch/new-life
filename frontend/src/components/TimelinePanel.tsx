import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import type { TimelineEntry, YearDetailResponse } from "../api/types";

type TimelinePanelProps = {
  lifeId: string;
};

const HIGH_IMPORTANCE_TYPES = new Set(["death", "inheritance", "legal_event", "family"]);

function groupEntriesByAge(entries: TimelineEntry[]): Map<number, TimelineEntry[]> {
  const grouped = new Map<number, TimelineEntry[]>();
  for (const entry of entries) {
    const list = grouped.get(entry.age) ?? [];
    list.push(entry);
    grouped.set(entry.age, list);
  }
  for (const [age, list] of grouped) {
    grouped.set(
      age,
      [...list].sort((a, b) => b.importance - a.importance),
    );
  }
  return grouped;
}

function YearDetailBlock({ detail }: { detail: YearDetailResponse }) {
  return (
    <div className="year-detail-block">
      <p className="muted-text">{detail.annual_summary}</p>
      <div className="change-block">
        <h4>状态变化</h4>
        <p>属性：{JSON.stringify(detail.state_changes.attributes)}</p>
        <p>健康：{JSON.stringify(detail.state_changes.health)}</p>
        <p>资产：{JSON.stringify(detail.state_changes.assets)}</p>
      </div>
      {detail.events.length > 0 ? (
        <div className="change-block">
          <h4>本年事件</h4>
          {detail.events.map((event) => (
            <p key={event.entry_id}>
              <strong>{event.title}</strong> — {event.display_text || event.summary}
            </p>
          ))}
        </div>
      ) : null}
      {Array.isArray(detail.achievements?.newly_unlocked) &&
      (detail.achievements.newly_unlocked as Array<Record<string, unknown>>).length > 0 ? (
        <div className="change-block">
          <h4>本年成就</h4>
          {(detail.achievements.newly_unlocked as Array<Record<string, unknown>>).map((item) => (
            <p key={String(item.achievement_id)}>
              {String(item.title)} (+{String(item.points_gained ?? 0)})
            </p>
          ))}
        </div>
      ) : null}
      {detail.milestones.length > 0 ? (
        <div className="change-block">
          <h4>里程碑</h4>
          {detail.milestones.map((item) => (
            <p key={String(item.milestone_id)}>{String(item.title)}</p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function TimelinePanel({ lifeId }: TimelinePanelProps) {
  const [expandedAge, setExpandedAge] = useState<number | null>(null);
  const [filterType, setFilterType] = useState<string>("");

  const entriesQuery = useQuery({
    queryKey: ["timeline-entries", lifeId, filterType],
    queryFn: () =>
      apiClient.getTimelineEntries(lifeId, filterType ? { entryType: filterType } : undefined),
  });

  const detailQuery = useQuery({
    queryKey: ["year-detail", lifeId, expandedAge],
    queryFn: () => apiClient.getYearDetail(lifeId, expandedAge!),
    enabled: expandedAge !== null,
  });

  const grouped = useMemo(() => {
    const entries = entriesQuery.data?.entries ?? [];
    return groupEntriesByAge(entries);
  }, [entriesQuery.data]);

  const ages = useMemo(() => Array.from(grouped.keys()).sort((a, b) => b - a), [grouped]);

  return (
    <section className="panel timeline-panel">
      <p className="eyebrow">Timeline</p>
      <h2>人生时间轴</h2>
      <div className="timeline-filters">
        <label>
          事件筛选
          <select value={filterType} onChange={(event) => setFilterType(event.target.value)}>
            <option value="">全部</option>
            <option value="death">死亡</option>
            <option value="inheritance">遗产</option>
            <option value="legal_event">法律</option>
            <option value="family">家庭</option>
            <option value="education">教育</option>
            <option value="career">职业</option>
            <option value="achievement">成就</option>
            <option value="milestone">里程碑</option>
            <option value="random_event">随机事件</option>
            <option value="mainline_task">主线</option>
          </select>
        </label>
      </div>
      {entriesQuery.isLoading ? <p className="muted-text">加载时间轴...</p> : null}
      {entriesQuery.isError ? <p className="error-text">{String(entriesQuery.error.message)}</p> : null}
      {ages.length === 0 ? <p className="muted-text">暂无人生记录。</p> : null}
      <ol className="timeline-list">
        {ages.map((age) => {
          const entries = grouped.get(age) ?? [];
          const overview = entries.find((item) => item.entry_type === "normal_summary");
          const highlights = entries.filter((item) => HIGH_IMPORTANCE_TYPES.has(item.entry_type));
          const isExpanded = expandedAge === age;
          return (
            <li key={`year-${age}`} className={highlights.length > 0 ? "timeline-year-highlight" : ""}>
              <button
                type="button"
                className="timeline-year-toggle"
                onClick={() => setExpandedAge(isExpanded ? null : age)}
              >
                <span>{age}岁</span>
                <p>{overview?.summary ?? overview?.display_text ?? "年度记录"}</p>
              </button>
              {highlights.length > 0 ? (
                <div className="timeline-highlights">
                  {highlights.map((item) => (
                    <p key={item.entry_id} className="timeline-highlight-item">
                      <strong>{item.title}</strong> — {item.display_text || item.summary}
                    </p>
                  ))}
                </div>
              ) : null}
              {isExpanded && detailQuery.data ? <YearDetailBlock detail={detailQuery.data} /> : null}
              {isExpanded && detailQuery.isLoading ? <p className="muted-text">加载年度详情...</p> : null}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
