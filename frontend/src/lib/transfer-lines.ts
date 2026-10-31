export type Box = { left: number; top: number; right: number; bottom: number };

export type Point = { x: number; y: number };

export type Gaps = { row: number; column: number };

const ALIGNED = 2;

const middle = (low: number, high: number) => (low + high) / 2;

export function transferRoute(from: Box, to: Box, gaps: Gaps): Point[] {
  const fromY = middle(from.top, from.bottom);
  const toY = middle(to.top, to.bottom);
  const fromX = middle(from.left, from.right);
  if (Math.abs(from.left - to.left) < ALIGNED) {
    const gutter = from.left - gaps.column / 2;
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
    const under = Math.max(from.bottom, to.bottom) + gaps.row / 2;
    const toX = middle(to.left, to.right);
    return [
      { x: fromX, y: from.bottom },
      { x: fromX, y: under },
      { x: toX, y: under },
      { x: toX, y: to.bottom },
    ];
  }
  const edge = below ? from.bottom : from.top;
  const lane = below ? edge + gaps.row / 2 : edge - gaps.row / 2;
  const gutter = to.left - gaps.column / 2;
  return [
    { x: fromX, y: edge },
    { x: fromX, y: lane },
    { x: gutter, y: lane },
    { x: gutter, y: toY },
    { x: to.left, y: toY },
  ];
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
