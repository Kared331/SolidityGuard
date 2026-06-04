FROM node:20-alpine AS build
ARG VITE_API_KEY=
ARG VITE_API_BASE_URL=
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Inject build-time env vars
RUN VITE_API_KEY="${VITE_API_KEY}" VITE_API_BASE_URL="${VITE_API_BASE_URL}" npm run build

FROM nginx:alpine

# 1.12: Create non-root user for nginx
RUN addgroup -g 1000 -S appuser && \
    adduser -u 1000 -S appuser -G appuser && \
    mkdir -p /var/cache/nginx /var/log/nginx /tmp/nginx && \
    chown -R appuser:appuser /var/cache/nginx /var/log/nginx /tmp/nginx /usr/share/nginx/html && \
    touch /var/run/nginx.pid && \
    chown appuser:appuser /var/run/nginx.pid

COPY --from=0 --chown=appuser:appuser /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

USER appuser

EXPOSE 8080
