FROM node:24-slim@sha256:dc26ae92c9fb15cf6b1d63e20f0944b2efe0f115b20e00be48fb23fceb061c54 AS base

WORKDIR /app
COPY package.json ./
RUN corepack enable && corepack install

FROM base AS dev

EXPOSE 3000

FROM base AS build

ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
ARG SITE_URL
RUN pnpm build && pnpm prune --prod && rm -rf .next/cache

FROM node:24-slim@sha256:dc26ae92c9fb15cf6b1d63e20f0944b2efe0f115b20e00be48fb23fceb061c54 AS runner

ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY --from=build /app/package.json /app/next.config.ts /app/tsconfig.json ./
COPY --from=build /app/src ./src
COPY --from=build /app/public ./public
COPY --from=build /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/.next ./.next
USER node
EXPOSE 3000
CMD ["node_modules/.bin/next", "start"]
