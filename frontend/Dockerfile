# =============================================================================
# Unstructured Minds Frontend Dockerfile
# Multi-stage build for React application with nginx
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build - Compile TypeScript and bundle assets
# -----------------------------------------------------------------------------
FROM node:22-alpine AS build

WORKDIR /app

# Copy package files for dependency installation
COPY package*.json ./

# Install dependencies with clean install for reproducibility
RUN npm ci

# Copy source files
COPY . .

# Build the production bundle (route API calls through nginx proxy)
ENV VITE_API_URL=/api
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Serve with nginx
# -----------------------------------------------------------------------------
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy error pages
COPY public/50x.html /usr/share/nginx/html/50x.html

# Create non-root user for security (nginx alpine already has nginx user)
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# Expose HTTP port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
