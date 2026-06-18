"use client";

import { FormEvent } from "react";
import { MessageSquarePlus, Star } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiClient, Game, Review } from "@/lib/api";
import { useState } from "react";
import { ConfirmDialog } from "@/components/ui/confirm";
import { useToast } from "@/components/ui/toast";

type ReviewPanelProps = {
  api: ApiClient;
  selectedGame: Game | null;
  reviews: Review[];
  onChanged: () => void;
  onError: (message: string) => void;
  selectedGroupId: string | null;
};

export function ReviewPanel({ api, selectedGame, reviews, onChanged, onError, selectedGroupId }: ReviewPanelProps) {
  const toast = useToast();
  async function createReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedGame) return;
    const form = new FormData(event.currentTarget);
    try {
      await api.request<Review>("/reviews", {
        method: "POST",
        body: JSON.stringify({
          game_id: selectedGame.id,
          rating: Number(form.get("rating")),
          review_text: String(form.get("review_text")),
          group_id: selectedGroupId || null
        })
      });
  if (event.currentTarget) event.currentTarget.reset();
      onChanged();
    } catch (caught) {
      const msg = caught instanceof Error ? caught.message : "Could not create review";
      onError(msg);
      toast.push(msg, "error");
    }
  }

  async function deleteReview(reviewId: string) {
    try {
      await api.delete(`/reviews/${reviewId}`);
      onChanged();
      toast.push("Review deleted", "success");
    } catch (caught) {
      const msg = caught instanceof Error ? caught.message : "Could not delete review";
      onError(msg);
      toast.push(msg, "error");
    }
  }

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  function requestDelete(reviewId: string) {
    setDeleteTarget(reviewId);
    setConfirmOpen(true);
  }

  function onConfirmDelete() {
    if (!deleteTarget) return setConfirmOpen(false);
    deleteReview(deleteTarget);
    setConfirmOpen(false);
    setDeleteTarget(null);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquarePlus className="h-5 w-5 text-primary" />
          Reviews
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <form className="grid gap-2" onSubmit={createReview}>
          <Input value={selectedGame?.title ?? ""} placeholder="Select game" readOnly />
          <Input name="rating" type="number" min={1} max={10} defaultValue={8} disabled={!selectedGame} />
          <Textarea name="review_text" placeholder="What worked for your group?" disabled={!selectedGame} required />
          <Button disabled={!selectedGame}>
            <Star className="h-4 w-4" />
            Save review
          </Button>
        </form>
        <div className="space-y-2">
          {reviews.map((review) => (
            <div className="rounded-md border bg-background p-3" key={review.id}>
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium">{review.game?.title ?? review.game_id}</span>
                <div className="flex items-center gap-2">
                  <Badge>{review.rating}/10</Badge>
                  <Button className="h-7 w-7 p-0" onClick={() => requestDelete(review.id)}>×</Button>
                </div>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{review.review_text}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                <Badge>{review.sentiment}</Badge>
                {review.liked_features.slice(0, 3).map((feature) => (
                  <Badge key={feature}>{feature}</Badge>
                ))}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
      <ConfirmDialog
        open={confirmOpen}
        title="Delete review"
        description="This will permanently remove your review."
        onCancel={() => setConfirmOpen(false)}
        onConfirm={onConfirmDelete}
      />
    </Card>
  );
}

