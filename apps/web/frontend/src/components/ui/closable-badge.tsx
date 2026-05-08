import { XIcon } from "lucide-react";

import { Badge, type badgeVariants } from "@/components/ui/badge";
import type { VariantProps } from "class-variance-authority";

interface ClosableBadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  onClose?: () => void;
}

const ClosableBadge = ({
  children,
  onClose,
  className,
  variant,
  ...props
}: ClosableBadgeProps) => (
  <Badge variant={variant} className={className} {...props}>
    {children}
    <button
      type="button"
      className="focus-visible:border-ring focus-visible:ring-ring/50 -my-px -ms-px -me-1.5 inline-flex size-4 shrink-0 cursor-pointer items-center justify-center rounded-[inherit] p-0 opacity-60 transition-[color,opacity,box-shadow] outline-none hover:opacity-100 focus-visible:ring-[3px]"
      aria-label="Close"
      onClick={onClose}
    >
      <XIcon className="size-3" aria-hidden="true" />
    </button>
  </Badge>
);

export { ClosableBadge };
