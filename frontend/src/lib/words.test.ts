import { afterEach, describe, expect, it, vi } from "vitest";

import { splitWords } from "@/lib/words";

describe("splitWords", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("カタカナの続く職業名を語に分ける", () => {
    expect(splitWords("データサイエンティスト")).toEqual([
      "データ",
      "サイエンティスト",
    ]);
    expect(splitWords("組込みソフトウェアエンジニア")).toEqual([
      "組込み",
      "ソフトウェア",
      "エンジニア",
    ]);
  });

  it("空白や記号も残し、つなぐと元の名前に戻る", () => {
    const name = "半導体・LSI 設計エンジニア";
    expect(splitWords(name)).toEqual([
      "半導体",
      "・",
      "LSI",
      " ",
      "設計",
      "エンジニア",
    ]);
    expect(splitWords(name).join("")).toBe(name);
  });

  it("Intl.Segmenter の無いブラウザでは分けない", () => {
    vi.stubGlobal("Intl", { Segmenter: undefined });
    expect(splitWords("データサイエンティスト")).toEqual([
      "データサイエンティスト",
    ]);
  });
});
