# ── Stage 1: Build optimized assets ──
FROM node:20-alpine AS builder
WORKDIR /build

# Install dependencies (layer cached if package*.json unchanged)
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Copy source files and run build
COPY build.js ./
COPY static/ ./static/
COPY src/ ./src/
RUN node build.js

# ── Stage 2: Serve with nginx ──
FROM nginx:stable-alpine

# Copy raw static files (served at /js/ and /css/ in dev via volume mount)
COPY static/ /usr/share/nginx/html/

# Keep a pristine copy of built assets that survives volume mounts.
# The entrypoint copies these into the shared volume on each container start.
COPY --from=builder /build/dist/ /build-assets/

# Also place them at the default nginx serve path for non-volume-mounted usage
COPY --from=builder /build/dist/ /usr/share/nginx/html/assets/

# Copy nginx configuration and entrypoint
# Pre-create nginx cache dirs with correct ownership so the container
# can start even with security_opt: no-new-privileges + cap_drop: ALL.
RUN mkdir -p /var/cache/nginx/client_temp \
             /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp \
             /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp && \
    chown -R nginx:nginx /var/cache/nginx

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
