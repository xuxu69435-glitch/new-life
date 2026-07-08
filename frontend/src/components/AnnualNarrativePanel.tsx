import { useGameStore } from "../store/gameStore";

type DisplaySection = {
  section_id: string;
  title: string;
  content: string;
};

type AnnualNarrativePanelProps = {
  narrativeResult?: Record<string, unknown> | null;
  fallbackText?: string;
  isDead?: boolean;
};

export function AnnualNarrativePanel({
  narrativeResult,
  fallbackText,
  isDead = false,
}: AnnualNarrativePanelProps) {
  if (!narrativeResult && !fallbackText) {
    return null;
  }

  const summaryText = String(
    narrativeResult?.summary_text ?? fallbackText ?? "",
  );
  const majorEvents = (narrativeResult?.major_event_texts as string[]) ?? [];
  const sections = (narrativeResult?.display_sections as DisplaySection[]) ?? [];
  const tone = String(narrativeResult?.tone ?? "normal");

  return (
    <section className={`panel ${isDead ? "panel-death" : ""}`}>
      <p className="eyebrow">Annual story</p>
      <h2>年度叙事</h2>
      {tone === "solemn" ? <p className="error-text">本年度以离世告终</p> : null}
      {tone === "tense" ? <p className="muted-text">本年度法律状态突出</p> : null}
      {tone === "warm" ? <p className="muted-text">本年度家庭变化突出</p> : null}
      <p className="narrative-text">{summaryText}</p>
      {majorEvents.length > 0 ? (
        <div className="change-block">
          <h3>重大事件</h3>
          {majorEvents.map((text) => (
            <p key={text}>{text}</p>
          ))}
        </div>
      ) : null}
      {sections.map((section) => (
        <div key={section.section_id} className="change-block">
          <h3>{section.title}</h3>
          <p className="narrative-text">{section.content}</p>
        </div>
      ))}
    </section>
  );
}

export function AnnualNarrativeFromStore() {
  const result = useGameStore((state) => state.lastResult);
  if (!result) {
    return null;
  }
  return (
    <AnnualNarrativePanel
      narrativeResult={result.narrative_result}
      fallbackText={result.annual_summary_text || result.narrative_text}
      isDead={result.is_dead}
    />
  );
}
