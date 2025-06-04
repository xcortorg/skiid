const socialRoutes = require('./social');
const funRoutes = require('./fun');
const utilityRoutes = require('./utility');
const gameRoutes = require('./game');
const botRoutes = require('./bot');
const valorantRoutes = require('./valorant');

const setupRoutes = (app) => {
  app.use('/', socialRoutes);
  app.use('/fun', funRoutes);
  app.use('/', utilityRoutes);
  app.use('/', gameRoutes);
  app.use('/', botRoutes);
  app.use('/valorant', valorantRoutes);
};

module.exports = { setupRoutes };