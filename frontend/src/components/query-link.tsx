"use client";

import type { ComponentProps, MouseEvent } from "react";

type QueryLinkProps = Omit<
  ComponentProps<"a">,
  "href" | "onClick" | "target"
> & {
  href: string;
  onNavigate?: () => void;
};

export function pushQuery(href: string): boolean {
  const target = new URL(href, window.location.href);
  const changed =
    target.pathname + target.search !==
    window.location.pathname + window.location.search;
  if (changed) {
    window.history.pushState(null, "", href);
  }
  return changed;
}

export function QueryLink({ href, onNavigate, ...rest }: QueryLinkProps) {
  function navigate(event: MouseEvent<HTMLAnchorElement>) {
    if (
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return;
    }
    event.preventDefault();
    pushQuery(href);
    onNavigate?.();
  }

  return <a href={href} onClick={navigate} {...rest} />;
}
