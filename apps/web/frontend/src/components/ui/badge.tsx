import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { connectedVariantClasses } from "@/components/ui/variants";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground",
        secondary: "bg-secondary text-secondary-foreground",
        outline: "text-foreground",
        destructive: "bg-destructive text-white",
        connected: connectedVariantClasses,
        awaiting:
          "border-amber-500/40 bg-amber-500/20 text-amber-700 dark:text-amber-300",
        invalid:
          "border-purple-500/40 bg-purple-500/20 text-purple-700 dark:text-purple-300",
        disconnected:
          "border-destructive/40 bg-destructive/15 text-destructive dark:text-rose-300",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

function Badge({
  className,
  variant,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return (
    <span
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  );
}

export { Badge, badgeVariants };
