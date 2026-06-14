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
  onTransientGenerated?: (items: Recommendation[]) => void;
};

export function RecommendationsPanel({
  api,
  selectedGroupId,
  recommendations,
  onChanged,
  onError
  ,onTransientGenerated
}: RecommendationsPanelProps) {
  const toast = useToast();
  const [generating, setGenerating] = useState(false);
  // local copy so we can refresh immediately without relying entirely on parent reload
  const [localRecs, setLocalRecs] = useState<Recommendation[]>(recommendations ?? []);
  const [isTransient, setIsTransient] = useState(false);

  useEffect(() => {
    // If we're currently showing transient generated results, don't overwrite them
    // with the parent's empty persisted list. Only sync when not transient.
    if (!isTransient) setLocalRecs(recommendations ?? []);
  }, [recommendations]);

  // when selected group changes, try to load any saved transient results for that group
  useEffect(() => {
    if (!selectedGroupId) return;
    try {
      const key = `transient_recs:${selectedGroupId}`;
      const raw = window.localStorage.getItem(key);
      if (raw) {
        const parsed = JSON.parse(raw) as Recommendation[];
        if (Array.isArray(parsed) && parsed.length > 0) {
          setLocalRecs(parsed);
          setIsTransient(true);
          return;
        }
      }
    } catch (e) {
      // ignore
    }
    // otherwise ensure we start with persisted recommendations
    setIsTransient(false);
    setLocalRecs(recommendations ?? []);
  }, [selectedGroupId]);

  async function generate(persist: boolean = false) {
    if (!selectedGroupId) return;
    try {
      setGenerating(true);
      const result = await api.request<any[]>(`/groups/${selectedGroupId}/recommendations/generate?persist=${persist}`, {
        method: "POST",
      });
      // Immediately show transient results if present so the user sees them
      if (Array.isArray(result) && result.length > 0) {
        const items = result as Recommendation[];
        setLocalRecs(items);
        setIsTransient(true);
        try {
          if (selectedGroupId) {
            window.localStorage.setItem(`transient_recs:${selectedGroupId}`, JSON.stringify(items));
          }
        } catch (e) {
          // ignore
        }
        // inform parent so it can temporarily show these items as its recommendations prop
        if (typeof onTransientGenerated === "function") {
          try {
            onTransientGenerated(items);
          } catch (e) {
            // ignore parent errors
          }
        }
      }
      if (persist) {
        // If persisting, refresh persisted list so UI reflects stored recommendations
        try {
          const updated = selectedGroupId
            ? await api.request<Recommendation[]>(`/groups/${selectedGroupId}/recommendations`)
            : result ?? [];
          setLocalRecs(updated ?? []);
          setIsTransient(false);
        } catch (e) {
          // if fetch failed, leave transient results if present
          if (Array.isArray(result) && result.length > 0) {
            setLocalRecs(result ?? []);
            setIsTransient(true);
            try {
              if (selectedGroupId) {
                window.localStorage.setItem(`transient_recs:${selectedGroupId}`, JSON.stringify(result));
              }
            } catch (e) {}
          }
        }
        onChanged();
      }

      const genCount = Array.isArray(result) ? result.length : 0;
      if (genCount === 0) {
        toast.push("No recommendations were generated", "info");
      } else {
        toast.push(`Generated ${genCount}${isTransient ? ' — showing transient results' : ''}`, "success");
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
  setLocalRecs([]);
  onChanged();
  try { window.localStorage.removeItem(`transient_recs:${selectedGroupId}`); } catch (e) {}
  toast.push("Recommendations cleared", "success");
    } catch (caught) {
      const msg = caught instanceof Error ? caught.message : "Could not clear recommendations";
      onError(msg);
      toast.push(msg, "error");
    }
  }

  async function deleteRecommendation(recId: string) {
    try {
      await api.delete(`/recommendations/${recId}`);
  // optimistically remove from local list and ask parent to refresh
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

  function clearTransient() {
    if (!selectedGroupId) return;
    try { window.localStorage.removeItem(`transient_recs:${selectedGroupId}`); } catch (e) {}
    setLocalRecs([]);
    setIsTransient(false);
    toast.push('Transient recommendations cleared', 'success');
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
          <Button disabled={!selectedGroupId || generating} onClick={() => void generate(false)} title="Generate recommendations (does not import games)">
            <Sparkles className="h-4 w-4" />
            {generating ? 'Generating...' : 'Generate'}
          </Button>
          <Button disabled={!selectedGroupId || generating} onClick={() => void generate(true)} title="Generate and persist recommendations (imports games into DB)">
            <Sparkles className="h-4 w-4" />
            {generating ? 'Saving...' : 'Generate & Persist'}
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <Button disabled={!selectedGroupId} onClick={() => setClearConfirmOpen(true)}>Clear</Button>
          <Button disabled={!selectedGroupId || !isTransient} variant="outline" onClick={() => clearTransient()}>Clear transient</Button>
          {isTransient ? <span className="text-sm text-muted-foreground">Transient results (not saved)</span> : null}
        </div>
        <div className="space-y-2">
          {localRecs.map((recommendation) => (
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
          ))}
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

