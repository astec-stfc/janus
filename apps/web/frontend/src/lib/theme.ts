export type Theme = "dark" | "light";

const DEFAULT_THEME: Theme = "light";
const THEME_STORAGE_KEY = "vite-ui-theme";

export const getStoredTheme = (): Theme => {
  const storedTheme = localStorage.getItem(THEME_STORAGE_KEY);
  return storedTheme === "dark" || storedTheme === "light"
    ? storedTheme
    : DEFAULT_THEME;
};

export const applyTheme = (theme: Theme) => {
  const root = window.document.documentElement;
  root.classList.remove("light", "dark");
  root.classList.add(theme);
};

export const storeTheme = (theme: Theme) => {
  localStorage.setItem(THEME_STORAGE_KEY, theme);
};

export const initialiseTheme = () => {
  applyTheme(getStoredTheme());
};
