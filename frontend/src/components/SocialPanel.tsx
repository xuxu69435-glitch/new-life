import type { LifeState } from "../api/types";

type SocialPanelProps = {
  state: LifeState;
};

type SocialRelationshipView = {
  relationship_id?: string;
  person_name?: string;
  relationship_type?: string;
  status?: string;
  closeness?: number;
  trust?: number;
  conflict?: number;
  familiarity?: number;
  tags?: string[];
  importance?: number;
};

type SocialSummary = {
  friend_count?: number;
  important_relationship_count?: number;
  active_relationship_count?: number;
  recent_new_relationships?: SocialRelationshipView[];
  recent_changed_relationships?: SocialRelationshipView[];
  active_relationships?: SocialRelationshipView[];
};

const EMPTY_SOCIAL: SocialSummary = {
  friend_count: 0,
  important_relationship_count: 0,
  active_relationship_count: 0,
  recent_new_relationships: [],
  recent_changed_relationships: [],
  active_relationships: [],
};

export function SocialPanel({ state }: SocialPanelProps) {
  const social = (state.social ?? {}) as { social_summary?: SocialSummary };
  const summary = social.social_summary ?? EMPTY_SOCIAL;
  const activeRelationships = summary.active_relationships ?? [];

  return (
    <section className="panel">
      <p className="eyebrow">Social</p>
      <h2>Social network</h2>
      <p>
        <span>Friends</span>
        <strong>{summary.friend_count ?? 0}</strong>
      </p>
      <p>
        <span>Important relations</span>
        <strong>{summary.important_relationship_count ?? 0}</strong>
      </p>
      <p>
        <span>Active relations</span>
        <strong>{summary.active_relationship_count ?? 0}</strong>
      </p>

      {(summary.recent_new_relationships ?? []).length > 0 ? (
        <div>
          <h3>New this year</h3>
          <ul>
            {summary.recent_new_relationships?.map((item) => (
              <li key={item.relationship_id ?? item.person_name}>
                {item.person_name} · {item.relationship_type}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {(summary.recent_changed_relationships ?? []).length > 0 ? (
        <div>
          <h3>Changed this year</h3>
          <ul>
            {summary.recent_changed_relationships?.map((item) => (
              <li key={item.relationship_id ?? item.person_name}>
                {item.person_name} · {item.relationship_type} · {item.status}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {activeRelationships.length > 0 ? (
        <div>
          <h3>Relationships</h3>
          <ul>
            {activeRelationships.map((item) => (
              <li key={item.relationship_id ?? item.person_name}>
                <strong>{item.person_name}</strong> ({item.relationship_type}) · closeness {item.closeness} · trust{" "}
                {item.trust} · conflict {item.conflict}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="muted-text">No active social relationships yet.</p>
      )}
    </section>
  );
}
