const axios = require('axios');
const { apiKeys } = require('../../config');

const weatherController = {
  getWeather: async (req, res) => {
    const { city: weatherCity, key } = req.query;

    if (!weatherCity) {
      return res.status(400).json({ error: '400', message: 'Parameter "city" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`http://api.weatherapi.com/v1/current.json?key=${apiKeys.weather}&q=${weatherCity}`, {
      });

      const data = response.data;
      const extractedData = {
        city: data.location?.name || null,
        country: data.location?.country || null,
        condition: data.current.condition?.text || null,
        condition_image: data.current.condition?.icon || null,
        temp_c: data.current?.temp_c || 0,
        temp_f: data.current?.temp_f || 0,
        wind_mph: data.current?.wind_mph || 0,
        wind_kph: data.current?.wind_kph || 0,
        humidity: data.current?.humidity || 0,
      };

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching informations from the City.' });
    }
  }
};

const cryptoController = {
  convert: async (req, res) => {
    const { amount, from, to, key } = req.query;

    if (!amount) {
      return res.status(400).json({ error: '400', message: 'Parameter "amount" is required' });
    }
    
    if (!from) {
      return res.status(400).json({ error: '400', message: 'Parameter "from" is required' });
    }
    
    if (!to) {
      return res.status(400).json({ error: '400', message: 'Parameter "to" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.coinconvert.net/convert/${from}/${to}?amount=${amount}`);
      
      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching the Crypto result' });
    }
  }
};

const stockController = {
  getStock: async (req, res) => {
    const { name, key } = req.query;

    if (!name) {
      return res.status(400).json({ error: '400', message: 'Parameter "name" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.post('https://yahoo-finance160.p.rapidapi.com/info', 
        { stock: name },
        {
          headers: {
            'X-RapidAPI-Key': apiKeys.rapidApi,
            'X-RapidAPI-Host': 'yahoo-finance160.p.rapidapi.com',
            'Content-Type': 'application/json'
          }
        }
      );

      const data = response.data;

      const extractedData = {
        price: data.ask || null,
        close: data.previousClose || null,
        open: data.open || null,
        low: data.dayLow || null,
        high: data.dayHigh || null,
      };

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching information from the API.' });
    }
  }
};

const googleController = {
  reverseImageSearch: async (req, res) => {
    const { image: imageUrl, key } = req.query;

    if (!imageUrl) {
      return res.status(400).json({ error: '400', message: 'Parameter "image" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://reverse-image-search-by-copyseeker.p.rapidapi.com/?imageUrl=${imageUrl}`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });

      const data = response.data;

      const pages = data.Pages || [];
      const extractedData = pages.map(page => ({
        name: page?.Title,
        url: page?.Url,
        image: page?.MatchingImages[0],
        rank: page?.Rank
      }));

      res.json({ results: extractedData });
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching reverse image search results.' });
    }
  }
};

const minecraftController = {
  getUser: async (req, res) => {
    const { username, key } = req.query;

    if (!username) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const mojangResponse = await axios.get(`https://api.mojang.com/users/profiles/minecraft/${username}`);
      const { id: uuid, name } = mojangResponse.data;

      const labyResponse = await axios.get(`https://laby.net/api/v3/user/${uuid}/profile`);
      const { name_history, textures } = labyResponse.data;

      const history = name_history.map(entry => ({
        name: entry.name,
        changed: entry.changed_at ? Math.floor(new Date(entry.changed_at).getTime() / 1000) : null
      }));

      const headUrl = `https://mineskin.eu/avatar/${username}`;
      const skinUrl = `https://visage.surgeplay.com/full/${uuid}`;

      res.json({
        uuid,
        name,
        history,
        head: headUrl,
        skin: skinUrl
      });
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching Minecraft user profile.' });
    }
  }
};

const spotifyController = {
  getTrack: async (req, res) => {
    const { q: spotifyTrackSearch, key } = req.query;

    if (!spotifyTrackSearch) {
      return res.status(400).json({ error: '400', message: 'Parameter "q" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://spotify23.p.rapidapi.com/search/?q=${spotifyTrackSearch}&type=tracks&offset=0&limit=1&numberOfTopResults=1`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });

      const data = response.data;
      const extractedData = {
        track: {
          id: data?.tracks.items[0].data.id || null,
          name: data?.tracks.items[0].data.name || null,
          url: `https://open.spotify.com/track/${data?.tracks.items[0].data.id}` || null,
          duration: data?.tracks.items[0].data.duration.totalMilliseconds || null,
          rating: data?.tracks.items[0].data.contentRating.label || null,
        },
        album: {
          id: data?.tracks.items[0].data.albumOfTrack.id || null,
          name: data?.tracks.items[0].data.albumOfTrack.name || null,
          url: data?.tracks.items[0].data.albumOfTrack.sharingInfo.shareUrl || null,
        },
        artist: {
          id: data?.tracks.items[0].data.artists.items[0].uri.slice(-22) || null,
          name: data?.tracks.items[0].data.artists.items[0].profile.name || null,
          url: `https://open.spotify.com/artists/${data?.tracks.items[0].data.artists.items[0].uri.slice(-22)}` || null,
        },
      };

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching the Spotify Track' });
    }
  }
};

const githubController = {
  getUser: async (req, res) => {
    const { username: githubUsername, key } = req.query;

    if (!githubUsername) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.github.com/users/${githubUsername}`);

      const data = response.data;
      const extractedData = {
        username: data?.login || null,
        display: data?.name || null,
        avatar: data?.avatar_url || null,
        bio: data?.bio || null,
        repos: data?.public_repos || 0,
        followers: data?.followers || 0,
        following: data?.following || 0,
        created: data?.created_at || 0,
      };

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching the Github Username' });
    }
  }
};

const discordController = {
  getUser: async (req, res) => {
    const { id: discordID, key } = req.query;

    if (!discordID) {
      return res.status(400).json({ error: '400', message: 'Parameter "id" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://discord.com/api/v10/users/${discordID}`, {
        headers: {
          'Authorization': `Bot ${apiKeys.discord}`
        }
      });

      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching informations from the Discord ID.' });
    }
  },

  getGuild: async (req, res) => {
    const { id: discordID, key } = req.query;

    if (!discordID) {
      return res.status(400).json({ error: '400', message: 'Parameter "id" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://discord.com/api/v10/guilds/${discordID}`, {
        headers: {
          'Authorization': `Bot ${apiKeys.discord}`
        }
      });

      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching informations from the Discord ID.' });
    }
  },

  getChannel: async (req, res) => {
    const { id: discordID, key } = req.query;

    if (!discordID) {
      return res.status(400).json({ error: '400', message: 'Parameter "id" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://discord.com/api/v10/channels/${discordID}`, {
        headers: {
          'Authorization': `Bot ${apiKeys.discord}`
        }
      });

      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching informations from the Discord ID.' });
    }
  },

  getInvite: async (req, res) => {
    const { code: invite, key } = req.query;

    if (!invite) {
      return res.status(400).json({ error: '400', message: 'Parameter "code" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://discord.com/api/v10/invites/${invite}`, {
        headers: {
          'Authorization': `Bot ${apiKeys.discord}`
        }
      });

      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching informations from the Discord ID.' });
    }
  }
};

const robloxController = {
  getUser: async (req, res) => {
    const { username, key } = req.query;

    if (!username) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    const headers = {
      "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36"
    };

    const getUserId = async (username) => {
      try {
        const response = await axios.get('https://www.roblox.com/users/profile', {
          params: { username },
          headers
        });
        if (response.status === 200) {
          return response.request.res.responseUrl.split('/')[4];
        }
      } catch (error) {
        console.error('Error fetching user ID:', error);
        return null;
      }
    };

    const getUserStats = async (user_id) => {
      const stats = ["friends", "followers", "followings"];
      const payload = {};

      for (const statistic of stats) {
        try {
          const response = await axios.get(`https://friends.roblox.com/v1/users/${user_id}/${statistic}/count`, { headers });
          payload[statistic] = response.data.count;
        } catch (error) {
          console.error(`Error fetching ${statistic} count:`, error);
          payload[statistic] = 0;
        }
      }

      return payload;
    };

    const getUserAvatar = async (user_id) => {
      try {
        const response = await axios.get(`https://www.roblox.com/users/${user_id}/profile`, { headers });
        const $ = cheerio.load(response.data);
        return $('meta[property="og:image"]').attr('content');
      } catch (error) {
        console.error('Error fetching user avatar:', error);
        return null;
      }
    };

    const getUserProfile = async (user_id) => {
      try {
        const response = await axios.get(`https://users.roblox.com/v1/users/${user_id}`, { headers });
        return response.data;
      } catch (error) {
        console.error('Error fetching user profile:', error);
        return null;
      }
    };

    const cache = new Map();
    const cacheKey = `roblox-${username.toLowerCase()}`;
    
    if (cache.has(cacheKey)) {
      return res.json(cache.get(cacheKey));
    }

    try {
      const user_id = await getUserId(username);
      if (!user_id) {
        return res.status(404).json({ error: '404', message: 'User not found' });
      }

      const profileData = await getUserProfile(user_id);
      const profileStats = await getUserStats(user_id);
      const userAvatar = await getUserAvatar(user_id);

      const payload = {
        username: profileData.name,
        display_name: profileData.displayName,
        bio: profileData.description,
        id: user_id,
        created_at: new Date(profileData.created).getTime() / 1000,
        banned: profileData.isBanned,
        verified: profileData.hasVerifiedBadge,
        avatar_url: userAvatar,
        url: `https://www.roblox.com/users/${user_id}/profile`,
        ...profileStats
      };

      cache.set(cacheKey, payload);
      setTimeout(() => cache.delete(cacheKey), 3600 * 1000);

      res.json(payload);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching Roblox user information.' });
    }
  }
};

const avatarhistoryController = {
  getUser: async (req, res) => {
    const { id, key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    if (!id) {
      return res.status(400).json({ error: '400', message: 'Parameter "id" is required' });
    }

    try {
      const response = await axios.get(`https://v1.evelina.bot/avatars/${id}`);

      const data = response.data;
      if (data.success === false) {
        return res.status(500).json({ error: '500', message: 'Error fetching the Pinterest URL' });
      }

      res.json(data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching the Pinterest URL' });
    }
  }
};

module.exports = {
  weatherController,
  cryptoController,
  stockController,
  googleController,
  minecraftController,
  spotifyController,
  githubController,
  discordController,
  robloxController,
  avatarhistoryController
};