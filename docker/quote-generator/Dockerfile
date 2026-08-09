# syntax=docker/dockerfile:1.7
FROM node:22-bookworm-slim AS dependencies

WORKDIR /app

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

FROM dependencies AS builder

COPY . .
RUN npm run build

FROM node:22-bookworm-slim AS runtime

WORKDIR /app
ENV NODE_ENV=production
ENV PORT=8115
ENV HOSTNAME=0.0.0.0

# Next standalone contains only traced production dependencies. Static and
# public files are copied explicitly because Next does not include them there.
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 8115
CMD ["node", "server.js"]
