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

async function wordsOfWith(segments: Segment[]) {
  const { wordsOf } = await wordsModuleWith(segments);
  return wordsOf(segments.map(({ segment }) => segment).join(""));
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

describe("wordsOf", () => {
  it("語のあいだで分ける", async () => {
    expect(
      await wordsOfWith([word("データ"), word("サイエンティスト")]),
    ).toEqual(["データ", "サイエンティスト"]);
  });

  it("記号と空白の前では折らず、あとでは次の語の前で折る", async () => {
    expect(
      await wordsOfWith([
        word("半導体"),
        mark("・"),
        word("LSI"),
        mark(" "),
        word("設計"),
        word("エンジニア"),
      ]),
    ).toEqual(["半導体・", "LSI ", "設計", "エンジニア"]);
  });

  it("開き括弧の前では折り、開き括弧のあとと閉じ括弧の前では折らない", async () => {
    expect(
      await wordsOfWith([
        word("エンジニア"),
        mark("（"),
        word("組込み"),
        mark("）"),
      ]),
    ).toEqual(["エンジニア", "（組込み）"]);
  });

  it("1 字の助詞は前の語に付け、そのあとで折る", async () => {
    expect(
      await wordsOfWith([
        word("社会"),
        word("の"),
        word("フィールドワーク"),
        word("担当"),
      ]),
    ).toEqual(["社会の", "フィールドワーク", "担当"]);
  });

  it("1 字の語は、後ろに付く語(者)も頭に付く語(光、副)も、前後の語とのあいだで折らない", async () => {
    expect(
      await wordsOfWith([word("電気"), word("主任"), word("技術"), word("者")]),
    ).toEqual(["電気", "主任", "技術者"]);
    expect(
      await wordsOfWith([word("光"), word("通信"), word("エンジニア")]),
    ).toEqual(["光通信", "エンジニア"]);
    expect(
      await wordsOfWith([word("システム"), word("副"), word("管理者")]),
    ).toEqual(["システム副管理者"]);
  });

  it("記号と空白のあとなら、1 字の語の前で折る", async () => {
    expect(
      await wordsOfWith([
        word("AI"),
        mark(" "),
        word("系"),
        word("エンジニア"),
      ]),
    ).toEqual(["AI ", "系エンジニア"]);
  });

  it("閉じ括弧のあとの 1 字の語は括弧につなぎ、続く開き括弧の前で折る", async () => {
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
    ).toEqual(["特殊", "講義", "（専門）Ⅲ", "（深層", "学習の", "応用）"]);
  });

  it("1 字の助詞のあとで折っても、頭に付く漢字の 1 字は次の語とつなぐ", async () => {
    expect(
      await wordsOfWith([word("電子"), word("と"), word("光"), word("通信")]),
    ).toEqual(["電子と", "光通信"]);
  });

  it("助詞でない 1 字のひらがなは、前後の語とつなぐ", async () => {
    expect(await wordsOfWith([word("ご"), word("案内"), word("係")])).toEqual([
      "ご案内係",
    ]);
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

describe("wordsByText", () => {
  it("文ごとに語の並びを引ける表にする", async () => {
    const { wordsByText } = await wordsModuleWith([
      word("データ"),
      word("サイエンティスト"),
    ]);
    expect(wordsByText(["データサイエンティスト"])).toEqual({
      データサイエンティスト: ["データ", "サイエンティスト"],
    });
  });
});

describe("splitTail", () => {
  it("最後の語から見た目の最後の 1 字を外す", async () => {
    const { splitTail } = await import("@/lib/words");
    expect(splitTail(["データ", "サイエンティスト"])).toEqual({
      words: ["データ", "サイエンティス"],
      tail: "ト",
    });
  });

  it("字は見た目の 1 字で数え、異体字セレクタや絵文字の組を割らない", async () => {
    const { splitTail } = await import("@/lib/words");
    expect(splitTail(["技術者\uFE00"])).toEqual({
      words: ["技術"],
      tail: "者\uFE00",
    });
    expect(splitTail(["エンジニア👩‍💻"])).toEqual({
      words: ["エンジニア"],
      tail: "👩‍💻",
    });
  });

  it("最後の語が 1 字なら、空の語を残してその前で折れるようにする", async () => {
    const { splitTail } = await import("@/lib/words");
    expect(splitTail(["電子と", "光"])).toEqual({
      words: ["電子と", ""],
      tail: "光",
    });
  });

  it("Intl.Segmenter の無いブラウザでも、最後の 1 字だけを外す", async () => {
    vi.stubGlobal("Intl", { Segmenter: undefined });
    vi.resetModules();
    const { splitTail } = await import("@/lib/words");
    expect(splitTail(["データサイエンティスト"])).toEqual({
      words: ["データサイエンティス"],
      tail: "ト",
    });
    expect(splitTail(["技術者\uFE00"])).toEqual({
      words: ["技術"],
      tail: "者\uFE00",
    });
  });
});

describe("bracketRuns", () => {
  it("語の頭の開き括弧は次の 1 字と、語の終わりの閉じ括弧は前の 1 字と組にする", async () => {
    const { bracketRuns } = await import("@/lib/words");
    expect(bracketRuns("（深層")).toEqual([
      { text: "（深", nowrap: true },
      { text: "層", nowrap: false },
    ]);
    expect(bracketRuns("学習の応用）")).toEqual([
      { text: "学習の応", nowrap: false },
      { text: "用）", nowrap: true },
    ]);
    expect(bracketRuns("【バスケットボール】")).toEqual([
      { text: "【バ", nowrap: true },
      { text: "スケットボー", nowrap: false },
      { text: "ル】", nowrap: true },
    ]);
  });

  it("重なった括弧は、全てを隣の 1 字と組にする", async () => {
    const { bracketRuns } = await import("@/lib/words");
    expect(bracketRuns("（「AI」入門））")).toEqual([
      { text: "（「A", nowrap: true },
      { text: "I」入", nowrap: false },
      { text: "門））", nowrap: true },
    ]);
  });

  it("括弧の隣の字は見た目の 1 字で数え、異体字セレクタを割らない", async () => {
    const { bracketRuns } = await import("@/lib/words");
    expect(bracketRuns("（葛\u{E0100}飾")).toEqual([
      { text: "（葛\u{E0100}", nowrap: true },
      { text: "飾", nowrap: false },
    ]);
  });

  it("Intl.Segmenter の無いブラウザでも、異体字セレクタや濁点の記号を前の字に付けて数える", async () => {
    vi.stubGlobal("Intl", { Segmenter: undefined });
    vi.resetModules();
    const { bracketRuns } = await import("@/lib/words");
    expect(bracketRuns("（葛\u{E0100}飾")).toEqual([
      { text: "（葛\u{E0100}", nowrap: true },
      { text: "飾", nowrap: false },
    ]);
    expect(bracketRuns("（か\u3099ら")).toEqual([
      { text: "（か\u3099", nowrap: true },
      { text: "ら", nowrap: false },
    ]);
  });

  it("語の真ん中の括弧は組にしない", async () => {
    const { bracketRuns } = await import("@/lib/words");
    expect(bracketRuns("（専門）Ⅲ")).toEqual([
      { text: "（専", nowrap: true },
      { text: "門）Ⅲ", nowrap: false },
    ]);
  });

  it("両端が括弧の短い語は全てを組にし、括弧の無い語はそのまま", async () => {
    const { bracketRuns } = await import("@/lib/words");
    expect(bracketRuns("(A)")).toEqual([{ text: "(A)", nowrap: true }]);
    expect(bracketRuns("データ")).toEqual([{ text: "データ", nowrap: false }]);
  });
});
