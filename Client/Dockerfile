FROM node:18-alpine

WORKDIR /app

# Set npm configurations to make installation more reliable
RUN npm config set timeout 120000 && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000

COPY package.json ./
COPY package-lock.json ./

# Try multiple strategies to make npm install more reliable
RUN npm install --no-audit --no-fund --loglevel verbose || \
    npm install --no-audit --no-fund --registry=https://registry.npmjs.org/ || \
    npm install --no-audit --no-fund --legacy-peer-deps

COPY . ./

EXPOSE 3000

CMD ["npm", "start"]