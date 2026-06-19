# Stage 1: Build Vite React App
FROM node:20-alpine AS build

WORKDIR /app

# Copy package configuration files
COPY package*.json ./

# Install packages
RUN npm ci

# Copy the rest of the application code
COPY . .

# Set Vite build environment variables
ENV VITE_API_BASE_URL=http://localhost:8000

# Build project
RUN npm run build

# Stage 2: Serve using Nginx
FROM nginx:alpine

# Copy build artifacts to Nginx html directory
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 (will map to 5001 in docker-compose)
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
