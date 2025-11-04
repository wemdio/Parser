# Multi-stage build для React приложения
FROM node:18-alpine as build

WORKDIR /app

# Копирование package файлов и установка зависимостей
COPY package*.json ./
RUN npm ci --only=production --ignore-scripts

# Копирование исходного кода
COPY public/ ./public/
COPY src/ ./src/

# Сборка приложения
RUN npm run build

# Production stage - используем nginx для раздачи статики
FROM nginx:alpine

# Удаляем дефолтную конфигурацию nginx
RUN rm /etc/nginx/conf.d/default.conf

# Копирование собранного приложения
COPY --from=build /app/build /usr/share/nginx/html

# Копирование нашей конфигурации nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Проверяем что файлы скопированы
RUN ls -la /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

