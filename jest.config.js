export default {
  preset: "ts-jest",
  testEnvironment: "node",
  roots: ["<rootDir>/scripts"],
  // Jest's default pattern also matches `scripts/test.ts`, which is a CLI
  // script, not a test suite.
  testMatch: ["**/__tests__/**/*.test.ts", "**/*.spec.ts"],
  transform: {
    // The project tsconfig targets ESM for TrailBase; tests run as CommonJS.
    // Type-checking is `yarn type-check`'s job, so transpile only.
    "^.+\\.ts$": [
      "ts-jest",
      {
        tsconfig: {
          module: "commonjs",
          moduleResolution: "node",
          isolatedModules: true,
        },
      },
    ],
  },
  collectCoverageFrom: [
    "scripts/**/*.ts",
    "traildepot/scripts/**/*.ts",
    "!**/*.d.ts",
    "!**/__tests__/**",
    "!**/node_modules/**",
  ],
  coverageDirectory: "coverage",
  coverageReporters: ["text", "lcov", "html"],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },
  moduleFileExtensions: ["ts", "js", "json"],
  moduleNameMapper: {
    "^@/scripts/(.*)$": "<rootDir>/scripts/$1",
    "^@/types/(.*)$": "<rootDir>/types/$1",
  },
  setupFilesAfterEnv: ["<rootDir>/jest.setup.js"],
  testTimeout: 10000,
  verbose: true,
};
