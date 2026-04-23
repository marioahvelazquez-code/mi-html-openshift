# Build del frontend (transicion a Angular)
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend_angular/package*.json ./
RUN npm install
COPY frontend_angular .
RUN npm run build

# NGINX
FROM nginx:alpine
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/mjs.types /etc/nginx/conf.d/mjs.types
RUN sed -i '/http {/a \\tinclude /etc/nginx/conf.d/mjs.types;' /etc/nginx/nginx.conf
COPY --from=build /app/dist/frontend_angular/browser /usr/share/nginx/html
