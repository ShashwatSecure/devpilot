"use client";

import { use } from "react";

import { AgentView } from "@/components/agent/agent-view";
import { RequireAuth } from "@/components/providers/require-auth";

export default function AgentPage({
  params,
}: {
  params: Promise<{ repoId: string }>;
}) {
  const { repoId } = use(params);

  return (
    <RequireAuth>
      <AgentView repoId={repoId} />
    </RequireAuth>
  );
}
