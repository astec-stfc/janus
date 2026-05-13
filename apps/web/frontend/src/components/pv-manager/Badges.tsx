import { Badge } from "@/components/ui/badge";

import type { PVMode, PVStatus } from "@/types";

export function StatusBadge({ status }: { status: PVStatus }) {
  return <Badge variant={status}>{status}</Badge>;
}

export function ModeBadge({ mode }: { mode: PVMode }) {
  return <Badge variant="outline">{mode}</Badge>;
}
