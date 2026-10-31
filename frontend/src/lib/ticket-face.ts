const FULL_WIDTH_ALPHANUMERIC = /[Ａ-Ｚａ-ｚ０-９]/g;
const FULL_WIDTH_OFFSET = 0xfee0;
const STAMP_TILTS = [-6, -9, -4, -8, -5, -10, -7];

export function halfWidthAlphanumerics(text: string): string {
  return text.replace(FULL_WIDTH_ALPHANUMERIC, (letter) =>
    String.fromCharCode(letter.charCodeAt(0) - FULL_WIDTH_OFFSET),
  );
}

export function stampTilt(name: string): number {
  let hash = 0;
  for (const character of halfWidthAlphanumerics(name)) {
    hash = (hash * 31 + (character.codePointAt(0) ?? 0)) % 2_147_483_647;
  }
  return STAMP_TILTS[hash % STAMP_TILTS.length];
}
