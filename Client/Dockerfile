FROM node:18-alpine

WORKDIR /app

# Install curl for healthchecks
RUN apk --no-cache add curl

COPY package*.json ./

# Install dependencies
RUN npm install --no-audit --no-fund
# Explicitly install Monaco Editor
RUN npm install @monaco-editor/react --save

COPY . ./

EXPOSE 3000

CMD ["npm", "start"]