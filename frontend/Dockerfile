# ---- Build stage ----
FROM node:20-slim AS build
WORKDIR /app

# Copy only lockfiles first so this layer is cached unless dependencies change
COPY package*.json .

# Cache mount persists npm's download cache across builds — big speedup on rebuilds
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# Now copy the rest of the source
COPY . .

# Cache mount also helps Next.js's own build cache across builds
RUN --mount=type=cache,target=/app/.next/cache \
    npm run build

# ---- Production stage ----
FROM node:20-slim
WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME="0.0.0.0"
ENV PORT=3000

COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]