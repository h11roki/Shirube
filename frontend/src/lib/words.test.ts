import { afterEach, describe, expect, it, vi } from "vitest";

import { plateParts, splitWords } from "@/lib/words";

type Segment = { segment: string; isWordLike: boolean };

async function wordsWith(segments: Segment[]) {
  vi.stubGlobal("Intl", {
    Segmenter: class {
      segment() {
        return segments;
      }
    },
  });
  vi.resetModules();
  return import("@/lib/words");
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("splitWords", () => {
  it("見本の職業名を、サーバー(Node)の辞書で語に分ける", () => {
    expect(splitWords("データサイエンティスト")).toEqual([
      "データ",
      "サイエンティスト",
    ]);
  });

  it("記号と空白は前後の語につなぎ、その前後に折る所を作らない", async () => {
    const { splitWords: split } = await wordsWith([
      { segment: "半導体", isWordLike: true },
      { segment: "・", isWordLike: false },
      { segment: "LSI", isWordLike: true },
      { segment: " ", isWordLike: false },
      { segment: "設計", isWordLike: true },
      { segment: "エンジニア", isWordLike: true },
    ]);
    expect(split("半導体・LSI 設計エンジニア")).toEqual([
      "半導体・LSI 設計",
      "エンジニア",
    ]);
  });

  it("括弧は語につなぎ、閉じ括弧が行の頭に来る折り方を作らない", async () => {
    const { splitWords: split } = await wordsWith([
      { segment: "エンジニア", isWordLike: true },
      { segment: "（", isWordLike: false },
      { segment: "組込み", isWordLike: true },
      { segment: "）", isWordLike: false },
    ]);
    expect(split("エンジニア（組込み）")).toEqual(["エンジニア（組込み）"]);
  });

  it("1 字の語(者、士など)は前の語につなぐ", async () => {
    const { splitWords: split } = await wordsWith([
      { segment: "電気", isWordLike: true },
      { segment: "主任", isWordLike: true },
      { segment: "技術", isWordLike: true },
      { segment: "者", isWordLike: true },
    ]);
    expect(split("電気主任技術者")).toEqual(["電気", "主任", "技術者"]);
  });

  it("Intl.Segmenter の無いブラウザでは分けない", async () => {
    vi.stubGlobal("Intl", { Segmenter: undefined });
    vi.resetModules();
    const { splitWords: split } = await import("@/lib/words");
    expect(split("データサイエンティスト")).toEqual(["データサイエンティスト"]);
  });
});

describe("plateParts", () => {
  it("最後の 1 字を、行とつなぐために語から外す", () => {
    expect(plateParts("データサイエンティスト")).toEqual({
      words: ["データ", "サイエンティス"],
      tail: "ト",
    });
  });

  it("1 字の名前は、その字だけを行とつなぐ", () => {
    expect(plateParts("医")).toEqual({ words: [""], tail: "医" });
  });
});
