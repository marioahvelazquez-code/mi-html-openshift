# Dockerfile para Angular + Nginx (producción)

FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install --legacy-peer-deps
COPY . .
RUN npm run build -- --output-path=dist/frontend_angular/browser

# Etapa 2: Nginx para servir la app
FROM nginx:alpine
COPY --from=build /app/dist/frontend_angular/browser/. /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/conf.d/default.conf.bak || true
RUN mkdir -p /run && chmod 777 /run
# Solución permisos para OpenShift
RUN mkdir -p /var/cache/nginx/client_temp && chmod -R 777 /var/cache/nginx
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
