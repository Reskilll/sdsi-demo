'use strict';

const { build, DEFAULT_PORT } = require('./server');

const port = Number(process.env.PORT) || DEFAULT_PORT;
const host = process.env.HOST || '127.0.0.1';

build({ logger: true })
  .then((app) => app.listen({ port, host }))
  .then((address) => {
    console.log(`URL shortener listening on ${address}`);
  })
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });