import type { LifeState } from "../api/types";

type StatusPanelProps = {
  state: LifeState;
};

function entries(record: Record<string, unknown>) {
  return Object.entries(record).map(([key, value]) => ({ key, value: String(value) }));
}

export function StatusPanel({ state }: StatusPanelProps) {
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
        {entries(state.health).map((item) => (
          <div className="metric" key={item.key}>
            <span>{item.key}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </div>

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
