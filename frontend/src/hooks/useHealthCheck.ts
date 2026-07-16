import { useCallback, useEffect, useState } from "react";

import { getHealth, getReadiness, type HealthResponse } from "../api/client";

type HealthState = {
  health: HealthResponse | null;
  readiness: HealthResponse | null;
  loading: boolean;
  error: string | null;
};

const initialState: HealthState = {
  health: null,
  readiness: null,
  loading: true,
  error: null
};

export function useHealthCheck() {
  const [state, setState] = useState<HealthState>(initialState);

  const refresh = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: null }));

    try {
      const [health, readiness] = await Promise.all([getHealth(), getReadiness()]);
      setState({ health, readiness, loading: false, error: null });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to reach the backend";
      setState({ health: null, readiness: null, loading: false, error: message });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { ...state, refresh };
}
