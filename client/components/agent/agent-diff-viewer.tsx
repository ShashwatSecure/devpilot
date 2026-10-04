import { cn } from "@/lib/utils";

/** Minimal unified-diff renderer: colors +/- lines, no external diff library needed. */
export function AgentDiffViewer({ diff }: { diff: string }) {
  if (!diff.trim()) {
    return (
      <p className="text-sm text-muted-foreground">No diff was proposed.</p>
    );
  }

  const lines = diff.split("\n");

  return (
    <pre className="max-h-[28rem] overflow-auto rounded-lg bg-muted p-3 text-xs leading-relaxed">
      <code>
        {lines.map((line, i) => (
          <div
            key={i}
            className={cn(
              "whitespace-pre-wrap",
              line.startsWith("+") && !line.startsWith("+++") &&
                "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
              line.startsWith("-") && !line.startsWith("---") &&
                "bg-red-500/10 text-red-700 dark:text-red-400",
              line.startsWith("@@") && "text-sky-600 dark:text-sky-400"
            )}
          >
            {line || " "}
          </div>
        ))}
      </code>
    </pre>
  );
}
