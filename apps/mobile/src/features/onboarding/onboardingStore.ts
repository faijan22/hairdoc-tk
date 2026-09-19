import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";

const storageKey = "hairdoc-onboarding";

type OnboardingState = {
  completed: boolean;
  hasHydrated: boolean;
  complete: () => void;
  replay: () => void;
  setHasHydrated: (value: boolean) => void;
};

export const useOnboardingStore = create<OnboardingState>((set) => ({
  completed: false,
  hasHydrated: false,
  complete: () => {
    set({ completed: true });
    void AsyncStorage.setItem(storageKey, "true");
  },
  replay: () => {
    set({ completed: false });
    void AsyncStorage.setItem(storageKey, "false");
  },
  setHasHydrated: (value) => set({ hasHydrated: value }),
}));

void AsyncStorage.getItem(storageKey)
  .then((value) => useOnboardingStore.setState({ completed: value === "true", hasHydrated: true }))
  .catch(() => useOnboardingStore.setState({ hasHydrated: true }));
