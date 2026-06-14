export type User = {
  id: string;
  email: string;
  username: string;
  created_at: string;
};

export type Group = {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
};

export type Game = {
  id: string;
  external_id: string | null;
  title: string;
  description: string;
  genres: string[];
  tags: string[];
  players_min: number;
  players_max: number;
  release_date: string | null;
  created_at: string;
};

export type Review = {
  id: string;
  user_id: string;
  game_id: string;
  rating: number;
  review_text: string;
  liked_features: string[];
  disliked_features: string[];
  sentiment: string;
  created_at: string;
  game?: Game;
};

export type Recommendation = {
  id: string;
  group_id: string;
  game_id: string;
  score: number;
  explanation: string;
  created_at: string;
  game: Game;
};

export type Dashboard = {
  groups: Group[];
  recent_reviews: Review[];
  recommendations: Recommendation[];
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function getStoredRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("refreshToken");
}

async function tryRefreshToken(): Promise<string | null> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return null;
  try {
    const resp = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!resp.ok) return null;
    const data = await resp.json() as { access_token: string };
    if (data.access_token) {
      window.localStorage.setItem("accessToken", data.access_token);
      return data.access_token;
    }
    return null;
  } catch {
    return null;
  }
}

export class ApiClient {
  constructor(private token: string | null) {
    // try to recover token from localStorage if not provided
    if (!this.token && typeof window !== "undefined") {
      this.token = window.localStorage.getItem("accessToken");
    }
  }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const execute = async (token: string | null): Promise<Response> => {
      const headers = new Headers(init.headers);
      headers.set("Content-Type", "application/json");
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
      return fetch(`${API_URL}${path}`, { ...init, headers });
    };

    let response: Response;
    try {
      response = await execute(this.token);
    } catch (err) {
      throw new Error("Network error");
    }

    // If 401, try to refresh the token and retry once
    if (response.status === 401) {
      const newToken = await tryRefreshToken();
      if (newToken) {
        this.token = newToken;
        try {
          response = await execute(this.token);
        } catch (err) {
          throw new Error("Network error");
        }
      } else {
        // Refresh failed; clear auth state
        if (typeof window !== "undefined") {
          window.localStorage.removeItem("accessToken");
          window.localStorage.removeItem("refreshToken");
          window.localStorage.removeItem("user");
        }
        const payload = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(typeof payload.detail === "string" ? payload.detail : "Session expired");
      }
    }

    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(typeof payload.detail === "string" ? payload.detail : "Request failed");
    }

    // No Content responses (204) or empty bodies should resolve to undefined
    if (response.status === 204) {
      return undefined as unknown as T;
    }

    const text = await response.text();
    if (!text) return undefined as unknown as T;

    try {
      return JSON.parse(text) as T;
    } catch (err) {
      throw new Error("Invalid JSON response");
    }
  }

  async delete(path: string): Promise<void> {
    await this.request<void>(path, { method: "DELETE" });
  }

  getToken(): string | null {
    return this.token;
  }
}

