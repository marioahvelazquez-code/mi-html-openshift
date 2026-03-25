FROM registry.access.redhat.com/ubi9/httpd-24
COPY index.html /var/www/html/index.html
EXPOSE 8080
