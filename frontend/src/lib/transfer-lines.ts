export type Box = { left: number; top: number; right: number; bottom: number };

export type Point = { x: number; y: number };

const HALF_GAP = 6;
const ALIGNED = 2;

const middle = (low: number, high: number) => (low + high) / 2;

export function transferRoute(from: Box, to: Box): Point[] {
  const fromY = middle(from.top, from.bottom);
  const toY = middle(to.top, to.bottom);
  const fromX = middle(from.left, from.right);
  if (Math.abs(from.left - to.left) < ALIGNED) {
    const gutter = from.left - HALF_GAP;
    return [
      { x: from.left, y: fromY },
      { x: gutter, y: fromY },
      { x: gutter, y: toY },
      { x: to.left, y: toY },
    ];
  }
  const below = to.top >= from.bottom;
  const above = to.bottom <= from.top;
  if (!below && !above) {
    const under = Math.max(from.bottom, to.bottom) + HALF_GAP;
    const toX = middle(to.left, to.right);
    return [
      { x: fromX, y: from.bottom },
      { x: fromX, y: under },
      { x: toX, y: under },
      { x: toX, y: to.bottom },
    ];
  }
  const edge = below ? from.bottom : from.top;
  const lane = below ? edge + HALF_GAP : edge - HALF_GAP;
  const gutter = to.left - HALF_GAP;
  return [
    { x: fromX, y: edge },
    { x: fromX, y: lane },
    { x: gutter, y: lane },
    { x: gutter, y: toY },
    { x: to.left, y: toY },
  ];
}

const tidy = (value: number) => Math.round(value * 10) / 10;

function toward(from: Point, to: Point, distance: number): Point {
  const length = Math.hypot(to.x - from.x, to.y - from.y);
  return {
    x: tidy(from.x + ((to.x - from.x) * distance) / length),
    y: tidy(from.y + ((to.y - from.y) * distance) / length),
  };
}

export function roundedPath(points: Point[], radius: number): string {
  const steps = [`M ${tidy(points[0].x)} ${tidy(points[0].y)}`];
  for (let index = 1; index < points.length - 1; index += 1) {
    const [before, corner, after] = points.slice(index - 1, index + 2);
    const round = Math.min(
      radius,
      Math.hypot(corner.x - before.x, corner.y - before.y) / 2,
      Math.hypot(after.x - corner.x, after.y - corner.y) / 2,
    );
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
