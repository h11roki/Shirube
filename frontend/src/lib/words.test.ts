import { afterEach, describe, expect, it, vi } from "vitest";

type Segment = { segment: string; isWordLike: boolean };

const RealSegmenter = Intl.Segmenter;

async function wordsModuleWith(segments: Segment[]) {
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

function joined(segments: Segment[]): string {
  return segments.map(({ segment }) => segment).join("");
}

async function platePartsWith(segments: Segment[]) {
  const { plateParts } = await wordsModuleWith(segments);
  return plateParts(joined(segments));
}

async function wordsOfWith(segments: Segment[]) {
  const { wordsOf } = await wordsModuleWith(segments);
  return wordsOf(joined(segments));
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

describe("plateParts", () => {
  it("語のあいだで分け、最後の 1 字を行とつなぐために外す", async () => {
    expect(
      await platePartsWith([word("データ"), word("サイエンティスト")]),
    ).toEqual({ words: ["データ", "サイエンティス"], tail: "ト" });
  });

  it("記号と空白の前では折らず、あとでは次の語の前で折る", async () => {
    expect(
      await platePartsWith([
        word("半導体"),
        mark("・"),
        word("LSI"),
        mark(" "),
        word("設計"),
        word("エンジニア"),
      ]),
    ).toEqual({ words: ["半導体・", "LSI ", "設計", "エンジニ"], tail: "ア" });
  });

  it("開き括弧の前では折り、開き括弧のあとと閉じ括弧の前では折らない", async () => {
    expect(
      await platePartsWith([
        word("エンジニア"),
        mark("（"),
        word("組込み"),
        mark("）"),
      ]),
    ).toEqual({ words: ["エンジニア", "（組込み"], tail: "）" });
  });

  it("1 字のひらがなは前の語に付け、そのあとで折る", async () => {
    expect(
      await platePartsWith([
        word("社会"),
        word("の"),
        word("フィールドワーク"),
        word("担当"),
      ]),
    ).toEqual({ words: ["社会の", "フィールドワーク", "担"], tail: "当" });
  });

  it("1 字の語は、後ろに付く語(者)も頭に付く語(光、副)も、前後の語とのあいだで折らない", async () => {
    expect(
      await platePartsWith([
        word("電気"),
        word("主任"),
        word("技術"),
        word("者"),
      ]),
    ).toEqual({ words: ["電気", "主任", "技術"], tail: "者" });
    expect(
      await platePartsWith([word("光"), word("通信"), word("エンジニア")]),
    ).toEqual({ words: ["光通信", "エンジニ"], tail: "ア" });
    expect(
      await platePartsWith([word("システム"), word("副"), word("管理者")]),
    ).toEqual({ words: ["システム副管理"], tail: "者" });
  });

  it("記号と空白のあとなら、1 字の語の前で折る", async () => {
    expect(
      await platePartsWith([
        word("AI"),
        mark(" "),
        word("系"),
        word("エンジニア"),
      ]),
    ).toEqual({ words: ["AI ", "系エンジニ"], tail: "ア" });
  });

  it("字は見た目の 1 字で数え、異体字セレクタや絵文字の組を割らない", async () => {
    expect(await platePartsWith([word("技術"), word("者\uFE00")])).toEqual({
      words: ["技術"],
      tail: "者\uFE00",
    });
    expect(await platePartsWith([word("エンジニア"), mark("👩‍💻")])).toEqual({
      words: ["エンジニア"],
      tail: "👩‍💻",
    });
  });

  it("1 字の名前は、その字だけを行とつなぐ", async () => {
    expect(await platePartsWith([word("医")])).toEqual({
      words: [""],
      tail: "医",
    });
  });

  it("Intl.Segmenter の無いブラウザでは分けず、最後の 1 字だけを外す", async () => {
    vi.stubGlobal("Intl", { Segmenter: undefined });
    vi.resetModules();
    const { plateParts } = await import("@/lib/words");
    expect(plateParts("データサイエンティスト")).toEqual({
      words: ["データサイエンティス"],
      tail: "ト",
    });
  });
});

describe("wordsOf", () => {
  it("授業名の括弧の続きは開き括弧の前で折り、1 字のひらがなのあとで折る", async () => {
    expect(
      await wordsOfWith([
        word("特殊"),
        word("講義"),
        mark("（"),
        word("専門"),
        mark("）"),
        word("Ⅲ"),
        mark("（"),
        word("深層"),
        word("学習"),
        word("の"),
        word("応用"),
        mark("）"),
      ]),
    ).toEqual(["特殊", "講義", "（専門）", "Ⅲ", "（深層", "学習の", "応用）"]);
  });

  it("1 字のひらがなのあとで折っても、頭に付く漢字の 1 字は次の語とつなぐ", async () => {
    expect(
      await wordsOfWith([word("電子"), word("と"), word("光"), word("通信")]),
    ).toEqual(["電子と", "光通信"]);
  });

  it("Intl.Segmenter の無いブラウザでは分けない", async () => {
    vi.stubGlobal("Intl", { Segmenter: undefined });
    vi.resetModules();
    const { wordsOf } = await import("@/lib/words");
    expect(wordsOf("データ構造とアルゴリズム")).toEqual([
      "データ構造とアルゴリズム",
    ]);
  });
});
