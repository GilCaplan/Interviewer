FROM node:18-alpine

WORKDIR /app

# Install curl for healthchecks
RUN apk --no-cache add curl

# Corrected npm configurations
RUN npm config set fetch-timeout 120000 && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000

COPY package.json ./
COPY package-lock.json ./

# Try multiple strategies to make npm install more reliable
RUN npm install --no-audit --no-fund --loglevel verbose || \
    npm install --no-audit --no-fund --registry=https://registry.npmjs.org/ || \
    npm install --no-audit --no-fund --legacy-peer-deps

COPY . ./

# Add proxy configuration
RUN if ! grep -q '"proxy":' package.json; then \
    sed -i 's/"private": true,/"private": true,\n  "proxy": "http:\/\/server:5000",/g' package.json; \
    fi

EXPOSE 3000

CMD ["npm", "start"]