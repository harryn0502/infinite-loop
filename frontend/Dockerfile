# Stage 1: Development stage
FROM node:lts-alpine AS develop-stage

WORKDIR /app

# Copy package.json and lock file
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application source code
COPY . .

# Expose Vite's default port
EXPOSE 5173

# The command to run the development server
CMD ["npm", "run", "dev"]

# Stage 2: Build stage for production
FROM node:lts-alpine AS build-stage

WORKDIR /app
COPY package*.json ./

# Install all the node dependencies
RUN npm install

# Copy the source code from your local 'app' directory
COPY . .
RUN npm run build

# Stage 3: Production stage
FROM nginx:stable-alpine AS production-stage

# Copy the built static files from the build stage
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copy the custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 for Nginx
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]