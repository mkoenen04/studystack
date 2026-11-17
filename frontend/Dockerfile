FROM nginx:1.27-alpine

# Port nginx listens on; Cloud Run overrides this at runtime
ENV PORT=8080

# nginx fills in ${PORT} in this template when the container starts
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template

# Static site files
COPY index.html /usr/share/nginx/html/index.html
COPY js /usr/share/nginx/html/js

EXPOSE 8080