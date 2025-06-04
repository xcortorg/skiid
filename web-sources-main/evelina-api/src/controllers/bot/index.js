const axios = require('axios');
const { apiKeys } = require('../../config');

const gunsController = {
  getUser: async (req, res) => {
    const { username, key } = req.query;

    if (!username) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.post('https://guns.lol/api/user/lookup?type=username', {
        key: apiKeys.guns,
        username: username
      });

      res.json(response.data);
    } catch (err) {
      console.warn('Username lookup failed, attempting alias lookup...');

      try {
        const aliasResponse = await axios.post('https://guns.lol/api/user/lookup?type=alias', {
          key: apiKeys.guns,
          alias: username
        });
          
        res.json(aliasResponse.data);
      } catch (aliasErr) {
        res.status(500).json({
          error: '500',
          message: 'Error fetching informations from the Guns.lol Username or Alias.',
        });
      }
    }
  },

  getUid: async (req, res) => {
    const { id, key } = req.query;

    if (!id) {
      return res.status(400).json({ error: '400', message: 'Parameter "id" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    const parsedId = parseInt(id, 10);
    if (isNaN(parsedId)) {
      return res.status(400).json({ error: '400', message: '"id" must be a valid integer' });
    }

    try {
      const response = await axios.post('https://guns.lol/api/user/lookup?type=uid', {
        key: apiKeys.guns,
        uid: parsedId
      });

      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching informations from the Guns.lol UID.' });
    }
  }
};

const uziController = {
  getUser: async (req, res) => {
    const { username, key } = req.query;

    if (!username) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.post('https://uzi.bio/api/bot/lookup2', {
        key: apiKeys.uzi,
        username: username
      });

      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching informations from the Uzi.bio username.' });
    }
  }
};

const topggController = {
  checkVote: async (req, res) => {
    const { id } = req.query;

    if (!id) {
      return res.status(400).json({ error: '400', message: 'Parameter "id" is required' });
    }

    try {
      const response = await axios.get(`https://top.gg/api/bots/1242930981967757452/check?userId=${id}`, {
        headers: {
          'Authorization': apiKeys.topgg,
        }
      });

      res.json(response.data);
    } catch (err) {
      if (err.response) {
        res.status(err.response.status).json({ error: err.response.status, message: err.response.data.message });
      } else {
        res.status(500).json({ error: '500', message: 'Error fetching information from Top.gg API.' });
      }
    }
  }
};

module.exports = {
  gunsController,
  uziController,
  topggController
};