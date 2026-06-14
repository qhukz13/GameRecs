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

export class ApiClient {
  constructor(private readonly token: string | null) {}

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Content-Type", "application/json");
    if (this.token) {
      headers.set("Authorization", `Bearer ${this.token}`);
    }
    let response: Response;
    try {
      response = await fetch(`${API_URL}${path}`, {
        ...init,
        headers,
      });
    } catch (err) {
      // network-level error (CORS, connection refused, etc.)
      throw new Error("Network error");
    }

    if (!response.ok) {
      // try to parse error details, fall back to statusText
      const payload = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(typeof payload.detail === "string" ? payload.detail : "Request failed");
    }

    // No Content responses (204) or empty bodies should resolve to undefined
    if (response.status === 204) {
      return undefined as unknown as T;
    }

    // some servers may return empty body with 200; handle that too
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
}

