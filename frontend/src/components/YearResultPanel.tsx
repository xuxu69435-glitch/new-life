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
          {result.family_changes && Object.keys(result.family_changes).length > 0 ? (
            <div className="change-block">
              <h3>Family changes</h3>
              {result.relationship_status_before && result.relationship_status_after ? (
                <p>
                  Status: {result.relationship_status_before} → {result.relationship_status_after}
                </p>
              ) : null}
              {result.married_this_year ? <p className="muted-text">Married this year.</p> : null}
              {result.child_born_this_year ? <p className="muted-text">Child born this year.</p> : null}
              {result.partner_relation_delta !== 0 ? (
                <p>Partner relation: {result.partner_relation_delta > 0 ? "+" : ""}{result.partner_relation_delta}</p>
              ) : null}
              {result.family_pressure_delta !== 0 ? (
                <p>Family pressure: {result.family_pressure_delta > 0 ? "+" : ""}{result.family_pressure_delta}</p>
              ) : null}
            </div>
          ) : null}
          {result.social_narrative && result.social_narrative.length > 0 ? (
            <div className="change-block">
              <h3>Social changes</h3>
              {result.social_narrative.map((line) => (
                <p key={line}>{line}</p>
              ))}
            </div>
          ) : null}
          {result.romance_narrative && result.romance_narrative.length > 0 ? (
            <div className="change-block">
              <h3>Romance changes</h3>
              {result.romance_narrative.map((line) => (
                <p key={line}>{line}</p>
              ))}
            </div>
          ) : null}
          {result.pending_random_event ? (
            <div className="change-block">
              <h3>Pending random event</h3>
              <p>
                <strong>{String(result.pending_random_event.name)}</strong>
              </p>
              <p className="muted-text">{String(result.pending_random_event.event_text)}</p>
            </div>
          ) : null}
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
          {result.education_stage_after ? (
            <div className="change-block">
              <h3>Education</h3>
              <p>
                <span>Stage</span>
                <strong>
                  {result.education_stage_before ?? "n/a"} → {result.education_stage_after}
                </strong>
              </p>
              {result.education_graduated_this_year ? (
                <p className="muted-text">Graduated this year.</p>
              ) : null}
            </div>
          ) : null}
          {result.career_status_after ? (
            <div className="change-block">
              <h3>Career</h3>
              <p>
                <span>Status</span>
                <strong>
                  {result.career_status_before ?? "n/a"} → {result.career_status_after}
                </strong>
              </p>
              {result.career_path ? <p>Path: {result.career_path}</p> : null}
              {result.position_level ? <p>Level: {result.position_level}</p> : null}
              {result.career_income_change > 0 ? (
                <p>Annual income: {result.annual_income} (+{result.career_income_change} cash)</p>
              ) : null}
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
