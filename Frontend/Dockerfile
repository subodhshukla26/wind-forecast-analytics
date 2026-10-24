# Stage 1: Build the React + Vite application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency manifests
COPY package.json package-lock.json* pnpm-lock.yaml* ./

# Install dependencies cleanly
RUN npm ci || npm install

# Copy source code and assets
COPY . .

# Build Vite production bundle
RUN npm run build

# Stage 2: Serve via Nginx
FROM nginx:alpine

# Remove default Nginx website
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration for SPA routing and backend proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose standard HTTP port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
