"use client";

import { RefreshCw, Shield, SquareChevronRight } from "lucide-react";
import { useCallback, useEffect, useMemo, useState, useRef } from "react";

import { AuthPanel } from "@/features/auth/AuthPanel";
import { GamesPanel } from "@/features/games/GamesPanel";
import { GroupsPanel } from "@/features/groups/GroupsPanel";
import { RecommendationsPanel } from "@/features/recommendations/RecommendationsPanel";
import { ReviewPanel } from "@/features/reviews/ReviewPanel";
import { ApiClient, Dashboard, Game, Group, Recommendation, Review, User } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function DashboardShell() {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [games, setGames] = useState<Game[]>([]);
  const [groupGames, setGroupGames] = useState<Game[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const [selectedGameId, setSelectedGameId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const api = useMemo(() => new ApiClient(accessToken), [accessToken]);
  const selectedGame = games.find((game) => game.id === selectedGameId) ?? null;

  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const prevGroupIdRef = useRef<string | null>(null);

  const loadInitial = useCallback(async () => {
    if (!accessToken) return;
    setError(null);
    try {
      const [dashboard, gameList] = await Promise.all([
        api.request<Dashboard>("/dashboard"),
        api.request<Game[]>("/games")
      ]);
      setGroups(dashboard.groups);
      setGames(gameList);
      
      if (dashboard.groups[0] && !selectedGroupId) {
        setSelectedGroupId(dashboard.groups[0].id);
      }
      if (gameList[0] && !selectedGameId) {
        setSelectedGameId(gameList[0].id);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load dashboard");
    }
  }, [accessToken, api, refreshTrigger]);

  const loadGroupData = useCallback(async () => {
    if (!accessToken || !selectedGroupId) return;
    setError(null);
    try {
      const [groupReviews, groupRecs, groupGamesList] = await Promise.all([
        api.request<Review[]>(`/groups/${selectedGroupId}/reviews`),
        api.request<Recommendation[]>(`/groups/${selectedGroupId}/recommendations`),
        api.request<Game[]>(`/groups/${selectedGroupId}/games`)
      ]);
      setReviews(groupReviews);
      setRecommendations(groupRecs);
      setGroupGames(groupGamesList);
      
      if (selectedGroupId !== prevGroupIdRef.current) {
        prevGroupIdRef.current = selectedGroupId;
        if (groupReviews.length > 0) {
          setSelectedGameId(groupReviews[0].game_id);
        } else if (groupGamesList.length > 0) {
          setSelectedGameId(groupGamesList[0].id);
        } else {
          setSelectedGameId(null);
        }
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load group data");
    }
  }, [accessToken, api, selectedGroupId, refreshTrigger]);

  useEffect(() => {
    const savedToken = window.localStorage.getItem("accessToken");
    const savedUser = window.localStorage.getItem("user");
    if (savedToken && savedUser) {
      setAccessToken(savedToken);
      setUser(JSON.parse(savedUser) as User);
    }
  }, []);

  useEffect(() => {
    void loadInitial();
  }, [loadInitial]);

  useEffect(() => {
    void loadGroupData();
  }, [loadGroupData]);

  const refresh = useCallback(() => {
    setRefreshTrigger((prev) => prev + 1);
  }, []);

  function authenticated(token: string, refreshToken: string, nextUser: User) {
    window.localStorage.setItem("accessToken", token);
    window.localStorage.setItem("refreshToken", refreshToken);
    window.localStorage.setItem("user", JSON.stringify(nextUser));
    setAccessToken(token);
    setUser(nextUser);
  }

  function logout() {
    window.localStorage.clear();
    setAccessToken(null);
    setUser(null);
    setGroups([]);
    setGames([]);
    setReviews([]);
    setRecommendations([]);
    setSelectedGroupId(null);
    setSelectedGameId(null);
  }

  if (!accessToken || !user) {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <AuthPanel onAuthenticated={authenticated} />
      </main>
    );
  }

  return (
    <main className="min-h-screen">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <div>
            <h1 className="text-xl font-semibold">Co-op Game Recs</h1>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <Badge className="border-primary/30 text-primary">
                <Shield className="mr-1 h-3 w-3" />
                {user.username}
              </Badge>
              <span>{user.email}</span>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={refresh} title="Refresh">
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
            <Button variant="ghost" onClick={logout}>
              <SquareChevronRight className="h-4 w-4" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-4 px-4 py-4 lg:grid-cols-[320px_1fr_360px]">
        <div className="space-y-4">
          <GroupsPanel
            api={api}
            groups={groups}
            selectedGroupId={selectedGroupId}
            onSelectGroup={setSelectedGroupId}
            onChanged={refresh}
            onError={setError}
          />
          <ReviewPanel
            api={api}
            selectedGame={selectedGame}
            reviews={reviews}
            onChanged={refresh}
            onError={setError}
            selectedGroupId={selectedGroupId}
          />
        </div>
        <GamesPanel
          api={api}
          games={groupGames}
          selectedGameId={selectedGameId}
          onSelectGame={setSelectedGameId}
          onChanged={refresh}
          onError={setError}
          reviews={reviews}
          selectedGroupId={selectedGroupId}
        />
        <RecommendationsPanel
          api={api}
          selectedGroupId={selectedGroupId}
          recommendations={recommendations}
          onChanged={refresh}
          onError={setError}
        />
      </section>

      {error ? (
        <div className="fixed bottom-4 left-1/2 w-[min(92vw,520px)] -translate-x-1/2 rounded-md border border-destructive/30 bg-card p-3 text-sm text-destructive shadow-lg">
          {error}
        </div>
      ) : null}
    </main>
  );
}

