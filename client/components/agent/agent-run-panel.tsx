"use client";

import { CheckCircle2, Loader2, MessageSquarePlus, ShieldAlert } from "lucide-react";

import { AgentDiffViewer } from "@/components/agent/agent-diff-viewer";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { usePostAgentComment } from "@/hooks/use-agent";
import type { AgentProgressEvent } from "@/lib/stream-agent";
import type { AgentRun } from "@/lib/api";

const confidenceVariant: Record<string, "default" | "secondary" | "destructive"> = {
  high: "default",
  medium: "secondary",
  low: "destructive",
};

export function AgentRunPanel({
  repoId,
  run,
  running,
  progress,
}: {
  repoId: string;
  run: AgentRun | undefined;
  running: boolean;
  progress: AgentProgressEvent[];
}) {
  const postComment = usePostAgentComment(repoId);

  if (!run) return null;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            {running ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <CheckCircle2 className="size-4 text-emerald-500" />
            )}
            Agent progress
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="space-y-1.5 text-sm">
            {progress.map((p, i) => (
              <li key={i} className="flex items-center gap-2 text-muted-foreground">
                <span className="size-1.5 shrink-0 rounded-full bg-foreground/40" />
                {p.message}
              </li>
            ))}
            {progress.length === 0 && running && (
              <li className="text-muted-foreground">Starting…</li>
            )}
          </ol>
        </CardContent>
      </Card>

      {run.status === "FAILED" && (
        <Card className="border-destructive/40">
          <CardContent className="flex items-start gap-2 pt-4 text-sm text-destructive">
            <ShieldAlert className="mt-0.5 size-4 shrink-0" />
            <p>{run.errorMessage ?? "The agent run failed."}</p>
          </CardContent>
        </Card>
      )}

      {run.status === "COMPLETED" && (
        <>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Summary</CardTitle>
              <div className="flex items-center gap-2">
                {run.issueType && <Badge variant="outline">{run.issueType}</Badge>}
                {run.confidence && (
                  <Badge variant={confidenceVariant[run.confidence] ?? "secondary"}>
                    {run.confidence} confidence
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p>{run.summary}</p>
              <Separator />
              <div>
                <p className="mb-1 font-medium">Root cause</p>
                <p className="text-muted-foreground">{run.rootCause}</p>
              </div>
              {run.plan.length > 0 && (
                <div>
                  <p className="mb-1 font-medium">Plan</p>
                  <ol className="list-decimal space-y-1 pl-4 text-muted-foreground">
                    {run.plan.map((step, i) => (
                      <li key={i}>{step}</li>
                    ))}
                  </ol>
                </div>
              )}
              {run.iterations > 0 && (
                <p className="text-xs text-muted-foreground">
                  Revised {run.iterations} time{run.iterations === 1 ? "" : "s"} after
                  self-review before finalizing.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Proposed diff (not applied)</CardTitle>
            </CardHeader>
            <CardContent>
              <AgentDiffViewer diff={run.proposedDiff ?? ""} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">PR description</CardTitle>
            </CardHeader>
            <CardContent className="whitespace-pre-wrap text-sm text-muted-foreground">
              {run.prDescription}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Suggested tests</CardTitle>
            </CardHeader>
            <CardContent className="whitespace-pre-wrap text-sm text-muted-foreground">
              {run.testSuggestions}
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex flex-col items-start gap-3 pt-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-muted-foreground">
                Nothing has been posted to GitHub yet. Review the proposal above before
                sharing it on the issue — the agent never posts automatically.
              </p>
              {run.githubCommentPosted ? (
                <Badge variant="secondary">
                  <CheckCircle2 data-icon="inline-start" />
                  Posted to GitHub
                </Badge>
              ) : (
                <AlertDialog>
                  <AlertDialogTrigger
                    render={
                      <Button size="sm" disabled={postComment.isPending}>
                        <MessageSquarePlus data-icon="inline-start" />
                        Post as GitHub comment
                      </Button>
                    }
                  />
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Post AI-generated analysis?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This will publish the summary, root cause, and proposed diff above as
                        a comment on issue #{run.issueNumber}, clearly labeled as
                        AI-generated. This action cannot be undone from DevPilot.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={() => postComment.mutate({ runId: run.id })}
                      >
                        Post comment
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
