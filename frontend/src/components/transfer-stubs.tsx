"use client";

import type { ReactNode } from "react";

import { useCourseWords } from "@/components/course-words";
import { Phrases } from "@/components/phrases";
import { useTransferFocus } from "@/components/transfer-focus";
import {
  TRANSFER_LABEL,
  arrivalsLabel,
  backPlace,
  hopPlace,
  stationsAway,
} from "@/lib/labels";
import type { Hop, Transfer } from "@/lib/roadmap";

const PERFORATED = "border-t-2 border-dashed border-line pt-2 text-xs";
const HOP_BUTTON = "grid min-h-6 w-full gap-0.5 text-left text-route";

export function Departure({ transfer }: { transfer: Transfer }) {
  const button = departureId(transfer.from.section);
  return (
    <div className={PERFORATED}>
      <HopLink
        from={transfer.from}
        to={transfer.to}
        button={button}
        title={
          <span className="flex flex-wrap items-center gap-x-1.5">
            <span>{TRANSFER_LABEL}</span>
            <TransferMark mark={transfer.mark} />
            <HopName name={transfer.to.name} />
          </span>
        }
      />
    </div>
  );
}

export function Arrivals({ arrivals }: { arrivals: Transfer[] }) {
  return (
    <div className={`grid gap-1.5 ${PERFORATED}`}>
      <p className="flex items-center gap-1.5 font-bold text-route">
        <TransferMark mark={arrivals[0].mark} />
        {arrivalsLabel(arrivals.length)}
      </p>
      <ul className="grid gap-1.5">
        {arrivals.map((transfer) => (
          <li key={transfer.from.section}>
            <HopLink
              from={transfer.to}
              to={transfer.from}
              button={arrivalId(transfer)}
              title={<HopName name={transfer.from.name} />}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}

export function BackFromTrip({ section }: { section: string }) {
  const focusing = useTransferFocus();
  const trip = focusing?.trip;
  if (!trip || trip.to.section !== section) {
    return null;
  }
  return <BackButton to={trip.from} onClick={focusing.back} />;
}

function BackButton({ to, onClick }: { to: Hop; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex min-h-6 items-center self-start text-left text-xs text-route underline underline-offset-4"
    >
      <span aria-hidden className="mr-1">
        ←
      </span>
      <Phrases parts={[...useCourseWords(to.name), backPlace(to)]} />
    </button>
  );
}

function HopLink({
  from,
  to,
  button,
  title,
}: {
  from: Hop;
  to: Hop;
  button: string;
  title: ReactNode;
}) {
  const focusing = useTransferFocus();
  const content = (
    <>
      <span className="font-bold">{title}</span>
      <span className="text-sub">
        {hopPlace(to)} {stationsAway(from.station, to.station)}
      </span>
    </>
  );
  if (!focusing?.reachable(to)) {
    return <p className="grid gap-0.5 text-route">{content}</p>;
  }
  return (
    <button
      id={button}
      type="button"
      onClick={() => focusing.follow({ from, to, button })}
      className={HOP_BUTTON}
    >
      {content}
    </button>
  );
}

function HopName({ name }: { name: string }) {
  return (
    <span className="underline-offset-4 in-[button]:underline">
      <Phrases parts={useCourseWords(name)} />
    </span>
  );
}

function TransferMark({ mark }: { mark: string }) {
  return (
    <span className="inline-grid min-w-[1.375em] place-items-center bg-route px-1 text-label leading-snug font-bold text-paper">
      {mark}
    </span>
  );
}

function departureId(section: string): string {
  return `transfer-${section}`;
}

function arrivalId(transfer: Transfer): string {
  return `transfer-${transfer.to.section}-${transfer.from.section}`;
}
