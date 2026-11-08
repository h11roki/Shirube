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
    fixed_courses: [],
  },
  reading: null,
  result: {
    profile: {
      occupation: "データサイエンティスト",
      interpretation: "データサイエンティスト",
      assumption: null,
      skills: [
        "統計学",
        "機械学習",
        "Python",
        "データベース",
        "データ可視化",
        "データ解析",
      ],
    },
    semesters: [
      {
        grade: 3,
        term: "spring",
        credits: 10,
        courses: [
          {
            name: "データエンジニアリング基礎",
            relevance: "core",
            reason:
              "データ収集→整形加工→データベース抽出→可視化までを概観し、分析前処理や管理・保護の手順を仕事で再現できる。",
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
            name: "確率統計",
            relevance: "core",
            reason:
              "データ解析で不可欠な確率・仮説検定・区間推定を学び、実験/サンプルから根拠ある結論を作る基礎になる。データのばらつきを数値で扱える。",
            prerequisite_for: null,
            syllabus_code: "32505",
            syllabus_url:
              "https://syllabus.ritsumei.ac.jp/syllabus/s/r-syllabus/a0ifD000003RwbpQAC/202632505?language=ja",
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
            name: "データサイエンス・AI基礎",
            relevance: "core",
            reason:
              "データ記述や分析手法、機械学習の基礎、深層学習の流れを演習で習得し、データ分析の進め方を現場で使える形にする。",
            prerequisite_for: null,
            syllabus_code: "34924",
            syllabus_url:
              "https://syllabus.ritsumei.ac.jp/syllabus/s/r-syllabus/a0ifD000003RwbJQAS/202634924?language=ja",
            section_code: "34923",
            class_code: "G1",
            slots: [],
            credits: 2,
            class_confirmed: true,
          },
          {
            name: "応用Cプログラミング",
            relevance: "foundation",
            reason:
              "データ分析を進めるうえで、配列や文字・ファイル入出力、構造体、再帰などを扱う力が前提になる。演習課題の実装に効く。",
            prerequisite_for: "データサイエンス・AI基礎",
            syllabus_code: "32482",
            syllabus_url:
              "https://syllabus.ritsumei.ac.jp/syllabus/s/r-syllabus/a0ifD000003RwITQA0/202632482?language=ja",
            section_code: "32482",
            class_code: "6A",
            slots: [
              {
                weekday: "thu",
                period: 1,
              },
            ],
            credits: 2,
            class_confirmed: false,
          },
          {
            name: "データ構造とアルゴリズム",
            relevance: "foundation",
            reason:
              "効率的な処理のために、探索・整列・グラフなどの手順を選ぶ考え方が必要で、演習での自作コードを高速化/整理する前提になる。",
            prerequisite_for: "情報処理演習",
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
        ],
        continuing: [],
      },
      {
        grade: 3,
        term: "autumn",
        credits: 5,
        courses: [
          {
            name: "ＡＩ・機械学習",
            relevance: "core",
            reason:
              "回帰・分類・ニューラルネットの流れを学び、目的変数に対する予測モデルを構築して意思決定に使う。画像中心の学習で実装も扱う。",
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
            name: "情報処理演習",
            relevance: "core",
            reason:
              "Cで入力・配列・関数を実装し、データ処理の土台を作る。デバッグ/テストとレポート作成も扱うので、分析用コード開発に直結する。",
            prerequisite_for: null,
            syllabus_code: "31839",
            syllabus_url:
              "https://syllabus.ritsumei.ac.jp/syllabus/s/r-syllabus/a0ifD000003Rvv9QAC/202631839?language=ja",
            section_code: "31839",
            class_code: "6A",
            slots: [
              {
                weekday: "wed",
                period: 3,
              },
            ],
            credits: 1,
            class_confirmed: false,
          },
          {
            name: "情報処理",
            relevance: "foundation",
            reason:
              "情報処理で学ぶ配列・関数・ポインタなどの基礎が、情報処理演習のプログラム作成やデバッグに必要になる。",
            prerequisite_for: "情報処理演習",
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
        credits: 0,
        courses: [],
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
    offered_earlier: [
      "データエンジニアリング基礎",
      "データサイエンス・AI基礎",
      "データ構造とアルゴリズム",
      "応用Cプログラミング",
      "情報処理",
      "情報処理演習",
    ],
    unlinked: [],
  },
  failure: null,
} satisfies Plan;
