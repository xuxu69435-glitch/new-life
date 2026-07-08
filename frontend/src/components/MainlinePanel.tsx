import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../api/client";

type MainlinePanelProps = {
  lifeId: string;
  disabled?: boolean;
};

export function MainlinePanel({ lifeId, disabled = false }: MainlinePanelProps) {
  const mainlineQuery = useQuery({
    queryKey: ["mainline-state", lifeId],
    queryFn: () => apiClient.getMainlineState(lifeId),
    enabled: Boolean(lifeId) && !disabled,
  });

  const data = mainlineQuery.data;
  if (!data) {
    return null;
  }

  const mainline = data.mainline as Record<string, unknown>;
  const completedTasks = Array.isArray(mainline.completed_tasks)
    ? (mainline.completed_tasks as string[])
    : [];
  const activeTasks = data.active_tasks ?? [];
  const hasContent = activeTasks.length > 0 || completedTasks.length > 0;

  if (!hasContent && !data.current_guidance_text) {
    return null;
  }

  return (
    <section className="panel">
      <p className="eyebrow">Mainline goals</p>
      <h2>主线任务</h2>
      <p className="muted-text">
        当前阶段：{String(mainline.current_chapter ?? "-")} / {String(mainline.current_stage ?? "-")}
      </p>
      {data.current_guidance_text ? (
        <p className="narrative-text">{data.current_guidance_text}</p>
      ) : null}
      {activeTasks.length > 0 ? (
        <ul className="status-list">
          {activeTasks.map((task) => (
            <li key={task.task_id}>
              <strong>{task.title}</strong>
              <p className="muted-text">{task.description}</p>
              <p className="muted-text">完成条件：{task.completion_summary}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted-text">当前没有进行中的主线任务。</p>
      )}
      {completedTasks.length > 0 ? (
        <p className="muted-text">已完成：{completedTasks.join("、")}</p>
      ) : null}
    </section>
  );
}
