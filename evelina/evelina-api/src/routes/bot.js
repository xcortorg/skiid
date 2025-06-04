const express = require('express');
const router = express.Router();
const { validateApiKey } = require('../db');
const { gunsController, uziController, topggController } = require('../controllers/bot');

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

// Guns.lol routes
router.get('/guns/user', gunsController.getUser);
router.get('/guns/uid', gunsController.getUid);

// Uzi.bio routes
router.get('/uzi/user', uziController.getUser);

// Top.gg routes
router.get('/topgg/voted', topggController.checkVote);

module.exports = router;