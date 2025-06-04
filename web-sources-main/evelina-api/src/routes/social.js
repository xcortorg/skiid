const express = require('express');
const router = express.Router();
const { validateApiKey } = require('../db');
const { 
  instagramController,
  tiktokController,
  twitterController,
  snapchatController,
  onlyfansController,
  steamController,
  youtubeController,
  pinterestController
} = require('../controllers/social');

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

// Instagram routes
router.get('/instagram/media', instagramController.getMedia);
router.get('/instagram/post', instagramController.getPost);
router.get('/instagram/posts', instagramController.getPosts);
router.get('/instagram/story', instagramController.getStory);
router.get('/instagram/user', instagramController.getUser);
router.get('/instagram/timeline', instagramController.getTimeline);
router.get('/instagram/postinfo', instagramController.getPostInfo);

// TikTok routes
router.get('/tiktok/media', tiktokController.getMedia);
router.get('/tiktok/fyp', tiktokController.getFYP);
router.get('/tiktok/user', tiktokController.getUser);
router.get('/tiktok/timeline', tiktokController.getTimeline);

// Twitter routes
router.get('/twitter/media', twitterController.getMedia);
router.get('/twitter/user', twitterController.getUser);
router.get('/twitter/timeline', twitterController.getTimeline);

// Snapchat routes
router.get('/snapchat/media', snapchatController.getMedia);
router.get('/snapchat/story', snapchatController.getStory);
router.get('/snapchat/user', snapchatController.getUser);

// OnlyFans routes
router.get('/onlyfans/user', onlyfansController.getUser);

// Steam routes
router.get('/steam/user', steamController.getUser);

// YouTube routes
router.get('/youtube/channel', youtubeController.getChannel);
router.get('/youtube/timeline', youtubeController.getTimeline);

// Pinterest routes
router.get('/pinterest/media', pinterestController.getMedia);

module.exports = router;