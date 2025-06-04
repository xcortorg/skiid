const express = require('express');
const router = express.Router();
const { validateApiKey } = require('../db');
const { valorantController } = require('../controllers/game');

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

// Valorant routes
router.get('/user', valorantController.getUser);
router.get('/ranked/user', valorantController.getRankedUser);
router.get('/ranked/matches', valorantController.getRankedMatches);

module.exports = router;