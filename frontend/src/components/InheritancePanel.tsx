import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../api/client";

type InheritancePanelProps = {
  lifeId: string;
};

export function InheritancePanel({ lifeId }: InheritancePanelProps) {
  const inheritanceQuery = useQuery({
    queryKey: ["inheritance", lifeId],
    queryFn: () => apiClient.getInheritance(lifeId),
  });

  return (
    <section className="panel">
      <p className="eyebrow">Inheritance</p>
      <h2>Result placeholder</h2>
      {inheritanceQuery.isLoading ? <p className="muted-text">Loading inheritance...</p> : null}
      {inheritanceQuery.isError ? <p className="error-text">{String(inheritanceQuery.error.message)}</p> : null}
      {inheritanceQuery.data ? <pre className="data-preview">{JSON.stringify(inheritanceQuery.data, null, 2)}</pre> : null}
    </section>
  );
}
