import {
  applyTheme,
  getStoredTheme,
  storeTheme,
  type Theme,
} from "@/lib/theme";
import { ThemeContext } from "@/providers/ThemeContext";
import { useState } from "react";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>(getStoredTheme);

  return (
    <ThemeContext.Provider
      value={{
        theme,
        setTheme: (newTheme: Theme) => {
          applyTheme(newTheme);
          storeTheme(newTheme);
          setTheme(newTheme);
        },
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}
