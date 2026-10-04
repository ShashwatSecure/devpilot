"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, Bot, History } from "lucide-react";

import { AgentIssueList } from "@/components/agent/agent-issue-list";
import { AgentRunPanel } from "@/components/agent/agent-run-panel";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  useAgentRun,
  useAgentRuns,
  useCreateAgentRun,
  useStreamAgentRun,
} from "@/hooks/use-agent";
import { useRepository } from "@/hooks/use-repos";
import type { AgentRun, GithubIssue } from "@/lib/api";

function statusVariant(status: AgentRun["status"]) {
  switch (status) {
    case "COMPLETED":
      return "default" as const;
    case "FAILED":
      return "destructive" as const;
    default:
      return "secondary" as const;
  }
}

export function AgentView({ repoId }: { repoId: string }) {
  const repoQuery = useRepository(repoId);
  const ready = repoQuery.data?.indexStatus === "READY";

  const createRun = useCreateAgentRun(repoId);
  const { start, running, progress } = useStreamAgentRun(repoId);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const runsQuery = useAgentRuns(repoId, ready);
  const activeRunQuery = useAgentRun(repoId, activeRunId);

  const handleSelectIssue = (issue: GithubIssue) => {
    createRun.mutate(issue.number, {
      onSuccess: (run) => {
        setActiveRunId(run.id);
        void start(run.id);
      },
    });
  };

  if (repoQuery.isLoading) {
    return (
      <AppShell title="Loading…">
        <Skeleton className="m-4 h-96 rounded-2xl" />
      </AppShell>
    );
  }

  if (!repoQuery.data) {
    return (
      <AppShell title="Repository unavailable">
        <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8">
          <Button render={<Link href="/dashboard" />}>Back to dashboard</Button>
        </div>
      </AppShell>
    );
  }

  const repo = repoQuery.data;

  return (
    <AppShell
      title={`${repo.fullName} · Issue Agent`}
      description="Pick an open issue and let the LangGraph agent propose a fix for you to review"
      actions={
        <Button
          variant="outline"
          size="sm"
          render={<Link href={`/chat/${repoId}`} />}
        >
          <ArrowLeft data-icon="inline-start" />
          Back to chat
        </Button>
      }
    >
      {!ready ? (
        <div className="flex flex-1 items-center justify-center p-8 text-sm text-muted-foreground">
          The repository must finish indexing before the agent can run.
        </div>
      ) : (
        <div className="grid min-h-0 flex-1 md:grid-cols-[22rem_1fr]">
          <aside className="flex min-h-0 flex-col border-b md:border-b-0 md:border-r">
            <Tabs defaultValue="issues" className="flex min-h-0 flex-1 flex-col">
              <div className="p-3">
                <TabsList className="w-full">
                  <TabsTrigger value="issues" className="flex-1">
                    <Bot data-icon="inline-start" />
                    Open issues
                  </TabsTrigger>
                  <TabsTrigger value="history" className="flex-1">
                    <History data-icon="inline-start" />
                    Runs
                  </TabsTrigger>
                </TabsList>
              </div>
              <Separator />
              <TabsContent value="issues" className="min-h-0 flex-1">
                <AgentIssueList
                  repoId={repoId}
                  onSelect={handleSelectIssue}
                  starting={createRun.isPending || running}
                />
              </TabsContent>
              <TabsContent value="history" className="min-h-0 flex-1">
                <ScrollArea className="h-full">
                  <div className="space-y-2 p-4">
                    {(runsQuery.data ?? []).map((run) => (
                      <button
                        key={run.id}
                        type="button"
                        onClick={() => setActiveRunId(run.id)}
                        className="w-full rounded-xl border px-3 py-2.5 text-left transition-colors hover:bg-muted"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate text-sm font-medium">
                            #{run.issueNumber} {run.issueTitle}
                          </span>
                          <Badge variant={statusVariant(run.status)}>
                            {run.status}
                          </Badge>
                        </div>
                      </button>
                    ))}
                    {runsQuery.isSuccess && (runsQuery.data ?? []).length === 0 && (
                      <p className="px-2 text-xs text-muted-foreground">
                        No agent runs yet.
                      </p>
                    )}
                  </div>
                </ScrollArea>
              </TabsContent>
            </Tabs>
          </aside>

          <section className="min-h-0 flex-1">
            <ScrollArea className="h-full">
              <div className="p-4">
                {activeRunQuery.data ? (
                  <AgentRunPanel
                    repoId={repoId}
                    run={activeRunQuery.data}
                    running={running}
                    progress={progress}
                  />
                ) : (
                  <div className="flex h-96 flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
                    <Bot className="size-8" />
                    <p>Pick an open issue on the left to run the agent.</p>
                  </div>
                )}
              </div>
            </ScrollArea>
          </section>
        </div>
      )}
    </AppShell>
  );
}
