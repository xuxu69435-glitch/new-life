import { useGameStore } from "../store/gameStore";

export function YearResultPanel() {
  const result = useGameStore((state) => state.lastResult);

  return (
    <section className="panel">
      <p className="eyebrow">Year result</p>
      <h2>{result ? `Age ${result.age_before} to ${result.age_after}` : "No year advanced yet"}</h2>
      {result ? (
        <>
          <p className="narrative-text">{result.narrative_text}</p>
          <div className="delta-grid">
            <ChangeBlock title="Attributes" values={result.changed_attributes} />
            <ChangeBlock title="Health" values={result.changed_health} />
            <ChangeBlock title="Assets" values={result.changed_assets} />
          </div>
          {result.death_reason ? <p className="error-text">Death reason: {result.death_reason}</p> : null}
        </>
      ) : (
        <p className="muted-text">Advance a year to receive backend-generated outcomes.</p>
      )}
    </section>
  );
}

function ChangeBlock({ title, values }: { title: string; values: Record<string, number> }) {
  const entries = Object.entries(values);
  return (
    <div className="change-block">
      <h3>{title}</h3>
      {entries.length === 0 ? <p className="muted-text">No changes</p> : null}
      {entries.map(([key, value]) => (
        <p key={key}>
          <span>{key}</span>
          <strong>{value > 0 ? `+${value}` : value}</strong>
        </p>
      ))}
    </div>
  );
}
