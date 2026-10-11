# Dev-oriented image (M0): installs deps and runs `next dev`.
# A production multi-stage build (standalone output) lands in M13.
FROM node:22-slim

RUN corepack enable

WORKDIR /app

COPY package.json ./
RUN pnpm install

COPY . .

EXPOSE 3000
CMD ["pnpm", "dev"]
