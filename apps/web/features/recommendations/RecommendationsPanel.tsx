"use client";

import { Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiClient, Recommendation } from "@/lib/api";
import { useState, useEffect } from "react";
import { ConfirmDialog } from "@/components/ui/confirm";
import { useToast } from "@/components/ui/toast";

type RecommendationsPanelProps = {
  api: ApiClient;
  selectedGroupId: string | null;
  recommendations: Recommendation[];
  onChanged: () => void;
  onError: (message: string) => void;
};

export function RecommendationsPanel({
  api,
  selectedGroupId,
  recommendations,
  onChanged,
  onError
}: RecommendationsPanelProps) {
  const toast = useToast();
  const [generating, setGenerating] = useState(false);
  const [localRecs, setLocalRecs] = useState<Recommendation[]>(recommendations ?? []);

  useEffect(() => {
    if (!selectedGroupId) {
      setLocalRecs(recommendations ?? []);
      return;
    }
    try {
      const key = `transient_recs:${selectedGroupId}`;
      const raw = window.localStorage.getItem(key);
      if (raw) {
        const parsed = JSON.parse(raw) as Recommendation[];
        if (Array.isArray(parsed) && parsed.length > 0) {
          setLocalRecs(parsed);
          return;
        }
      }
    } catch (e) {
      // ignore
    }
    setLocalRecs(recommendations ?? []);
  }, [selectedGroupId, recommendations]);

  async function generate() {
    if (!selectedGroupId) return;
    try {
      setGenerating(true);
      const result = await api.request<any[]>(`/groups/${selectedGroupId}/recommendations/generate?persist=false`, {
        method: "POST",
      });
      if (Array.isArray(result)) {
        const items = result as Recommendation[];
        setLocalRecs(items);
        try {
          window.localStorage.setItem(`transient_recs:${selectedGroupId}`, JSON.stringify(items));
        } catch (e) {}
      }
      onChanged();
      const genCount = Array.isArray(result) ? result.length : 0;
      if (genCount === 0) {
        toast.push("No recommendations were generated", "info");
      } else {
        toast.push(`Generated ${genCount} recommendations`, "success");
      }
    } catch (caught) {
      const msg = caught instanceof Error ? caught.message : "Could not generate recommendations";
      onError(msg);
      toast.push(msg, "error");
    } finally {
      setGenerating(false);
    }
  }

  async function clearGroupRecommendations() {
    if (!selectedGroupId) return;
    try {
      await api.delete(`/groups/${selectedGroupId}/recommendations`);
      try {
        window.localStorage.removeItem(`transient_recs:${selectedGroupId}`);
      } catch (e) {}
      setLocalRecs([]);
      onChanged();
      toast.push("Recommendations cleared", "success");
    } catch (caught) {
      const msg = caught instanceof Error ? caught.message : "Could not clear recommendations";
      onError(msg);
      toast.push(msg, "error");
    }
  }

  async function deleteRecommendation(recId: string) {
    const target = localRecs.find((r) => r.id === recId);
    if (target?.transient) {
      const updated = localRecs.filter((r) => r.id !== recId);
      setLocalRecs(updated);
      try {
        if (selectedGroupId) {
          window.localStorage.setItem(`transient_recs:${selectedGroupId}`, JSON.stringify(updated));
        }
      } catch (e) {}
      toast.push("Recommendation removed", "success");
      return;
    }

    try {
      await api.delete(`/recommendations/${recId}`);
      setLocalRecs(localRecs.filter((r) => r.id !== recId));
      onChanged();
      toast.push("Recommendation removed", "success");
    } catch (caught) {
      const msg = caught instanceof Error ? caught.message : "Could not delete recommendation";
      onError(msg);
      toast.push(msg, "error");
    }
  }

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [clearConfirmOpen, setClearConfirmOpen] = useState(false);

  function requestDelete(recId: string) {
    setDeleteTarget(recId);
    setConfirmOpen(true);
  }

  function onConfirmDelete() {
    if (!deleteTarget) return setConfirmOpen(false);
    deleteRecommendation(deleteTarget);
    setConfirmOpen(false);
    setDeleteTarget(null);
  }

  function onConfirmClear() {
    if (!selectedGroupId) return setClearConfirmOpen(false);
    clearGroupRecommendations();
    setClearConfirmOpen(false);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-secondary" />
          Recommendations
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Button disabled={!selectedGroupId || generating} onClick={() => void generate()} title="Generate recommendations for this group">
            <Sparkles className="h-4 w-4" />
            {generating ? 'Generating...' : 'Generate'}
          </Button>
          <Button disabled={!selectedGroupId} onClick={() => setClearConfirmOpen(true)} variant="outline">Clear</Button>
        </div>
        <div className="space-y-2">
          {generating ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="rounded-md border bg-background p-3 animate-pulse">
                  <div className="flex items-center justify-between gap-3">
                    <div className="h-4 w-1/3 bg-muted rounded"></div>
                    <div className="h-5 w-12 bg-muted rounded-full"></div>
                  </div>
                  <div className="mt-3 space-y-2">
                    <div className="h-3 w-full bg-muted rounded"></div>
                    <div className="h-3 w-5/6 bg-muted rounded"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : localRecs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 px-4 text-center rounded-lg border border-dashed bg-muted/40">
              <p className="text-sm font-medium text-muted-foreground">No recommendations yet</p>
              <p className="text-xs text-muted-foreground mt-1 max-w-[240px]">
                {!selectedGroupId 
                  ? "Select a group to see or generate cooperative game recommendations."
                  : "Click 'Generate' to get AI recommendations for this group."}
              </p>
            </div>
          ) : (
            localRecs.map((recommendation) => (
              <div className="rounded-md border bg-background p-3" key={recommendation.id}>
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium">{recommendation.game.title}</span>
                  <div className="flex items-center gap-2">
                    <Badge>{Math.round(recommendation.score * 100)}%</Badge>
                    <Button className="h-7 w-7 p-0" onClick={() => requestDelete(recommendation.id)}>×</Button>
                  </div>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{recommendation.explanation}</p>
              </div>
            ))
          )}
        </div>
      </CardContent>
      <ConfirmDialog
        open={confirmOpen}
        title="Delete recommendation"
        description="Remove this recommendation from the group."
        onCancel={() => setConfirmOpen(false)}
        onConfirm={onConfirmDelete}
      />
      <ConfirmDialog
        open={clearConfirmOpen}
        title="Clear recommendations"
        description="This will remove all recommendations for the selected group."
        onCancel={() => setClearConfirmOpen(false)}
        onConfirm={onConfirmClear}
      />
    </Card>
  );
}

