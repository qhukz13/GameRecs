"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

type ConfirmDialogProps = {
  title?: string;
  description?: string;
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export function ConfirmDialog({ title = "Confirm", description, open, onCancel, onConfirm }: ConfirmDialogProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded bg-white p-6 shadow-lg">
        <h3 className="text-lg font-medium">{title}</h3>
        {description && <p className="mt-2 text-sm text-muted-foreground">{description}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={onConfirm}>Confirm</Button>
        </div>
      </div>
    </div>
  );
}
