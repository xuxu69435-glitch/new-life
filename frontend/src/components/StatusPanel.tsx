import type { LifeState } from "../api/types";

type StatusPanelProps = {
  state: LifeState;
};

function entries(record: Record<string, unknown>) {
  return Object.entries(record).map(([key, value]) => ({ key, value: String(value) }));
}

function healthValue(health: Record<string, unknown>, key: string) {
  const value = health[key];
  return value === undefined || value === null ? null : String(value);
}

export function StatusPanel({ state }: StatusPanelProps) {
  const diseases = Array.isArray(state.health.diseases)
    ? state.health.diseases.map(String)
    : [];

  return (
    <section className="panel status-panel">
      <p className="eyebrow">Person state</p>
      <h2>Age {state.age}</h2>
      <dl className="stat-list">
        <div>
          <dt>Stage</dt>
          <dd>{state.life_stage}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{state.is_dead ? "Ended" : "Alive"}</dd>
        </div>
        <div>
          <dt>Rule version</dt>
          <dd>{state.rule_version}</dd>
        </div>
        {state.death_reason ? (
          <div>
            <dt>Death reason</dt>
            <dd>{state.death_reason}</dd>
          </div>
        ) : null}
      </dl>

      <h3>Attributes</h3>
      <div className="metric-grid">
        {entries(state.attributes).map((item) => (
          <div className="metric" key={item.key}>
            <span>{item.key}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </div>

      <h3>Health</h3>
      <div className="metric-grid">
        {healthValue(state.health, "health_score") ? (
          <div className="metric">
            <span>health_score</span>
            <strong>{healthValue(state.health, "health_score")}</strong>
          </div>
        ) : null}
        {healthValue(state.health, "health_level") ? (
          <div className="metric">
            <span>health_level</span>
            <strong>{healthValue(state.health, "health_level")}</strong>
          </div>
        ) : null}
        {entries(state.health)
          .filter(([key]) => !["health_score", "health_level", "diseases", "warnings"].includes(key))
          .map((item) => (
            <div className="metric" key={item.key}>
              <span>{item.key}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
      </div>
      {diseases.length > 0 ? (
        <>
          <h4>Diseases</h4>
          <ul>
            {diseases.map((disease) => (
              <li key={disease}>{disease}</li>
            ))}
          </ul>
        </>
      ) : null}

      <h3>Assets</h3>
      <div className="metric-grid">
        {entries(state.assets).map((item) => (
          <div className="metric" key={item.key}>
            <span>{item.key}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}
