FROM node:24-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

# Extra hostnames the Vite dev server accepts (see vite.config.ts); baked in
# as a default here, still overridable via the environment at run time.
ARG ALLOWED_HOSTS=""
ENV ALLOWED_HOSTS=$ALLOWED_HOSTS

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
