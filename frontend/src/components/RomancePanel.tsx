import type { LifeState } from "../api/types";

type RomancePanelProps = {
  state: LifeState;
};

type RomanceCandidateView = {
  candidate_id?: string;
  name?: string;
  status?: string;
  favor?: number;
  trust?: number;
  attraction?: number;
  conflict?: number;
  familiarity?: number;
  tags?: string[];
};

type RomanceRelationshipView = {
  relationship_id?: string;
  partner_name?: string;
  status?: string;
  favor?: number;
  trust?: number;
  intimacy?: number;
  conflict?: number;
  stability?: number;
  years_together?: number;
  engagement_intent?: boolean;
};

type RomanceSummary = {
  status?: string;
  candidate_count?: number;
  current_partner_name?: string;
  years_single?: number;
  years_in_current_relationship?: number;
  recent_candidates?: RomanceCandidateView[];
  active_candidates?: RomanceCandidateView[];
  current_relationship?: RomanceRelationshipView | null;
  recent_changes?: Array<Record<string, unknown>>;
  history_highlights?: Array<Record<string, unknown>>;
};

const EMPTY_ROMANCE: RomanceSummary = {
  status: "single",
  candidate_count: 0,
  current_partner_name: "",
  years_single: 0,
  years_in_current_relationship: 0,
  recent_candidates: [],
  active_candidates: [],
  current_relationship: null,
  recent_changes: [],
  history_highlights: [],
};

export function RomancePanel({ state }: RomancePanelProps) {
  const romance = (state.romance ?? {}) as { romance_summary?: RomanceSummary };
  const summary = romance.romance_summary ?? EMPTY_ROMANCE;
  const current = summary.current_relationship ?? null;
  const candidates = summary.active_candidates ?? [];

  return (
    <section className="panel">
      <p className="eyebrow">Romance</p>
      <h2>Romance status</h2>
      <p>
        <span>Status</span>
        <strong>{summary.status ?? "single"}</strong>
      </p>
      <p>
        <span>Candidates</span>
        <strong>{summary.candidate_count ?? 0}</strong>
      </p>
      <p>
        <span>Years single</span>
        <strong>{summary.years_single ?? 0}</strong>
      </p>
      <p>
        <span>Years together</span>
        <strong>{summary.years_in_current_relationship ?? 0}</strong>
      </p>

      {current ? (
        <div>
          <h3>Current relationship</h3>
          <p>
            <strong>{current.partner_name}</strong> · {current.status}
          </p>
          <p>
            favor {current.favor} · trust {current.trust} · intimacy {current.intimacy} · conflict {current.conflict} ·
            stability {current.stability}
          </p>
        </div>
      ) : (
        <p className="muted-text">No current romantic relationship.</p>
      )}

      {(summary.recent_candidates ?? []).length > 0 ? (
        <div>
          <h3>New this year</h3>
          <ul>
            {summary.recent_candidates?.map((item) => (
              <li key={item.candidate_id ?? item.name}>
                {item.name} · {item.status}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {candidates.length > 0 ? (
        <div>
          <h3>Candidates</h3>
          <ul>
            {candidates.map((item) => (
              <li key={item.candidate_id ?? item.name}>
                <strong>{item.name}</strong> ({item.status}) · favor {item.favor} · trust {item.trust} · attraction{" "}
                {item.attraction}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
