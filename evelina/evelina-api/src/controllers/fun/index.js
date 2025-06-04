const axios = require('axios');
const { apiKeys } = require('../../config');

const funController = {
  getQuran: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.alquran.cloud/v1/quran/en.asad`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a quran verse.' });
    }
  },

  getBible: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://beta.ourmanna.com/api/v1/get?format=json&order=random`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a bible verse.' });
    }
  },

  getPack: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://evilinsult.com/generate_insult.php?lang=en&type=json`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a pack image.' });
    }
  },

  getBird: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.alexflipnote.dev/birb`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a bird image.' });
    }
  },

  getCat: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.thecatapi.com/v1/images/search`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a cat image.' });
    }
  },

  getDog: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://random.dog/woof.json`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a dog image.' });
    }
  },

  getCapybara: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.capy.lol/v1/capybara?json=true`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a capybara image.' });
    }
  },

  getUselessFact: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://uselessfacts.jsph.pl/random.json?language=en`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a useless fact.' });
    }
  },

  getAdvice: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.adviceslip.com/advice`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching advice.' });
    }
  },

  getDadJoke: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://icanhazdadjoke.com/slack`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a dad joke.' });
    }
  },

  getMeme: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://meme-api.com/gimme`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a meme.' });
    }
  },

  // Reaction GIFs
  getLick: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.otakugifs.xyz/gif?reaction=lick&format=gif`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a lick image.' });
    }
  },

  getKiss: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.otakugifs.xyz/gif?reaction=kiss&format=gif`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a kiss image.' });
    }
  },

  getPinch: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.otakugifs.xyz/gif?reaction=pinch&format=gif`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a pinch image.' });
    }
  },

  getCuddle: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.otakugifs.xyz/gif?reaction=cuddle&format=gif`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a cuddle image.' });
    }
  },

  getHug: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.otakugifs.xyz/gif?reaction=hug&format=gif`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a hug image.' });
    }
  },

  getPat: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.otakugifs.xyz/gif?reaction=pat&format=gif`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a pat image.' });
    }
  },

  getSlap: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.otakugifs.xyz/gif?reaction=slap&format=gif`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a slap image.' });
    }
  },

  getLaugh: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.otakugifs.xyz/gif?reaction=laugh&format=gif`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a laugh image.' });
    }
  },

  getCry: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.otakugifs.xyz/gif?reaction=cry&format=gif`);
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a cry image.' });
    }
  },

  // NSFW endpoints
  getMolest: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    const randomGifNumber = Math.floor(Math.random() * 20) + 1;
    res.json({ url: `https://api.evelina.bot/fun/molest/${randomGifNumber}.gif` });
  },

  getFuck: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://purrbot.site/api/img/nsfw/fuck/gif`);
      const data = response.data;
      res.json({ url: data.link || null });
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a fuck image.' });
    }
  },

  getAnal: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://purrbot.site/api/img/nsfw/anal/gif`);
      const data = response.data;
      res.json({ url: data.link || null });
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fet ching an anal image.' });
    }
  },

  getBlowjob: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://purrbot.site/api/img/nsfw/blowjob/gif`);
      const data = response.data;
      res.json({ url: data.link || null });
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a blowjob image.' });
    }
  },

  getCum: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://purrbot.site/api/img/nsfw/cum/gif`);
      const data = response.data;
      res.json({ url: data.link || null });
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a cum image.' });
    }
  },

  getPussylick: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://purrbot.site/api/img/nsfw/pussylick/gif`);
      const data = response.data;
      res.json({ url: data.link || null });
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a pussylick image.' });
    }
  },

  getThreesomeFFF: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://purrbot.site/api/img/nsfw/threesome_fff/gif`);
      const data = response.data;
      res.json({ url: data.link || null });
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a threesome FFF image.' });
    }
  },

  getThreesomeFFM: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://purrbot.site/api/img/nsfw/threesome_ffm/gif`);
      const data = response.data;
      res.json({ url: data.link || null });
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a threesome FFM image.' });
    }
  },

  getThreesomeFMM: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://purrbot.site/api/img/nsfw/threesome_mmf/gif`);
      const data = response.data;
      res.json({ url: data.link || null });
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching a threesome FMM image.' });
    }
  }
};

module.exports = funController;