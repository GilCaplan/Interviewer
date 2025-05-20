FROM node:18-alpine

WORKDIR /app

# Install curl for healthchecks
RUN apk --no-cache add curl

COPY package*.json ./

# Install dependencies
RUN npm install --no-audit --no-fund

COPY . ./

# Remove the automatic proxy modification as we're using environment variables
# We'll set the API URL via REACT_APP_API_URL environment variable in docker-compose

EXPOSE 3000

CMD ["npm", "start"]