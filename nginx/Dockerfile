# ===== Build Angular =====
# pdfjs-dist@5.x requiere Node >=22.13 en build.
FROM node:22-alpine AS build

WORKDIR /app

COPY frontend-angular/app/package*.json ./
RUN npm ci --no-audit --no-fund

COPY frontend-angular/app .

RUN npx ng build --configuration=production

# ===== NGINX =====
FROM nginx:alpine

#  ELIMINA configs default
RUN rm -rf /etc/nginx/conf.d/*

# Mario: agrega tipo MIME para archivos .mjs (módulos JavaScript, necesario para pdf.worker)
RUN sed -i 's|application/javascript.*js;|application/javascript                                 js mjs;|' /etc/nginx/mime.types

# Copia  config
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# Copia Angular
COPY --from=build /app/dist/sitio/browser /usr/share/nginx/html

# Copia carpeta fichas locales
COPY frontend-angular/app/public/fichas /usr/share/nginx/html/fichas

# Mario: copia carpeta de fichas nacionales
COPY frontend-angular/app/public/nacional /usr/share/nginx/html/nacional