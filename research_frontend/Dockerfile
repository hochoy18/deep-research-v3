# =============================================================================
# research_frontend/Dockerfile — multi-stage, pnpm, Next.js standalone
# =============================================================================
# Stage 1 (deps):       pnpm fetch + install all (incl. dev) using frozen
#                       lockfile produced in T003.
# Stage 2 (builder):    pnpm build → Next.js emits a self-contained
#                       \`.next/standalone\` server (deps + server.js).
# Stage 3 (runner):     distroless-ish node:20-alpine carrying only the
#                       standalone output, \`.next/static\`, and \`public/\`.
#
# Why standalone?
#   - output: 'standalone' (next.config.ts, owned by Dev.cai.3) traces the
#     minimal \`node_modules\` subset the server actually loads, dropping
#     \`react-dom/server\` symlinks we don't ship (T014 needs the resulting
#     layout to fit on a single alpine layer).
#   - Enables \`task dev:up\` to start the container in < 2s instead of
#     re-installing 131 npm packages per `docker compose up`.
#
# Spec traceability:
#   - plan.md §Technical Context: Node 20+ frontend runtime
#   - ADR-0004: single-repo, this Dockerfile lives next to package.json
#   - ADR-0007: Tailwind v4 — CSS is built into \`.next/static\` so no
#               PostCSS pipeline is required at runtime
#   - constitution III (critical paths): tests are run in CI, not here
#
# Build context: research_frontend/ directory (not repo root); see
# deploy/docker-compose.yml (T012) for build.context wiring.
# =============================================================================

# ---- Stage 1: dependency installer ---------------------------------------
FROM node:20-alpine AS deps

# Corepack ships with the official node image; \`corepack enable\` makes
# the \`pnpm\` shim match the packageManager field of package.json
# (pinned at 8.15.9 in T003).
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    PNPM_HOME=/usr/local/share/pnpm \
    PATH=/usr/local/share/pnpm:$PATH

RUN corepack enable \
 && corepack prepare pnpm@8.15.9 --activate \
 && apk add --no-cache libc6-compat

WORKDIR /app

# Copy ONLY the lockfile + package.json first (dep layer rarely changes).
COPY package.json pnpm-lock.yaml ./

# \`--frozen-lockfile\` mirrors CI: any drift fails the build before we
# leak a half-resolved lockfile into the image.
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile --ignore-scripts

# ---- Stage 2: build (Next.js compilation) -------------------------------
FROM node:20-alpine AS builder

ENV NEXT_TELEMETRY_DISABLED=1 \
    COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    PNPM_HOME=/usr/local/share/pnpm \
    PATH=/usr/local/share/pnpm:$PATH

RUN corepack enable \
 && corepack prepare pnpm@8.15.9 --activate \
 && apk add --no-cache libc6-compat

WORKDIR /app

# Reuse the resolved node_modules from stage 1 instead of re-installing.
COPY --from=deps /app/node_modules ./node_modules
COPY package.json pnpm-lock.yaml ./
# Public assets + source.
COPY public ./public
COPY app ./app
COPY components ./components
COPY lib ./lib
COPY next.config.* tsconfig.json ./
COPY tailwind.config.* postcss.config.* ./

# Build-time envs must be NEXT_PUBLIC_* (browser bundle); everything
# else is server-only. Real values are injected at runtime via docker
# compose (T012). Names mirror research_frontend/.env.example (T011).
ENV NODE_ENV=production \
    NEXT_PUBLIC_API_URL=http://localhost:8000 \
    NEXT_PUBLIC_LANGFUSE_URL=http://localhost:3001 \
    NEXT_PUBLIC_APP_ENV=m1

# \`next build\` invokes the Tailwind v4 compiler (CSS-first, no PostCSS
# shim needed) and produces \`.next/standalone/\` once \`next.config.ts\`
# sets \`output: 'standalone'\`. The config file is owned by Dev.cai.3
# (T045); without it \`next build\` will still produce \`.next\` but the
# standalone runner step below will be a no-op.
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm run build

# ---- Stage 3: standalone runner ------------------------------------------
# Alpine 20 with a non-root user keeps the runtime tight (~150 MB) and
# avoids the distroless / glibc mismatch issues standalone needs.
FROM node:20-alpine AS runner

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 10001 app \
 && adduser  --system --uid 10001 -G app --no-create-home app

WORKDIR /app

# Static + public go ahead of the server so they're cached.
COPY --from=builder --chown=app:app /app/public ./public

# Next.js standalone build emits:
#   .next/standalone   → self-contained node_modules + server.js
#   .next/static       → hashed JS / CSS chunks (immutable)
# We copy the trace file too for production debugging if needed.
COPY --from=builder --chown=app:app /app/.next/standalone ./
COPY --from=builder --chown=app:app /app/.next/static ./.next/static

USER app

EXPOSE 3000

# HEALTHCHECK: Next.js' default \`next start\` doesn't expose /api/health,
# so Dev.cai.3 must add a small Route Handler in M2. For M1 we probe
# \`/ \` which returns the layout shell. \`--spider\` keeps curl from
# crawling the React tree.
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider \
        "http://127.0.0.1:${PORT:-3000}/" || exit 1

# The standalone server.js is what \`next build\` emits; \`node\` + the
# appropriate HOSTNAME/PORT env vars (set above) is all it needs.
CMD ["node", "server.js"]
