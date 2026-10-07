# 前端镜像：多阶段构建
# 阶段 1：Node 环境跑 vite build 产出静态文件
# 阶段 2：只用 nginx 托管静态文件（最终镜像里没有 Node 和源码，体积小）
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
