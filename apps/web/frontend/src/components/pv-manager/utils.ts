import type { UpdateMessage } from "@/types/pvws";

/**
 * Formats PV data into separate value and label components for display.
 *
 * Handles three scenarios :
 * 1. VEnum: value corresponds to index of label array.
 * 2. Arrays: preview of first 5 elements, no label
 * 3. Scalars: value as string, label from labels array
 */
export function formatPVData(raw: UpdateMessage | null): {
  value: string;
  label: string;
} {
  if (raw?.value == null) {
    return { value: "", label: "" };
  }

  const { value, labels } = raw;

  // Scenario 1 and 3: Numeric values (enum index or scalar)
  if (typeof value === "number") {
    const label = labels?.[value] ?? "";
    return { value: String(value), label };
  }

  // Scenario 2: Arrays
  if (Array.isArray(value)) {
    const preview = value
      .slice(0, 5)
      .map((v) => String(v))
      .join(", ");
    const suffix = value.length > 5 ? ", …" : "";
    return { value: `len=${value.length} [${preview}${suffix}]`, label: "" };
  }

  // String values
  if (typeof value === "string") {
    return { value, label: "" };
  }

  return { value: "", label: "" };
}

export function hasPVValue(raw: UpdateMessage | null): boolean {
  return raw?.value != null;
}
