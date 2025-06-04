const express = require('express');
const router = express.Router();
const { validateApiKey } = require('../db');
const {
  weatherController,
  cryptoController,
  stockController,
  googleController,
  minecraftController,
  spotifyController,
  githubController,
  discordController,
  robloxController
} = require('../controllers/utility');

// Add API key validation middleware
router.use(async (req, res, next) => {
  const { key } = req.query;
  if (!key) {
    return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
  }
  const isValidKey = await validateApiKey(key);
  if (!isValidKey) {
    return res.status(403).json({ error: '403', message: 'Invalid or unauthorized API key' });
  }
  next();
});

// Weather routes
router.get('/weather', weatherController.getWeather);

// Crypto routes
router.get('/crypto', cryptoController.convert);

// Stock routes
router.get('/stock', stockController.getStock);

// Google routes
router.get('/google/reverse', googleController.reverseImageSearch);

// Minecraft routes
router.get('/minecraft', minecraftController.getUser);

// Spotify routes
router.get('/spotify/track', spotifyController.getTrack);

// GitHub routes
router.get('/github/user', githubController.getUser);

// Discord routes
router.get('/discord/user', discordController.getUser);
router.get('/discord/guild', discordController.getGuild);
router.get('/discord/channel', discordController.getChannel);
router.get('/discord/invite', discordController.getInvite);

// Roblox routes
router.get('/roblox/user', robloxController.getUser);

module.exports = router;