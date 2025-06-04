const express = require('express');
const router = express.Router();
const { validateApiKey } = require('../db');
const funController = require('../controllers/fun');

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

// Fun routes
router.get('/quran', funController.getQuran);
router.get('/bible', funController.getBible);
router.get('/pack', funController.getPack);
router.get('/bird', funController.getBird);
router.get('/cat', funController.getCat);
router.get('/dog', funController.getDog);
router.get('/capybara', funController.getCapybara);
router.get('/uselessfact', funController.getUselessFact);
router.get('/advice', funController.getAdvice);
router.get('/dadjoke', funController.getDadJoke);
router.get('/meme', funController.getMeme);

// Reaction GIFs
router.get('/lick', funController.getLick);
router.get('/kiss', funController.getKiss);
router.get('/pinch', funController.getPinch);
router.get('/cuddle', funController.getCuddle);
router.get('/hug', funController.getHug);
router.get('/pat', funController.getPat);
router.get('/slap', funController.getSlap);
router.get('/laugh', funController.getLaugh);
router.get('/cry', funController.getCry);

// NSFW routes
router.get('/molest', funController.getMolest);
router.get('/fuck', funController.getFuck);
router.get('/anal', funController.getAnal);
router.get('/blowjob', funController.getBlowjob);
router.get('/cum', funController.getCum);
router.get('/pussylick', funController.getPussylick);
router.get('/threesome_fff', funController.getThreesomeFFF);
router.get('/threesome_ffm', funController.getThreesomeFFM);
router.get('/threesome_fmm', funController.getThreesomeFMM);

module.exports = router;