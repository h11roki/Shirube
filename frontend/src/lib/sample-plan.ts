import type { Plan } from "@/lib/api/client";

export const SAMPLE_PLAN = {
  id: "de4d4f3e-5c1c-4673-b6c7-93ba0a97e5e3",
  status: "succeeded",
  stage: null,
  conditions: {
    occupation: "データサイエンティスト",
    department: "情",
    year: 2026,
    grade: 3,
    term: "spring",
    chosen_classes: {
      確率統計: "6B",
    },
    credit_limit: 16,
  },
  result: {
    profile: {
      occupation: "データサイエンティスト",
      interpretation: "データサイエンティスト",
      assumption: null,
      skills: [
        "統計学",
        "機械学習",
        "データ分析",
        "プログラミング",
        "データ可視化",
      ],
    },
    semesters: [
      {
        grade: 3,
        term: "spring",
        credits: 12,
        courses: [
          {
            name: "データエンジニアリング基礎",
            relevance: "core",
            reason:
              "データ表現、収集、整形・加工、DB抽出、可視化まで扱い、データ分析を回す実務の中心を学べるため。",
            prerequisite_for: null,
            syllabus_code: "34926",
            syllabus_url:
              "https://syllabus.ritsumei.ac.jp/syllabus/s/r-syllabus/a0ifD000003RwdFQAS/202634926?language=ja",
            section_code: "34925",
            class_code: "G1",
            slots: [],
            credits: 2,
            class_confirmed: true,
          },
          {
            name: "データサイエンス・AI基礎",
            relevance: "core",
            reason:
              "データ分析の進め方と設計、数学の基礎、教師あり/なし学習や深層学習の入口を演習で習得できるため。データサイエンティストの中核スキルに直結する。",
            prerequisite_for: null,
            syllabus_code: "34923",
            syllabus_url:
              "https://syllabus.ritsumei.ac.jp/syllabus/s/r-syllabus/a0ifD000003RwaLQAS/202634923?language=ja",
            section_code: "34923",
            class_code: "G1",
            slots: [],
            credits: 2,
            class_confirmed: true,
          },
          {
            name: "確率統計",
            relevance: "core",
            reason:
              "確率分布・推定・仮説検定などの基礎理論と、Matlab等での実践的統計処理を学べるため。統計的判断の土台になる。",
            prerequisite_for: null,
            syllabus_code: "32506",
            syllabus_url:
              "https://syllabus.ritsumei.ac.jp/syllabus/s/r-syllabus/a0ifD000003RwcnQAC/202632506?language=ja",
            section_code: "32506",
            class_code: "6B",
            slots: [
              {
                weekday: "mon",
                period: 4,
              },
            ],
            credits: 2,
            class_confirmed: true,
          },
          {
            name: "メディア情報処理",
            relevance: "core",
            reason:
              "音声・画像を中心に信号処理や画像処理の解析基礎をMATLABで実装するため。特徴抽出や類似性評価など可視化と分析に効く。",
            prerequisite_for: null,
            syllabus_code: "32510",
            syllabus_url:
              "https://syllabus.ritsumei.ac.jp/syllabus/s/r-syllabus/a0ifD000003RwgfQAC/202632510?language=ja",
            section_code: "32510",
            class_code: "6T",
            slots: [
              {
                weekday: "tue",
                period: 4,
              },
            ],
            credits: 2,
            class_confirmed: true,
          },
          {
            name: "データ構造とアルゴリズム",
            relevance: "core",
            reason:
              "探索・整列・グラフなどを通じて効率的アルゴリズムの選択を学ぶため。大量データ解析で計算量を意識した実装に必要。",
            prerequisite_for: null,
            syllabus_code: "32481",
            syllabus_url:
              "https://syllabus.ritsumei.ac.jp/syllabus/s/r-syllabus/a0ifD000003RwHVQA0/202632481?language=ja",
            section_code: "32481",
            class_code: "6T",
            slots: [
              {
                weekday: "tue",
                period: 5,
              },
            ],
            credits: 2,
            class_confirmed: true,
          },
          {
            name: "電子情報基礎数学",
            relevance: "foundation",
            reason:
              "指数・対数、微分積分、行列、ベクトルなどを道具として計算できるようにする。確率分布や推定・検定で使う数学の前提になるため。",
            prerequisite_for: "確率統計",
            syllabus_code: "32459",
            syllabus_url:
              "https://syllabus.ritsumei.ac.jp/syllabus/s/r-syllabus/a0ifD000003Rvz7QAC/202632459?language=ja",
            section_code: "32459",
            class_code: "6T",
            slots: [
              {
                weekday: "thu",
                period: 2,
              },
            ],
            credits: 2,
            class_confirmed: true,
          },
        ],
        continuing: [],
      },
      {
        grade: 3,
        term: "autumn",
        credits: 4,
        courses: [
          {
            name: "ＡＩ・機械学習",
            relevance: "core",
            reason:
              "機械学習のワークフローから回帰・分類、ニューラルネットワーク、CNNまでMATLABで実装するため。予測モデル開発に直結する。",
            prerequisite_for: null,
            syllabus_code: "32516",
            syllabus_url:
              "https://syllabus.ritsumei.ac.jp/syllabus/s/r-syllabus/a0ifD000003Rwn7QAC/202632516?language=ja",
            section_code: "32516",
            class_code: "6T",
            slots: [
              {
                weekday: "tue",
                period: 3,
              },
            ],
            credits: 2,
            class_confirmed: true,
          },
          {
            name: "情報処理",
            relevance: "foundation",
            reason:
              "Cでデータ読み込みや配列、関数を扱い、実装の基礎を作る。探索・整列・グラフを作る前に必要なプログラミング力になるため。",
            prerequisite_for: "データ構造とアルゴリズム",
            syllabus_code: "31825",
            syllabus_url:
              "https://syllabus.ritsumei.ac.jp/syllabus/s/r-syllabus/a0ifD000003RwtmQAC/202631825?language=ja",
            section_code: "31825",
            class_code: "6T",
            slots: [
              {
                weekday: "thu",
                period: 2,
              },
            ],
            credits: 2,
            class_confirmed: true,
          },
        ],
        continuing: [],
      },
      {
        grade: 4,
        term: "spring",
        credits: 2,
        courses: [
          {
            name: "特殊講義（専門）Ⅲ（深層学習の応用）",
            relevance: "core",
            reason:
              "分類・回帰から時系列分類、検出、生成まで深層学習の応用をMATLABで実装し、実務のモデル設計に近づくため。",
            prerequisite_for: null,
            syllabus_code: "32519",
            syllabus_url:
              "https://syllabus.ritsumei.ac.jp/syllabus/s/r-syllabus/a0ifD000003Rwq1QAC/202632519?language=ja",
            section_code: "32519",
            class_code: "6T",
            slots: [
              {
                weekday: "tue",
                period: 1,
              },
            ],
            credits: 2,
            class_confirmed: true,
          },
        ],
        continuing: [],
      },
      {
        grade: 4,
        term: "autumn",
        credits: 0,
        courses: [],
        continuing: [],
      },
    ],
    unplaced: [],
    taken: [],
    offered_earlier: [],
    unlinked: [],
  },
  failure: null,
} satisfies Plan;
