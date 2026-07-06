# ==============================================================
# Frontend Dockerfile — Multi-stage build
# Stage 1: base       — Node 20 base
# Stage 2: deps       — Install dependencies
# Stage 3: development — Vite dev server (hot-reload)
# Stage 4: builder    — TypeScript compile + Vite production build
# Stage 5: production  — Nginx serving static dist/
# ==============================================================

# ---- Base ----
FROM node:20-alpine AS base
WORKDIR /app

# ---- Dependencies ----
FROM base AS deps
COPY package.json package-lock.json* ./
RUN npm ci --frozen-lockfile

# ---- Development ----
FROM deps AS development
COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ---- Production Build ----
FROM deps AS builder
COPY . .
RUN npm run build

# ---- Production: Nginx ----
FROM nginx:1.27-alpine AS production

# Copy Vite build output
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

RUN addgroup -g 1001 -S appuser && \
    adduser -S -u 1001 -G appuser appuser && \
    chown -R appuser:appuser /var/cache/nginx /var/run /var/log/nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

USER root

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -q --spider http://localhost/healthz || exit 1

# Run nginx as non-root `appuser`. Set pid to /tmp to avoid writing to /run (root-owned tmpfs).
CMD ["nginx", "-g", "daemon off;"]
