import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../api/client";

type FamilyPanelProps = {
  lifeId: string;
};

export function FamilyPanel({ lifeId }: FamilyPanelProps) {
  const familyQuery = useQuery({
    queryKey: ["family", lifeId],
    queryFn: () => apiClient.getFamily(lifeId),
  });

  return (
    <section className="panel">
      <p className="eyebrow">Family tree</p>
      <h2>Family placeholder</h2>
      {familyQuery.isLoading ? <p className="muted-text">Loading family...</p> : null}
      {familyQuery.isError ? <p className="error-text">{String(familyQuery.error.message)}</p> : null}
      {familyQuery.data ? <pre className="data-preview">{JSON.stringify(familyQuery.data, null, 2)}</pre> : null}
    </section>
  );
}
