import { useEffect, useState } from "react";

import { messageOf, requestJson } from "@/lib/api/client";

export type ApiAnswer<T> = {
  answer: T | undefined;
  lastAnswer: T | undefined;
  failure: string | undefined;
  reloading: boolean;
  reload: () => void;
};

export function useApiAnswer<T>(path: string, query: string): ApiAnswer<T> {
  const [loaded, setLoaded] = useState<{ query: string; answer: T }>();
  const [failed, setFailed] = useState<{ query: string; message: string }>();
  const [reloads, setReloads] = useState(0);
  const [reloading, setReloading] = useState(false);

  useEffect(() => {
    let active = true;
    requestJson<T>(`${path}?${query}`)
      .then((answer) => {
        if (active) {
          setLoaded({ query, answer });
          setFailed(undefined);
          setReloading(false);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setFailed({ query, message: messageOf(error) });
          setReloading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [path, query, reloads]);

  const failure = failed?.query === query ? failed.message : undefined;
  return {
    answer: !failure && loaded?.query === query ? loaded.answer : undefined,
    lastAnswer: loaded?.answer,
    failure,
    reloading,
    reload: () => {
      setReloading(true);
      setReloads((current) => current + 1);
    },
  };
}
