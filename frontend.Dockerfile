# ── Stage 1: build the React app ─────────────────────────────────────────────
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files first (layer cache — only reinstalls when deps change)
COPY frontend/package.json frontend/package-lock.json* ./

RUN npm ci --silent

# Copy the rest of the frontend source
COPY frontend/ ./

# Create an optimised production build
RUN npm run build

# ── Stage 2: serve with nginx ─────────────────────────────────────────────────
FROM nginx:alpine AS runtime

# Copy the built assets into nginx's default serve directory
COPY --from=builder /app/build /usr/share/nginx/html

# Proxy /api calls to the backend container so the React app
# can talk to FastAPI without CORS issues
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
