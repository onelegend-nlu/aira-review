# AIRA frontend — Next.js. NEXT_PUBLIC_API_URL được nhúng lúc BUILD
# (trình duyệt của người dùng gọi thẳng tới backend), nên phải truyền
# qua build arg, không phải runtime env.
# Thống nhất dùng npm + package-lock.json: pnpm-lock.yaml đã lệch
# (thiếu react-markdown) nên bản build bằng pnpm không tái lập được.
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
