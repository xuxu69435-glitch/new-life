import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../api/client";

type FamilyPanelProps = {
  lifeId: string;
};

type FamilyMember = {
  person_id: string;
  name: string;
  relation: string;
  age?: number;
  relation_score?: number;
};

type FamilyData = {
  relationship_status?: string;
  partner_relation?: number;
  parent_child_relation?: number;
  family_pressure?: number;
  children_count?: number;
  spouse?: FamilyMember | null;
  dating_partner?: FamilyMember | null;
  children?: FamilyMember[];
  parents?: FamilyMember[];
};

export function FamilyPanel({ lifeId }: FamilyPanelProps) {
  const familyQuery = useQuery({
    queryKey: ["family", lifeId],
    queryFn: () => apiClient.getFamily(lifeId),
  });

  const family = (familyQuery.data?.family ?? {}) as FamilyData;

  return (
    <section className="panel">
      <p className="eyebrow">Family</p>
      <h2>Family status</h2>
      {familyQuery.isLoading ? <p className="muted-text">Loading family...</p> : null}
      {familyQuery.isError ? <p className="error-text">{String(familyQuery.error.message)}</p> : null}
      {familyQuery.data ? (
        <>
          <p>
            <span>Relationship</span>
            <strong>{family.relationship_status ?? "unknown"}</strong>
          </p>
          <p>
            <span>Partner relation</span>
            <strong>{family.partner_relation ?? "-"}</strong>
          </p>
          <p>
            <span>Parent-child relation</span>
            <strong>{family.parent_child_relation ?? "-"}</strong>
          </p>
          <p>
            <span>Family pressure</span>
            <strong>{family.family_pressure ?? "-"}</strong>
          </p>
          <p>
            <span>Children</span>
            <strong>{family.children_count ?? family.children?.length ?? 0}</strong>
          </p>
          {family.spouse ? <p>Spouse: {family.spouse.name}</p> : null}
          {family.dating_partner ? <p>Partner: {family.dating_partner.name}</p> : null}
        </>
      ) : null}
    </section>
  );
}
