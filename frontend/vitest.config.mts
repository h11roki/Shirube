import {
  configDefaults,
  coverageConfigDefaults,
  defineConfig,
} from "vitest/config";

export default defineConfig({
  resolve: { tsconfigPaths: true },
  test: {
    environment: "node",
    exclude: [...configDefaults.exclude, "e2e/**"],
    coverage: {
      provider: "v8",
      include: ["src/lib/**/*.ts"],
      exclude: [
        ...coverageConfigDefaults.exclude,
        "src/lib/api/schema.ts",
        "src/lib/fonts.ts",
        "src/lib/session.ts",
        "src/lib/sign-out.ts",
        "src/lib/motion.ts",
        "src/lib/theme.ts",
      ],
      reporter: ["text-summary", "json-summary"],
      reportOnFailure: true,
      thresholds: { statements: 97, branches: 93, functions: 97, lines: 97 },
    },
  },
});
