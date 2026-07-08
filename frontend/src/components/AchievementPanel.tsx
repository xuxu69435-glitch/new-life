import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import { useGameStore } from "../store/gameStore";

type AchievementPanelProps = {
  lifeId: string;
  disabled?: boolean;
};

export function AchievementPanel({ lifeId, disabled = false }: AchievementPanelProps) {
  const lastResult = useGameStore((state) => state.lastResult);
  const query = useQuery({
    queryKey: ["achievement-state", lifeId],
    queryFn: () => apiClient.getAchievementState(lifeId),
    enabled: Boolean(lifeId) && !disabled,
  });

  const data = query.data;
  if (!data) {
    return null;
  }

  const achievements = data.achievement_list ?? [];
  const unlocked = achievements.filter((item) => item.unlocked);
  const newlyThisYear = lastResult?.newly_unlocked_achievements ?? [];

  return (
    <section className="panel">
      <p className="eyebrow">Achievements</p>
      <h2>成就与里程碑</h2>
      <p className="muted-text">
        成就点数：{data.total_points ?? 0} · 已解锁：{data.unlocked_count ?? 0}
      </p>
      {newlyThisYear.length > 0 ? (
        <div className="change-block">
          <h3>本年新解锁</h3>
          {newlyThisYear.map((item) => (
            <p key={item.achievement_id}>
              <strong>{item.title}</strong> (+{item.points_gained})
            </p>
          ))}
        </div>
      ) : null}
      {Array.isArray(data.achievements?.milestones) && data.achievements.milestones.length > 0 ? (
        <div className="change-block">
          <h3>里程碑</h3>
          {(data.achievements.milestones as Array<Record<string, unknown>>).slice(-5).map((item) => (
            <p key={String(item.milestone_id)}>
              {String(item.title)}（{String(item.age)}岁）
            </p>
          ))}
        </div>
      ) : null}
      <div className="change-block">
        <h3>最近解锁</h3>
        {unlocked.length === 0 ? <p className="muted-text">暂无已解锁成就。</p> : null}
        {unlocked.slice(-5).map((item) => (
          <p key={item.achievement_id}>
            <strong>{item.title}</strong>
            <span className="muted-text"> · {item.category}</span>
          </p>
        ))}
      </div>
    </section>
  );
}
