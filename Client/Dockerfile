FROM node:18-alpine

WORKDIR /app

# Install curl for healthchecks
RUN apk --no-cache add curl

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies with optimizations for Docker
RUN npm ci --only=production=false --no-audit --no-fund --prefer-offline

# Copy source code (except what's in .dockerignore)
COPY . ./

# Set environment for faster development builds
ENV NODE_ENV=development
ENV GENERATE_SOURCEMAP=false
ENV FAST_REFRESH=false
ENV TSC_COMPILE_ON_ERROR=true
ENV ESLINT_NO_DEV_ERRORS=true
ENV WDS_SOCKET_PORT=0

EXPOSE 3000

# Start the application
CMD ["npm", "start"]