import ComponentPropsWithoutRef from "react"

import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: React.ComponentPropsWithoutRef<"span">) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-medium text-muted-foreground",
        className
      )}
      {...props}
    />
  );
}

