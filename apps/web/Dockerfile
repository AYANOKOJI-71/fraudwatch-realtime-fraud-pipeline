FROM node:22-alpine AS build
WORKDIR /app
COPY apps/web/package.json apps/web/pnpm-lock.yaml* ./
RUN corepack enable && pnpm install --frozen-lockfile=false
COPY apps/web ./
RUN pnpm build

FROM nginx:1.27-alpine
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
