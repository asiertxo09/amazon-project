# Frontend image: build the Vite app, serve the static bundle via nginx.
# Build context is the frontend/ directory (Plan_v2 P1-A4):
#   docker build -f frontend/Dockerfile -t opportunity-copilot-frontend ./frontend

# ── Build stage ──────────────────────────────────────────────────────────────
FROM node:22-slim AS build
WORKDIR /app

# Install deps against the lockfile first (cached on package manifests).
COPY package.json package-lock.json ./
RUN npm ci

# Build. VITE_API_URL is baked in at build time (Vite inlines import.meta.env).
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL
COPY . .
RUN npm run build

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
