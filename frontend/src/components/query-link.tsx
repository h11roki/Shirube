"use client";

import type { ComponentProps, MouseEvent } from "react";

type QueryLinkProps = Omit<
  ComponentProps<"a">,
  "href" | "onClick" | "target"
> & {
  href: string;
  onNavigate?: () => void;
};

function pushQuery(href: string) {
  const target = new URL(href, window.location.href);
  if (
    target.pathname + target.search !==
    window.location.pathname + window.location.search
  ) {
    window.history.pushState(null, "", href);
  }
}

export function replaceQuery(href: string) {
  window.history.replaceState(null, "", href);
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
