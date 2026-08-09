FROM nginx:1.27-alpine

COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY local-public-preview.conf.template /etc/nginx/local-public-preview-templates/default.conf.template
COPY 10-dmc-gateway-mode.envsh /docker-entrypoint.d/10-dmc-gateway-mode.envsh
RUN chmod 0755 /docker-entrypoint.d/10-dmc-gateway-mode.envsh
