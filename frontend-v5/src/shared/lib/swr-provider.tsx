"use client";

import { SWRConfig } from "swr";

export function SWRProvider({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig
      value={{
        revalidateOnFocus: false,
        revalidateOnReconnect: true,
        dedupingInterval: 8000,
        errorRetryCount: 2,
        focusThrottleInterval: 60_000,
      }}
    >
      {children}
    </SWRConfig>
  );
}
