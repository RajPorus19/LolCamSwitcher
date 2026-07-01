# nginx-rtmp with bundled config (avoids envsubst write to read-only bind mount)
FROM alfg/nginx-rtmp:latest

COPY docker/nginx-rtmp/nginx.conf /etc/nginx/nginx.conf

CMD ["nginx", "-g", "daemon off;"]
