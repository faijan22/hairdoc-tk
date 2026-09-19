import { PropsWithChildren, createContext, useContext, useMemo } from "react";

import { AppTheme, createTheme } from "./tokens";

const ThemeContext = createContext<AppTheme | null>(null);

export function ThemeProvider({ children }: PropsWithChildren) {
  const theme = useMemo(() => createTheme("light"), []);

  return (
    <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): AppTheme {
  const theme = useContext(ThemeContext);
  if (!theme) {
    throw new Error("useTheme must be used inside ThemeProvider.");
  }
  return theme;
}
