# Multi-stage frontend Dockerfile.
# Targets:
#   deps   — install pnpm + all dependencies
#   build  — shadcn init (pre-baked) + production build
#   prod   — nginx serving static files
#   test   — vitest runner

FROM node:26-bookworm-slim AS deps

WORKDIR /app

# Non-interactive mode (prevents pnpm from prompting during build)
ENV CI=true

# Install pnpm inside the container — no host pnpm required
RUN npm install -g pnpm@11 --quiet

# Copy package manifests (pnpm-workspace.yaml needed for allowBuilds config)
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc* ./

# Install all dependencies (including devDeps for build and E2E)
RUN pnpm install --frozen-lockfile

# Install Chromium and its Linux dependencies for the Playwright E2E target.
RUN pnpm exec playwright install --with-deps chromium

# ── Shadcn init + build ──────────────────────────────────────────────────────
FROM deps AS build

# Copy full source
COPY . .

# Pre-bake shadcn/ui: run non-interactive init then add required components.
# This generates components.json and src/components/ui/* at build time.
# No manual setup required on the host.
RUN pnpm dlx shadcn@latest init --yes \
    && pnpm dlx shadcn@latest add table --yes \
    && pnpm dlx shadcn@latest add card --yes \
    && pnpm dlx shadcn@latest add badge --yes \
    && pnpm dlx shadcn@latest add button --yes

# Build production bundle
RUN pnpm build

# ── Production target ────────────────────────────────────────────────────────
FROM nginx:alpine AS prod

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# nginx config: proxy /api/* to backend, serve SPA on all other routes
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

# ── Test target ──────────────────────────────────────────────────────────────
FROM build AS test

CMD ["pnpm", "test:coverage"]
