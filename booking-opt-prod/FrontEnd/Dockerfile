# Dockerfile for static front-end
FROM nginx:alpine

WORKDIR /usr/share/nginx/html

# Remove default content (if any)
RUN rm -rf ./*

# Copy static assets
COPY index.html .
COPY css ./css
COPY js ./js

# Expose port 80 and run nginx in foreground
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
