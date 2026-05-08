import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TableCell } from "@/components/ui/table";
import { usePVWS } from "@/hooks/usePVWS";
import { usePVWSGet } from "@/hooks/usePVWSGet";
import { Trash2 } from "lucide-react";
import { useState, type ReactNode } from "react";

import type { PVEntry } from "@/types";
import { usePVStatus } from "../../hooks/usePVStatus";
import { ModeBadge, StatusBadge } from "./Badges";
import { formatPVData } from "./utils";

function RemoveButton({ onClick }: { onClick: () => void }) {
  return (
    <Button
      type="button"
      size="icon-sm"
      variant="ghost"
      onClick={onClick}
      aria-label="Remove"
    >
      <Trash2 className="size-4" aria-hidden="true" />
    </Button>
  );
}

function GetButton({
  onClick,
  disabled,
}: {
  onClick: () => void;
  disabled: boolean;
}) {
  return (
    <Button
      type="button"
      size="sm"
      variant="outline"
      onClick={onClick}
      disabled={disabled}
    >
      GET
    </Button>
  );
}

function PutButton({
  onSubmit,
  input,
  onInputChange,
  disabled,
  canPut,
}: {
  onSubmit: (e: React.FormEvent) => void;
  input: string;
  onInputChange: (value: string) => void;
  disabled: boolean;
  canPut: boolean;
}) {
  return (
    <form className="flex items-center gap-2" onSubmit={onSubmit}>
      <Button
        type="submit"
        size="sm"
        variant="outline"
        disabled={disabled || !canPut}
      >
        PUT
      </Button>
      <Input
        type="number"
        step="any"
        inputMode="decimal"
        value={input}
        onChange={(event) => onInputChange(event.target.value)}
        placeholder="Value"
        className="w-40"
      />
    </form>
  );
}

function PVRowLayout({
  status,
  pvName,
  mode,
  value,
  label,
  actions,
  remove,
}: {
  status: ReactNode;
  pvName: string;
  mode: ReactNode;
  value: string;
  label: string;
  actions: ReactNode;
  remove: ReactNode;
}) {
  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(pvName);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <>
      <TableCell className="w-[140px] whitespace-nowrap">{status}</TableCell>
      <TableCell
        className="whitespace-normal break-words font-mono cursor-pointer"
        onClick={copyToClipboard}
      >
        {pvName}
      </TableCell>
      <TableCell className="w-[120px] whitespace-nowrap">{mode}</TableCell>
      <TableCell className="w-[140px] whitespace-nowrap font-mono tabular-nums">
        {value}
      </TableCell>
      <TableCell className="w-[160px] whitespace-nowrap">{label}</TableCell>
      <TableCell className="w-[200px]">{actions}</TableCell>
      <TableCell className="w-[72px] text-center">{remove}</TableCell>
    </>
  );
}

function PVGetRowCells({
  entry,
  onRemove,
}: {
  entry: PVEntry;
  onRemove: (id: number) => void;
}) {
  const { connected, raw, get, error, requested } = usePVWSGet(entry.pvName);
  const { value, label } = formatPVData(raw);
  const status = usePVStatus({
    connected,
    error,
    raw,
    active: requested,
  });

  return (
    <PVRowLayout
      status={<StatusBadge status={status} />}
      pvName={entry.pvName}
      mode={<ModeBadge mode={entry.mode} />}
      value={value}
      label={label}
      actions={<GetButton onClick={get} disabled={!connected} />}
      remove={<RemoveButton onClick={() => onRemove(entry.id)} />}
    />
  );
}

function PVMonitorRowCells({
  entry,
  onRemove,
}: {
  entry: PVEntry;
  onRemove: (id: number) => void;
}) {
  const { connected, raw, error } = usePVWS(entry.pvName);
  const { value, label } = formatPVData(raw);
  const status = usePVStatus({
    connected,
    error,
    raw,
    active: true,
  });

  return (
    <PVRowLayout
      status={<StatusBadge status={status} />}
      pvName={entry.pvName}
      mode={<ModeBadge mode={entry.mode} />}
      value={value}
      label={label}
      actions={null}
      remove={<RemoveButton onClick={() => onRemove(entry.id)} />}
    />
  );
}

function PVPutRowCells({
  entry,
  onRemove,
}: {
  entry: PVEntry;
  onRemove: (id: number) => void;
}) {
  const { connected, raw, put, error } = usePVWS(entry.pvName);
  const [input, setInput] = useState("");
  const { value, label } = formatPVData(raw);
  const status = usePVStatus({
    connected,
    error,
    raw,
    active: true,
  });

  const canPut = input.trim() !== "" && Number.isFinite(Number(input));

  const onPut = () => {
    if (!canPut) return;
    put(Number(input));
  };

  return (
    <PVRowLayout
      status={<StatusBadge status={status} />}
      pvName={entry.pvName}
      mode={<ModeBadge mode={entry.mode} />}
      value={value}
      label={label}
      actions={
        <PutButton
          onSubmit={(e) => {
            e.preventDefault();
            onPut();
          }}
          input={input}
          onInputChange={setInput}
          disabled={!connected}
          canPut={canPut}
        />
      }
      remove={<RemoveButton onClick={() => onRemove(entry.id)} />}
    />
  );
}

export function PVRowCells({
  entry,
  onRemove,
}: {
  entry: PVEntry;
  onRemove: (id: number) => void;
}): React.JSX.Element | null {
  switch (entry.mode) {
    case "GET":
      return <PVGetRowCells entry={entry} onRemove={onRemove} />;
    case "MONITOR":
      return <PVMonitorRowCells entry={entry} onRemove={onRemove} />;
    case "PUT":
      return <PVPutRowCells entry={entry} onRemove={onRemove} />;
    default:
      return null;
  }
}
