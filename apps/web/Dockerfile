FROM node:20-alpine
WORKDIR /app

# Copy only the package files first (for caching)
COPY apps/web/package*.json ./
RUN npm install

# Copy web app source code
COPY apps/web/ .

# ✅ Copy shared contracts (relative to build context root)
COPY packages/contracts ./packages/contracts

# Build the Next.js app
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]