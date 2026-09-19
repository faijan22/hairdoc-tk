import { ColorSchemeName, Platform, TextStyle, ViewStyle } from "react-native";

const palette = {
  ink: "#111713",
  forest: "#184C39",
  ivory: "#FFFFFF",
  night: "#111713",
  nightRaised: "#19221C",
  nightBorder: "#344139",
  mist: "#F3F5F2",
  danger: "#A7353D",
} as const;

const lightColors = {
  background: palette.mist,
  surface: palette.ivory,
  surfaceMuted: "#E8EEEA",
  text: palette.ink,
  textMuted: "#667069",
  primary: palette.forest,
  primaryMuted: "#DCE9E1",
  onPrimary: palette.ivory,
  accent: "#527663",
  accentMuted: "#E5EDE7",
  border: "#E1E6E2",
  success: "#2F765B",
  danger: palette.danger,
  decorative: "#C4D7C9",
} as const;

const darkColors = {
  background: palette.night,
  surface: palette.nightRaised,
  surfaceMuted: "#232E27",
  text: palette.mist,
  textMuted: "#B7C2BA",
  primary: "#A9C7B3",
  primaryMuted: "#24382C",
  onPrimary: "#102117",
  accent: "#A9C7B3",
  accentMuted: "#24382C",
  border: palette.nightBorder,
  success: "#86C9A4",
  danger: "#EB8B8D",
  decorative: "#3E5546",
} as const;

export const spacing = {
  none: 0,
  xxs: 4,
  xs: 8,
  sm: 12,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
  hero: 64,
} as const;

export const radius = {
  sm: 12,
  md: 18,
  lg: 26,
  pill: 999,
} as const;

const webDisplayFont =
  Platform.OS === "web"
    ? '\"SF Pro Display\", -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif'
    : undefined;
const webTextFont =
  Platform.OS === "web"
    ? '\"SF Pro Text\", -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif'
    : undefined;

export const typography = {
  display: {
    fontSize: 38,
    lineHeight: 43,
    fontWeight: "700",
    letterSpacing: -1.1,
    fontFamily: webDisplayFont,
  },
  title: {
    fontSize: 27,
    lineHeight: 34,
    fontWeight: "700",
    letterSpacing: -0.6,
    fontFamily: webDisplayFont,
  },
  heading: {
    fontSize: 21,
    lineHeight: 27,
    fontWeight: "700",
    fontFamily: webDisplayFont,
  },
  body: {
    fontSize: 16,
    lineHeight: 24,
    fontWeight: "400",
    fontFamily: webTextFont,
  },
  bodyStrong: {
    fontSize: 16,
    lineHeight: 24,
    fontWeight: "600",
    fontFamily: webTextFont,
  },
  caption: {
    fontSize: 14,
    lineHeight: 20,
    fontWeight: "500",
    fontFamily: webTextFont,
  },
  overline: {
    fontSize: 13,
    lineHeight: 18,
    fontWeight: "600",
    letterSpacing: 0.2,
    fontFamily: webTextFont,
  },
} as const satisfies Record<string, TextStyle>;

export const elevation = {
  card: {
    shadowColor: "#102117",
    shadowOpacity: 0.045,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 6 },
    elevation: 2,
  },
} as const satisfies Record<string, ViewStyle>;

export const iconSize = { sm: 16, md: 22, lg: 30 } as const;
export const layout = { contentMaxWidth: 720, compactBreakpoint: 480 } as const;

export type AppColors = typeof lightColors;
export type AppTheme = {
  colorScheme: "light" | "dark";
  colors: AppColors;
  spacing: typeof spacing;
  radius: typeof radius;
  typography: typeof typography;
  elevation: typeof elevation;
  iconSize: typeof iconSize;
  layout: typeof layout;
};

export function createTheme(colorScheme: ColorSchemeName): AppTheme {
  const resolvedScheme = colorScheme === "dark" ? "dark" : "light";
  return {
    colorScheme: resolvedScheme,
    colors: (resolvedScheme === "dark" ? darkColors : lightColors) as AppColors,
    spacing,
    radius,
    typography,
    elevation,
    iconSize,
    layout,
  };
}
