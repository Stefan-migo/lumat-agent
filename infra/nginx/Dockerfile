# Immutable panel delivery image: build the SPA and serve it from nginx.

FROM node:22.22.2-alpine AS build
WORKDIR /app
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM nginx:1.27-alpine
RUN rm /etc/nginx/conf.d/default.conf
COPY infra/nginx/panel.lumat.cl.conf /etc/nginx/conf.d/
COPY infra/nginx/agente.lumat.cl.conf /etc/nginx/conf.d/
COPY infra/nginx/snippets/ /etc/nginx/conf.d/snippets/
COPY --from=build /app/dist/ /usr/share/nginx/html/panel/app/
