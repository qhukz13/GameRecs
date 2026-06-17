"use client";

import { FormEvent } from "react";
import { Gamepad2, Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiClient, Game, Review } from "@/lib/api";
import { useState, useMemo, useEffect } from "react";
import { ConfirmDialog } from "@/components/ui/confirm";
import { useToast } from "@/components/ui/toast";

type GamesPanelProps = {
  api: ApiClient;
  games: Game[];
  selectedGameId: string | null;
  onSelectGame: (gameId: string) => void;
  onChanged: () => void;
  onError: (message: string) => void;
  reviews?: Review[];
  selectedGroupId?: string | null;
};

function splitList(value: FormDataEntryValue | null) {
  return String(value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function GamesPanel({
  api,
  games,
  selectedGameId,
  onSelectGame,
  onChanged,
  onError,
  reviews = [],
  selectedGroupId = null
}: GamesPanelProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [steamQuery, setSteamQuery] = useState("");
  const [steamResults, setSteamResults] = useState<any[]>([]);
  const toast = useToast();

  const filteredGames = games;

  async function createGame(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const newGame = await api.request<Game>("/games", {
        method: "POST",
        body: JSON.stringify({
          external_id: String(form.get("external_id") || "") || null,
          title: String(form.get("title")),
          description: String(form.get("description")),
          genres: splitList(form.get("genres")),
          tags: splitList(form.get("tags")),
          players_min: Number(form.get("players_min")),
          players_max: Number(form.get("players_max")),
          group_id: selectedGroupId || null
        })
      });
      if (event.currentTarget) event.currentTarget.reset();
      if (newGame && newGame.id) {
        onSelectGame(newGame.id);
      }
      onChanged();
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Could not create game");
    }
  }

  async function searchSteam() {
    if (!steamQuery) return;
    try {
      const results = await api.request<any[]>(`/external/steam/search?q=${encodeURIComponent(steamQuery)}`);
      setSteamResults(results ?? []);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Steam search failed");
    }
  }

  async function importSteam(appId: string) {
    try {
      const newGame = await api.request<Game>(`/external/steam/import`, {
        method: "POST",
        body: JSON.stringify({
          id: appId,
          group_id: selectedGroupId || null
        }),
      });
      toast.push("Imported game from Steam", "success");
      setSteamResults([]);
      setSteamQuery("");
      if (newGame && newGame.id) {
        onSelectGame(newGame.id);
      }
      onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Import failed");
      toast.push(err instanceof Error ? err.message : "Import failed", "error");
    }
  }

  async function deleteGame(gameId: string) {
    try {
      await api.delete(`/games/${gameId}`);
      onChanged();
      toast.push("Game deleted", "success");
    } catch (caught) {
      const msg = caught instanceof Error ? caught.message : "Could not delete game";
      onError(msg);
      toast.push(msg, "error");
    }
  }

  function requestDelete(gameId: string) {
    setDeleteTarget(gameId);
    setConfirmOpen(true);
  }

  function onConfirmDelete() {
    if (!deleteTarget) return setConfirmOpen(false);
    deleteGame(deleteTarget);
    setConfirmOpen(false);
    setDeleteTarget(null);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Gamepad2 className="h-5 w-5 text-primary" />
          Games
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2">
          <div className="flex gap-2">
            <Input
              placeholder="Search Steam"
              value={steamQuery}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSteamQuery(e.target.value)}
            />
            <Button onClick={() => void searchSteam()}>Search</Button>
          </div>
          {steamResults.length > 0 ? (
            <div className="space-y-2">
              {steamResults.map((r) => (
                <div key={r.id} className="flex items-center justify-between rounded-md border p-2">
                  <div className="flex items-center gap-2">
                    {r.thumb ? <img src={r.thumb} className="h-8 w-8" alt="" /> : null}
                    <div>{r.name}</div>
                  </div>
                  <Button onClick={() => void importSteam(r.id)}>Import</Button>
                </div>
              ))}
            </div>
          ) : null}
        </div>
        <form className="grid gap-2" onSubmit={createGame}>
          <Input name="title" placeholder="Game title" required />
          <Textarea name="description" placeholder="Co-op loop, pacing, tone" required />
          <div className="grid grid-cols-2 gap-2">
            <Input name="genres" placeholder="genres" />
            <Input name="tags" placeholder="tags" />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <Input name="external_id" placeholder="external id" />
            <Input name="players_min" type="number" min={1} defaultValue={2} />
            <Input name="players_max" type="number" min={1} defaultValue={4} />
          </div>
          <Button>
            <Plus className="h-4 w-4" />
            Add game
          </Button>
        </form>
        <div className="max-h-80 space-y-2 overflow-auto pr-1">
          {filteredGames.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 px-4 text-center rounded-lg border border-dashed bg-muted/40">
              <p className="text-sm font-medium text-muted-foreground">
                Group library is empty
              </p>
              <p className="text-xs text-muted-foreground mt-1 max-w-[240px]">
                Use the search above to find and import/select games from Steam, or add custom games using the form below to write reviews.
              </p>
            </div>
          ) : (
            filteredGames.map((game) => (
              <div
                className={`w-full rounded-md border bg-background p-3 text-left transition-colors hover:bg-muted cursor-pointer ${
                  selectedGameId === game.id ? "border-primary" : ""
                }`}
                key={game.id}
                role="button"
                tabIndex={0}
                onClick={() => onSelectGame(game.id)}
                onKeyDown={(e: any) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectGame(game.id);
                  }
                }}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium">{game.title}</span>
                  <div className="flex items-center gap-2">
                    <Badge>{game.players_min}-{game.players_max}p</Badge>
                    <Button className="h-7 w-7 p-0" onClick={(e: any) => { e.stopPropagation(); requestDelete(game.id); }}>
                      ×
                    </Button>
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {[...game.genres, ...game.tags].slice(0, 4).map((item, i) => (
                    <Badge key={`${item}-${i}`}>{item}</Badge>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
      <ConfirmDialog
        open={confirmOpen}
        title="Delete game"
        description="This will remove the game and any associated reviews. This action cannot be undone."
        onCancel={() => setConfirmOpen(false)}
        onConfirm={onConfirmDelete}
      />
    </Card>
  );
}

