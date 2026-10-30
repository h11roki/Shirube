FROM node:24-slim AS base

RUN corepack enable && corepack prepare pnpm@11.9.0 --activate

WORKDIR /app

FROM base AS dev

EXPOSE 3000

FROM base AS build

ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
ARG SITE_URL
RUN SITE_URL=${SITE_URL} pnpm build && pnpm prune --prod

FROM node:24-slim AS runner

ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY --from=build /app/package.json /app/next.config.ts ./
COPY --from=build /app/src/lib/security-headers.ts ./src/lib/
COPY --from=build /app/public ./public
COPY --from=build /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/.next ./.next
USER node
EXPOSE 3000
CMD ["node_modules/.bin/next", "start"]
