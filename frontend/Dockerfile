FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ARG VITE_APP_VERSION=local
ARG VITE_APP_BUILD_DATE=local
ENV VITE_APP_VERSION=$VITE_APP_VERSION VITE_APP_BUILD_DATE=$VITE_APP_BUILD_DATE
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
