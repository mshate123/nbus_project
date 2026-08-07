import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    // @ alias resolves to src/ — consistent with shadcn/ui conventions
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  test: {
    environment: "jsdom",
    coverage: {
      provider: "v8",
      thresholds: { lines: 5, functions: 5, branches: 5, statements: 5 },
    },
  },
});
