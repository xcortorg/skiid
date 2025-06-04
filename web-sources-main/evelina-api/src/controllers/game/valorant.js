const axios = require('axios');
const { apiKeys } = require('../../config');

const valorantController = {
  getUser: async (req, res) => {
    const { name, tag, key } = req.query;

    if (!name) {
      return res.status(400).json({ error: '400', message: 'Parameter "name" is required' });
    }

    if (!tag) {
      return res.status(400).json({ error: '400', message: 'Parameter "tag" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.henrikdev.xyz/valorant/v2/account/${name}/${tag}`, {
        headers: {
          'Authorization': apiKeys.valorant
        }
      });

      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching Valorant user information.' });
    }
  },

  getRankedUser: async (req, res) => {
    const { name, tag, key } = req.query;

    if (!name) {
      return res.status(400).json({ error: '400', message: 'Parameter "name" is required' });
    }

    if (!tag) {
      return res.status(400).json({ error: '400', message: 'Parameter "tag" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      // First get user data to determine region
      const userResponse = await axios.get(`https://api.henrikdev.xyz/valorant/v2/account/${name}/${tag}`, {
        headers: {
          'Authorization': apiKeys.valorant
        }
      });

      const region = userResponse.data.data.region;

      // Then get ranked data
      const rankedResponse = await axios.get(`https://api.henrikdev.xyz/valorant/v2/mmr/${region}/${name}/${tag}`, {
        headers: {
          'Authorization': apiKeys.valorant
        }
      });

      res.json(rankedResponse.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching Valorant ranked user information.' });
    }
  },

  getRankedMatches: async (req, res) => {
    const { name, tag, key } = req.query;

    if (!name) {
      return res.status(400).json({ error: '400', message: 'Parameter "name" is required' });
    }

    if (!tag) {
      return res.status(400).json({ error: '400', message: 'Parameter "tag" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      // First get user data to determine region
      const userResponse = await axios.get(`https://api.henrikdev.xyz/valorant/v2/account/${name}/${tag}`, {
        headers: {
          'Authorization': apiKeys.valorant
        }
      });

      const region = userResponse.data.data.region;

      // Then get ranked matches history
      const matchesResponse = await axios.get(`https://api.henrikdev.xyz/valorant/v1/mmr-history/${region}/${name}/${tag}`, {
        headers: {
          'Authorization': apiKeys.valorant
        }
      });

      res.json(matchesResponse.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching Valorant ranked matches information.' });
    }
  }
};

module.exports = valorantController;