"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";

import { api, type AgentRun } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import {
  streamAgentRun,
  type AgentProgressEvent,
} from "@/lib/stream-agent";
import { toast } from "@/components/ui/toast";

export function useAgentIssues(repoId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.agent.issues(repoId),
    queryFn: () => api.listAgentIssues(repoId),
    enabled: Boolean(repoId) && enabled,
    staleTime: 30_000,
  });
}

export function useAgentRuns(repoId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.agent.runs(repoId),
    queryFn: () => api.listAgentRuns(repoId),
    enabled: Boolean(repoId) && enabled,
  });
}

export function useCreateAgentRun(repoId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (issueNumber: number) => api.createAgentRun(repoId, issueNumber),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.agent.runs(repoId),
      });
    },
    onError: (error: Error) => {
      toast.add({
        title: "Could not start agent run",
        description: error.message,
        type: "error",
      });
    },
  });
}

/** Starts + streams a PENDING agent run's progress until it completes or fails. */
export function useStreamAgentRun(repoId: string) {
  const queryClient = useQueryClient();
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<AgentProgressEvent[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(
    async (runId: string) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setRunning(true);
      setProgress([]);

      try {
        await streamAgentRun(repoId, runId, {
          signal: controller.signal,
          onProgress: (event) => setProgress((prev) => [...prev, event]),
          onResult: (run: AgentRun) => {
            queryClient.setQueryData(queryKeys.agent.run(repoId, runId), run);
            void queryClient.invalidateQueries({
              queryKey: queryKeys.agent.runs(repoId),
            });
          },
          onError: (err) => {
            toast.add({
              title: "Agent run failed",
              description: err.message,
              type: "error",
            });
          },
        });
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        toast.add({
          title: "Agent run failed",
          description: err instanceof Error ? err.message : "Unknown error",
          type: "error",
        });
      } finally {
        setRunning(false);
      }
    },
    [repoId, queryClient]
  );

  return { start, running, progress };
}

export function useAgentRun(repoId: string, runId: string | null) {
  return useQuery({
    queryKey: queryKeys.agent.run(repoId, runId ?? ""),
    queryFn: () => api.getAgentRun(repoId, runId!),
    enabled: Boolean(repoId) && Boolean(runId),
  });
}

export function usePostAgentComment(repoId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ runId, commentBody }: { runId: string; commentBody?: string }) =>
      api.postAgentComment(repoId, runId, commentBody),
    onSuccess: (run) => {
      queryClient.setQueryData(queryKeys.agent.run(repoId, run.id), run);
      void queryClient.invalidateQueries({ queryKey: queryKeys.agent.runs(repoId) });
      toast.add({
        title: "Comment posted",
        description: "The AI analysis was posted to the GitHub issue.",
        type: "success",
      });
    },
    onError: (error: Error) => {
      toast.add({
        title: "Could not post comment",
        description: error.message,
        type: "error",
      });
    },
  });
}
