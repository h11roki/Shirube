const STAMP_TILTS = [-6, -9, -4, -8, -5, -10, -7];

export function stampTilt(name: string): number {
  let hash = 0;
  for (const character of name) {
    hash = (hash * 31 + (character.codePointAt(0) ?? 0)) % 2_147_483_647;
  }
  return STAMP_TILTS[hash % STAMP_TILTS.length];
}
