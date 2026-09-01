# Stage 1: Build React application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency files trước để tận dụng Docker cache
COPY package*.json ./

# Cài dependencies
RUN npm ci

# Copy source code
COPY . .

# Using VITE_API_BASE_URL from Render
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Build production
RUN npm run build


# Stage 2: Serve static files
FROM nginx:alpine

# Copy build result vào nginx
COPY --from=builder /app/dist /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port
EXPOSE 80

# Chạy nginx
CMD ["nginx", "-g", "daemon off;"]