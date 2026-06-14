"use client";

import * as React from "react";
const { createContext, useContext, useState } = React;

type Toast = { id: string; message: string; variant?: "success" | "error" | "info" };

type ToastContextValue = {
  push: (message: string, variant?: Toast["variant"]) => void;
};

const ToastContext = createContext(null as any);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  type ToastItem = { id: string; message: string; variant?: Toast["variant"] };
  const [toasts, setToasts] = useState([] as ToastItem[]);

  function push(message: string, variant: Toast["variant"] = "success") {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
  setToasts((t: any[]) => [...t, { id, message, variant }]);
    setTimeout(() => {
      setToasts((t: any[]) => t.filter((x: any) => x.id !== id));
    }, 4000);
  }

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="fixed right-4 top-4 z-50 flex flex-col gap-2">
        {toasts.map((t: ToastItem) => (
          <div
            key={t.id}
            className={`rounded px-3 py-2 text-sm shadow-md ${
              t.variant === "success"
                ? "bg-green-600 text-white"
                : t.variant === "error"
                ? "bg-red-600 text-white"
                : "bg-blue-600 text-white"
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
