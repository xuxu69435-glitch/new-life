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
          {result.triggered_random_events.length > 0 ? (
            <div className="change-block">
              <h3>Random events</h3>
              {result.triggered_random_events.map((event) => (
                <div key={event.event_id}>
                  <p>
                    <strong>{event.name}</strong> ({event.category})
                  </p>
                  {event.narrative_text ? <p className="muted-text">{event.narrative_text}</p> : null}
                </div>
              ))}
            </div>
          ) : null}
          {result.health_score_before !== null && result.health_score_after !== null ? (
            <div className="change-block">
              <h3>Health summary</h3>
              <p>
                <span>Score</span>
                <strong>
                  {result.health_score_before} → {result.health_score_after}
                  {result.health_score_delta !== 0
                    ? ` (${result.health_score_delta > 0 ? "+" : ""}${result.health_score_delta})`
                    : ""}
                </strong>
              </p>
              {result.health_level_before && result.health_level_after ? (
                <p>
                  <span>Level</span>
                  <strong>
                    {result.health_level_before} → {result.health_level_after}
                  </strong>
                </p>
              ) : null}
            </div>
          ) : null}
          {result.new_health_warnings.length > 0 ? (
            <div className="change-block">
              <h3>Health warnings</h3>
              {result.new_health_warnings.map((warning) => (
                <p key={warning}>{warning}</p>
              ))}
            </div>
          ) : null}
          <div className="delta-grid">
            <ChangeBlock title="Attributes" values={result.changed_attributes} />
            <ChangeBlock title="Health deltas" values={result.changed_health} />
            <ChangeBlock title="Assets" values={result.changed_assets} />
          </div>
          {Object.keys(result.random_event_attribute_changes).length > 0 ? (
            <ChangeBlock title="Random event attribute changes" values={result.random_event_attribute_changes} />
          ) : null}
          {Object.keys(result.random_event_health_changes).length > 0 ? (
            <ChangeBlock title="Random event health changes" values={result.random_event_health_changes} />
          ) : null}
          {Object.keys(result.random_event_asset_changes).length > 0 ? (
            <ChangeBlock title="Random event asset changes" values={result.random_event_asset_changes} />
          ) : null}
          {result.natural_death_candidate_created ? (
            <p className="muted-text">A natural death candidate was created this year.</p>
          ) : null}
          {result.direct_death_candidate_created ? (
            <p className="muted-text">A direct death candidate was created this year.</p>
          ) : null}
          {result.death_reason ? (
            <p className="error-text">
              Death reason: {result.death_reason}
              {result.death_type ? ` (${result.death_type})` : ""}
            </p>
          ) : null}
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
