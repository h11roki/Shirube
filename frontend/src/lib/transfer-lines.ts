export type Box = { left: number; top: number; right: number; bottom: number };

export type Point = { x: number; y: number };

export type Layout = {
  gaps: { row: number; column: number };
  gutter: number;
  sameGrid: boolean;
};

export type Side = "above" | "below";

const ALIGNED = 2;

const middle = (low: number, high: number) => (low + high) / 2;

const point = (x: number, y: number): Point => ({ x, y });

export function transferRoute(from: Box, to: Box, layout: Layout): Point[] {
  const { gaps, gutter, sameGrid } = layout;
  const fromX = middle(from.left, from.right);
  const toX = middle(to.left, to.right);
  if (sameGrid && Math.abs(from.left - to.left) < ALIGNED) {
    const side = from.left - gaps.column / 2;
    const fromY = middle(from.top, from.bottom);
    const toY = middle(to.top, to.bottom);
    return [
      point(from.left, fromY),
      point(side, fromY),
      point(side, toY),
      point(to.left, toY),
    ];
  }
  const below = to.top >= from.bottom;
  const above = to.bottom <= from.top;
  if (!below && !above) {
    const under = Math.max(from.bottom, to.bottom) + gaps.row / 2;
    return [
      point(fromX, from.bottom),
      point(fromX, under),
      point(toX, under),
      point(toX, to.bottom),
    ];
  }
  const leave = below ? from.bottom : from.top;
  const enter = below ? to.top : to.bottom;
  const step = ((below ? 1 : -1) * gaps.row) / 2;
  const leaving = leave + step;
  const entering = enter - step;
  if (Math.abs(leaving - entering) < ALIGNED) {
    return [
      point(fromX, leave),
      point(fromX, leaving),
      point(toX, leaving),
      point(toX, enter),
    ];
  }
  return [
    point(fromX, leave),
    point(fromX, leaving),
    point(gutter, leaving),
    point(gutter, entering),
    point(toX, entering),
    point(toX, enter),
  ];
}

export function offscreenSide(
  rect: { top: number; bottom: number },
  coveredTo: number,
  height: number,
): Side | null {
  if (rect.bottom < coveredTo) {
    return "above";
  }
  return rect.top > height ? "below" : null;
}

const tidy = (value: number) => Math.round(value * 10) / 10;

const distance = (from: Point, to: Point) =>
  Math.hypot(to.x - from.x, to.y - from.y);

function toward(from: Point, to: Point, length: number): Point {
  const whole = distance(from, to);
  return {
    x: tidy(from.x + ((to.x - from.x) * length) / whole),
    y: tidy(from.y + ((to.y - from.y) * length) / whole),
  };
}

export function roundedPath(points: Point[], radius: number): string {
  const steps = [`M ${tidy(points[0].x)} ${tidy(points[0].y)}`];
  for (let index = 1; index < points.length - 1; index += 1) {
    const [before, corner, after] = points.slice(index - 1, index + 2);
    const round = Math.min(
      radius,
      distance(before, corner) / 2,
      distance(corner, after) / 2,
    );
    if (round === 0) {
      steps.push(`L ${tidy(corner.x)} ${tidy(corner.y)}`);
      continue;
    }
    const enter = toward(corner, before, round);
    const leave = toward(corner, after, round);
    steps.push(
      `L ${enter.x} ${enter.y}`,
      `Q ${tidy(corner.x)} ${tidy(corner.y)} ${leave.x} ${leave.y}`,
    );
  }
  const last = points[points.length - 1];
  steps.push(`L ${tidy(last.x)} ${tidy(last.y)}`);
  return steps.join(" ");
}
