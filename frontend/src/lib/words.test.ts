import { afterEach, describe, expect, it, vi } from "vitest";

type Segment = { segment: string; isWordLike: boolean };

const RealSegmenter = Intl.Segmenter;

async function wordsWith(segments: Segment[]) {
  vi.stubGlobal("Intl", {
    Segmenter: class {
      readonly locale: string;
      readonly options: Intl.SegmenterOptions;

      constructor(locale: string, options: Intl.SegmenterOptions) {
        this.locale = locale;
        this.options = options;
      }

      segment(text: string) {
        return this.options.granularity === "word"
          ? segments
          : new RealSegmenter(this.locale, this.options).segment(text);
      }
    },
  });
  vi.resetModules();
  return import("@/lib/words");
}

function word(segment: string): Segment {
  return { segment, isWordLike: true };
}

function mark(segment: string): Segment {
  return { segment, isWordLike: false };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("splitWords", () => {
  it("語のあいだで分ける", async () => {
    const { splitWords } = await wordsWith([
      word("データ"),
      word("サイエンティスト"),
    ]);
    expect(splitWords("データサイエンティスト")).toEqual([
      "データ",
      "サイエンティスト",
    ]);
  });

  it("記号と空白は前後の語につなぎ、その前後に折る所を作らない", async () => {
    const { splitWords } = await wordsWith([
      word("半導体"),
      mark("・"),
      word("LSI"),
      mark(" "),
      word("設計"),
      word("エンジニア"),
    ]);
    expect(splitWords("半導体・LSI 設計エンジニア")).toEqual([
      "半導体・LSI 設計",
      "エンジニア",
    ]);
  });

  it("括弧は語につなぎ、閉じ括弧が行の頭に来る折り方を作らない", async () => {
    const { splitWords } = await wordsWith([
      word("エンジニア"),
      mark("（"),
      word("組込み"),
      mark("）"),
    ]);
    expect(splitWords("エンジニア（組込み）")).toEqual([
      "エンジニア（組込み）",
    ]);
  });

  it("1 字の語(者、士など)は、異体字セレクタが付いていても前の語につなぐ", async () => {
    const { splitWords } = await wordsWith([
      word("電気"),
      word("主任"),
      word("技術"),
      word("者︀"),
    ]);
    expect(splitWords("電気主任技術者︀")).toEqual(["電気", "主任", "技術者︀"]);
  });

  it("Intl.Segmenter の無いブラウザでは分けない", async () => {
    vi.stubGlobal("Intl", { Segmenter: undefined });
    vi.resetModules();
    const { splitWords } = await import("@/lib/words");
    expect(splitWords("データサイエンティスト")).toEqual([
      "データサイエンティスト",
    ]);
  });
});

describe("plateParts", () => {
  it("最後の 1 字を、行とつなぐために語から外す", async () => {
    const { plateParts } = await wordsWith([
      word("データ"),
      word("サイエンティスト"),
    ]);
    expect(plateParts("データサイエンティスト")).toEqual({
      words: ["データ", "サイエンティス"],
      tail: "ト",
    });
  });

  it("最後の 1 字は、見た目の 1 字(絵文字の組や濁点の付いた字)ごと外す", async () => {
    const { plateParts } = await wordsWith([word("エンジニア"), mark("👩‍💻")]);
    expect(plateParts("エンジニア👩‍💻")).toEqual({
      words: ["エンジニア"],
      tail: "👩‍💻",
    });
  });

  it("1 字の名前は、その字だけを行とつなぐ", async () => {
    const { plateParts } = await wordsWith([word("医")]);
    expect(plateParts("医")).toEqual({ words: [""], tail: "医" });
  });

  it("Intl.Segmenter の無いブラウザでも、最後の 1 字を外す", async () => {
    vi.stubGlobal("Intl", { Segmenter: undefined });
    vi.resetModules();
    const { plateParts } = await import("@/lib/words");
    expect(plateParts("データサイエンティスト")).toEqual({
      words: ["データサイエンティス"],
      tail: "ト",
    });
  });
});
