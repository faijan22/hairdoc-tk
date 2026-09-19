import { Easing } from "react-native-reanimated";

export const motion = {
  duration: {
    fast: 140,
    normal: 220,
    slow: 420,
  },
  easing: {
    standard: Easing.bezier(0.2, 0, 0, 1),
  },
  spring: {
    damping: 18,
    stiffness: 240,
    mass: 0.8,
  },
} as const;

