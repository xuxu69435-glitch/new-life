import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import type { InheritanceResult, PlayableHeirsResponse } from "../api/types";

type InheritancePanelProps = {
  lifeId: string;
};

export function InheritancePanel({ lifeId }: InheritancePanelProps) {
  const inheritanceQuery = useQuery({
    queryKey: ["inheritance", lifeId],
    queryFn: () => apiClient.getInheritance(lifeId),
  });
  const heirsQuery = useQuery({
    queryKey: ["playable-heirs", lifeId],
    queryFn: () => apiClient.getPlayableHeirs(lifeId),
  });

  const inheritance = inheritanceQuery.data as InheritanceResult | undefined;
  const heirs = heirsQuery.data as PlayableHeirsResponse | undefined;

  return (
    <section className="panel">
      <p className="eyebrow">Inheritance</p>
      <h2>Estate settlement</h2>
      {inheritanceQuery.isLoading ? <p className="muted-text">Loading inheritance...</p> : null}
      {inheritanceQuery.isError ? <p className="error-text">{String(inheritanceQuery.error.message)}</p> : null}
      {inheritance && inheritance.status !== "not_available" ? (
        <>
          <dl className="stat-list">
            <div>
              <dt>Gross estate</dt>
              <dd>{inheritance.gross_estate}</dd>
            </div>
            <div>
              <dt>Tax rate</dt>
              <dd>{inheritance.tax_rate}</dd>
            </div>
            <div>
              <dt>Tax amount</dt>
              <dd>{inheritance.tax_amount}</dd>
            </div>
            <div>
              <dt>Net estate</dt>
              <dd>{inheritance.net_estate}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{inheritance.status}</dd>
            </div>
          </dl>
          {inheritance.heirs.length > 0 ? (
            <>
              <h3>Heirs</h3>
              <ul>
                {inheritance.heirs.map((heir) => (
                  <li key={heir.person_id}>
                    {heir.relation}: {heir.person_id} — {heir.amount} ({heir.share_ratio})
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </>
      ) : (
        <p className="muted-text">No inheritance result yet.</p>
      )}

      <h3>Playable heirs</h3>
      {heirsQuery.isLoading ? <p className="muted-text">Loading heirs...</p> : null}
      {heirs && heirs.playable_heirs.length > 0 ? (
        <ul>
          {heirs.playable_heirs.map((heir) => (
            <li key={heir.person_id}>
              {heir.name} ({heir.relation}) — inheritance {heir.inheritance_amount}
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted-text">{heirs?.status ?? "No playable heirs"}</p>
      )}
    </section>
  );
}
