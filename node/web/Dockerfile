FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev
COPY src ./src
COPY public ./public
# Kopia design systemu zgodna z lockiem (bez ../shared w obrazie sprawdzana jest tylko integralność).
RUN node public/css/design-system/check.cjs
CMD ["node", "src/index.js"]
