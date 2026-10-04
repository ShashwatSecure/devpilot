"use client";

import { formatDistanceToNow } from "date-fns";
import { ExternalLink, MessageSquare, Play } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { useAgentIssues } from "@/hooks/use-agent";
import type { GithubIssue } from "@/lib/api";

export function AgentIssueList({
  repoId,
  onSelect,
  starting,
}: {
  repoId: string;
  onSelect: (issue: GithubIssue) => void;
  starting: boolean;
}) {
  const issuesQuery = useAgentIssues(repoId);

  if (issuesQuery.isLoading) {
    return (
      <div className="space-y-2 p-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-xl" />
        ))}
      </div>
    );
  }

  if (issuesQuery.isError) {
    return (
      <p className="p-4 text-sm text-destructive">
        {(issuesQuery.error as Error).message}
      </p>
    );
  }

  const issues = issuesQuery.data ?? [];

  if (issues.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 p-8 text-center text-sm text-muted-foreground">
        <MessageSquare className="size-8" />
        <p>No open issues on this repository.</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="space-y-2 p-4">
        {issues.map((issue) => (
          <Card key={issue.number} className="ring-foreground/10">
            <CardContent className="flex items-start justify-between gap-3 px-4">
              <div className="min-w-0 space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">#{issue.number}</Badge>
                  {issue.createdAt && (
                    <span className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(issue.createdAt), {
                        addSuffix: true,
                      })}
                    </span>
                  )}
                </div>
                <p className="truncate text-sm font-medium">{issue.title}</p>
                <p className="text-xs text-muted-foreground">
                  {issue.authorLogin ? `by ${issue.authorLogin} · ` : ""}
                  {issue.commentsCount} comment
                  {issue.commentsCount === 1 ? "" : "s"}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                {issue.htmlUrl && (
                  <Button
                    size="icon-sm"
                    variant="ghost"
                    render={
                      <a href={issue.htmlUrl} target="_blank" rel="noreferrer" />
                    }
                    aria-label="Open on GitHub"
                  >
                    <ExternalLink />
                  </Button>
                )}
                <Button
                  size="sm"
                  disabled={starting}
                  onClick={() => onSelect(issue)}
                >
                  <Play data-icon="inline-start" />
                  Run agent
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </ScrollArea>
  );
}
