FROM node:22-alpine AS build

WORKDIR /app/apps/web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
ARG VITE_API_BASE_URL=http://localhost:8080/api/v1
ARG VITE_ENV=development
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_ENV=${VITE_ENV}
RUN npm run build

FROM nginx:1.27-alpine
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/web/dist/ /usr/share/nginx/html/
EXPOSE 80
