import { cn } from "@/lib/utils";

type Tone = "default" | "good" | "critical" | "warning";

const toneClasses: Record<Tone, string> = {
  default: "text-ink",
  good: "text-status-good",
  critical: "text-status-critical",
  warning: "text-status-warning",
};

export function StatTile({
  label,
  value,
  sublabel,
  tone = "default",
}: {
  label: string;
  value: string | number;
  sublabel?: string;
  tone?: Tone;
}) {
  return (
    <div className="min-w-0 rounded-card border border-line bg-card px-3 py-3 sm:px-5 sm:py-4">
      <p className="truncate font-mono text-[0.6rem] uppercase tracking-wide text-ink-dim sm:text-[0.65rem]">
        {label}
      </p>
      <p className={cn("tabular mt-1 truncate font-mono text-2xl font-semibold sm:text-3xl", toneClasses[tone])}>
        {value}
      </p>
      {sublabel && <p className="mt-1 truncate text-xs text-ink-dim">{sublabel}</p>}
    </div>
  );
}
