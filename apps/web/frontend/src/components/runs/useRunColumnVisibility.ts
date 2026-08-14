import { useState } from "react";

import { getDefaultFields, type RunColumnField } from "./runColumns";

export function useRunColumnVisibility() {
  const [visibleFields, setVisibleFields] =
    useState<ReadonlySet<RunColumnField>>(getDefaultFields);

  const setColumnsVisible = (
    fields: readonly RunColumnField[],
    visible: boolean,
  ): void => {
    setVisibleFields((currentFields) => {
      const nextFields = new Set(currentFields);

      if (visible) {
        for (const field of fields) {
          nextFields.add(field);
        }
      } else {
        for (const field of fields) {
          nextFields.delete(field);
        }
      }

      return nextFields;
    });
  };

  return { visibleFields, setColumnsVisible };
}
