"use client";

import { KeyRound, LogIn, UserPlus } from "lucide-react";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiClient, User } from "@/lib/api";

type AuthPanelProps = {
  onAuthenticated: (accessToken: string, refreshToken: string, user: User) => void;
};

type AuthResponse = {
  access_token: string;
  refresh_token: string;
  user: User;
};

export function AuthPanel({ onAuthenticated }: AuthPanelProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsLoading(true);

    const form = new FormData(event.currentTarget);
    const api = new ApiClient(null);
    const body =
      mode === "register"
        ? {
            email: String(form.get("email")),
            username: String(form.get("username")),
            password: String(form.get("password"))
          }
        : {
            email: String(form.get("email")),
            password: String(form.get("password"))
          };

    try {
      const response = await api.request<AuthResponse>(`/auth/${mode}`, {
        method: "POST",
        body: JSON.stringify(body)
      });
      onAuthenticated(response.access_token, response.refresh_token, response.user);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Authentication failed");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <KeyRound className="h-5 w-5 text-primary" />
          Co-op Game Recs
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mb-4 grid grid-cols-2 rounded-md border p-1">
          <Button
            type="button"
            variant={mode === "login" ? "default" : "ghost"}
            onClick={() => setMode("login")}
          >
            <LogIn className="h-4 w-4" />
            Login
          </Button>
          <Button
            type="button"
            variant={mode === "register" ? "default" : "ghost"}
            onClick={() => setMode("register")}
          >
            <UserPlus className="h-4 w-4" />
            Sign up
          </Button>
        </div>
        <form className="space-y-3" onSubmit={submit}>
          <Input name="email" placeholder="email@example.com" type="email" required />
          {mode === "register" ? <Input name="username" placeholder="username" required /> : null}
          <Input name="password" placeholder="password" type="password" minLength={8} required />
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button className="w-full" disabled={isLoading}>
            {isLoading ? "Working..." : mode === "login" ? "Login" : "Create account"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

