"use client";

import type { ComponentProps, MouseEvent } from "react";

type QueryLinkProps = Omit<ComponentProps<"a">, "href" | "onClick"> & {
  href: string;
  onNavigate?: () => void;
};

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
    window.history.pushState(null, "", href);
    onNavigate?.();
  }

  return <a href={href} onClick={navigate} {...rest} />;
}
