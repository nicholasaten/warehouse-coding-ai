"use client";

import { useEffect, useState } from "react";
import { GitMerge, PackageX, Sparkles, TrendingDown, TrendingUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiJson, ApiError } from "@/lib/api-client";
import type { Recommendation } from "@/lib/types";

const CATEGORY_ICON: Record<Recommendation["category"], typeof GitMerge> = {
  merge_opportunity: GitMerge,
  redundant_warehouse: PackageX,
  underutilized: TrendingDown,
  overloaded: TrendingUp,
};

export function RecommendationsPanel() {
  const [recommendations, setRecommendations] = useState<Recommendation[] | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await apiJson<Recommendation[]>("/recommendations");
        setRecommendations(data);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Could not load recommendations.");
      }
    })();
  }, []);

  async function handleGenerate() {
    setIsGenerating(true);
    setError(null);
    try {
      const data = await apiJson<Recommendation[]>("/recommendations/generate", { method: "POST" });
      setRecommendations(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not generate recommendations.");
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-signal" />
          <CardTitle>AI Optimization Recommendations</CardTitle>
        </div>
        <Button variant="secondary" onClick={handleGenerate} disabled={isGenerating}>
          {isGenerating ? "Analyzing…" : "Generate"}
        </Button>
      </CardHeader>
      <CardContent>
        {error && <p className="text-sm text-status-critical">{error}</p>}

        {!error && recommendations === null && <p className="text-sm text-ink-dim">Loading…</p>}

        {!error && recommendations !== null && recommendations.length === 0 && (
          <p className="text-sm text-ink-dim">
            No recommendations right now. Click Generate to analyze warehouses and locations for optimization
            opportunities.
          </p>
        )}

        {recommendations !== null && recommendations.length > 0 && (
          <ul className="space-y-3">
            {recommendations.map((rec) => {
              const Icon = CATEGORY_ICON[rec.category];
              return (
                <li key={rec.id} className="rounded-md border border-line bg-accent-wash/20 p-3">
                  <div className="flex items-center gap-2 text-sm font-medium text-ink">
                    <Icon className="h-4 w-4 text-signal" />
                    {rec.title}
                  </div>
                  <p className="mt-1.5 text-sm leading-relaxed text-ink-dim">{rec.explanation}</p>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
