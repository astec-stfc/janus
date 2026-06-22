import type { Theme } from "@/lib/theme";
import { createContext } from "react";

type ThemeContextState = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
};

export const ThemeContext = createContext<ThemeContextState | undefined>(
  undefined,
);
