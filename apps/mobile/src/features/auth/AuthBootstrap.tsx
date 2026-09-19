import { useEffect } from "react";

import { useAuthStore } from "./authStore";

export function AuthBootstrap() {
  const bootstrap = useAuthStore((state) => state.bootstrap);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  return null;
}
