import { cn } from "@/lib/utils";

type Tone = "good" | "warning" | "critical" | "neutral";

const toneClasses: Record<Tone, string> = {
  good: "bg-status-good-wash text-status-good",
  warning: "bg-status-warning-wash text-status-warning",
  critical: "bg-status-critical-wash text-status-critical",
  neutral: "bg-line text-ink-dim",
};

export function Badge({ tone, label }: { tone: Tone; label: string }) {
  return (
    <span className={cn("inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium", toneClasses[tone])}>
      {label}
    </span>
  );
}

/** Warehouse/location occupancy status -> the same tone everywhere it's shown. */
export function OccupancyBadge({ status }: { status: string }) {
  const map: Record<string, { tone: Tone; label: string }> = {
    empty: { tone: "neutral", label: "Empty" },
    underutilized: { tone: "warning", label: "Underutilized" },
    normal: { tone: "good", label: "Normal" },
    overloaded: { tone: "critical", label: "Overloaded" },
    no_capacity_set: { tone: "neutral", label: "No Capacity Set" },
  };
  const entry = map[status] ?? { tone: "neutral" as Tone, label: status };
  return <Badge tone={entry.tone} label={entry.label} />;
}
