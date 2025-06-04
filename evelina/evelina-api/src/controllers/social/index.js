const axios = require('axios');
const cheerio = require('cheerio');
const { apiKeys } = require('../../config');

const instagramController = {
  getMedia: async (req, res) => {
    const { url: instagramUrl, key } = req.query;

    if (!instagramUrl) {
      return res.status(400).json({ error: '400', message: 'Parameter "url" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const modifiedUrl = instagramUrl.replace(/reels/g, 'reel');

      const response = await axios.get(`https://social-api4.p.rapidapi.com/v1/post_info?code_or_id_or_url=${modifiedUrl}`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });
      const data = response.data.data;
      const extractedData = {
        author: {
          id: data.user?.id || null,
          username: data.user?.username || null,
          display: data.user?.full_name || null,
          avatar: data.user?.profile_pic_url || null,
        },
        video: {
          video: data?.video_url || null,
          caption: data.caption?.text || null,
          likes: data.metrics?.like_count || 0,
          comments: data.metrics?.comment_count || 0,
          shares: data.metrics?.share_count || 0,
          views: data.metrics?.play_count || 0,
        },
      };

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching informations from the Instagram URL.' });
    }
  },

  getPost: async (req, res) => {
    const { url: instagramUrl, key } = req.query;

    if (!instagramUrl) {
      return res.status(400).json({ error: '400', message: 'Parameter "url" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://social-api4.p.rapidapi.com/v1/post_info?code_or_id_or_url=${instagramUrl}`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });

      const data = response.data.data;

      let mediaUrls = [];
      if (data.carousel_media) {
        mediaUrls = data.carousel_media.map(media => {
          if (media.media_type === 2 && media.video_url) {
            return media.video_url;
          } else if (media.media_type === 1 && media.image_versions) {
            return media.image_versions.items[0]?.url;
          }
          return null;
        }).filter(url => url !== null);
      } else if (data.image_versions && data.media_type === 1) {
        mediaUrls = [data.image_versions.items[0]?.url];
      } else if (data.video_url && data.media_type === 2) {
        mediaUrls = [data.video_url];
      }

      const extractedData = {
        author: {
          id: data.user?.id || null,
          username: data.user?.username || null,
          display: data.user?.full_name || null,
          avatar: data.user?.profile_pic_url || null,
        },
        media: {
          urls: mediaUrls,
          caption: data.caption?.text || null,
          likes: data.metrics?.like_count || 0,
          comments: data.metrics?.comment_count || 0,
          time: data.taken_at || 0,
        }
      };

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching informations from the Instagram URL.' });
    }
  },

  getPosts: async (req, res) => {
    const { username, key } = req.query;

    if (!username) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://social-api4.p.rapidapi.com/v1.2/posts?username_or_id_or_url=${username}`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });
      const data = response.data.data;

      const limitedItems = data.items.slice(0, 50);

      const formattedItems = limitedItems.map(item => {
        let media = [];

        if (item.carousel_media && item.carousel_media.length > 0) {
          media = item.carousel_media.map(mediaItem => ({
            type: mediaItem.media_type === 1 ? 'image' : 'video',
            url: mediaItem.image_versions?.items[0]?.url || null
          }));
        } else if (item.media_type === 1 && item.image_versions?.items[0]?.url) {
          media = [{
            type: 'image',
            url: item.image_versions.items[0].url
          }];
        }

        return {
          id: item.id || null,
          code: item.code || null,
          author: {
            id: data.user?.id || null,
            username: data.user?.username || null,
            display: data.user?.full_name || null,
            avatar: data.user?.profile_pic_url || null,
          },
          caption: item.caption?.text || null,
          media,
          likes: item.like_count || 0,
          comments: item.comment_count || 0,
          timestamp: item.taken_at || null
        };
      });

      res.json({
        count: formattedItems.length,
        items: formattedItems
      });
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching information from the Instagram username.' });
    }
  },

  getStory: async (req, res) => {
    const { username, key } = req.query;

    if (!username) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://social-api4.p.rapidapi.com/v1/stories?username_or_id_or_url=${username}`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi,
        },
      });

      const data = response.data.data;

      const user = data.additional_data.user || {};
      const fullName = user.full_name || null;
      const profilePicUrl = user.profile_pic_url || null;

      const stories = data.items || [];
      const storyUrls = stories.map(story => {
        if (story.media_type === 1) {
          return story.image_versions.items[0]?.url;
        } else if (story.media_type === 2) {
          return story.video_versions[0]?.url;
        }
        return null;
      }).filter(url => url);

      const storyTimes = stories.map(story => story.taken_at || null);

      const extractedData = {
        author: {
          username: username || null,
          display: fullName,
        },
        stories: {
          urls: storyUrls,
          times: storyTimes,
        },
      };

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching information from Instagram.' });
    }
  },

  getUser: async (req, res) => {
    const { username: instagramUsername, key } = req.query;

    if (!instagramUsername) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://social-api4.p.rapidapi.com/v1/info?username_or_id_or_url=${instagramUsername}`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });

      const data = response.data.data;
      const extractedData = {
        username: data?.username || null,
        full_name: data?.full_name || null,
        bio: data?.biography || null,
        profile_pic: data?.profile_pic_url_hd || null,
        followers: data?.follower_count || 0,
        following: data?.following_count || 0,
        posts: data?.media_count || 0,
        is_verified: data?.is_verified || false,
        is_private: data?.is_private || false,
      };

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching the Instagram Username' });
    }
  },

  getTimeline: async (req, res) => {
    const { username: instagramUsername, key } = req.query;

    if (!instagramUsername) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://social-api4.p.rapidapi.com/v1/posts?username_or_id_or_url=${username}&url_embed_safe=true`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });

      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching the Instagram Username' });
    }
  },

  getPostInfo: async (req, res) => {
    const { code, key } = req.query;

    if (!code) {
      return res.status(400).json({ error: '400', message: 'Parameter "code" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://social-api4.p.rapidapi.com/v1/post_info?code_or_id_or_url=${code}&include_insights=true`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });

      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching the Instagram Post' });
    }
  }
};

const tiktokController = {
  getMedia: async (req, res) => {
    const { url: tiktokUrl, key } = req.query;

    if (!tiktokUrl) {
      return res.status(400).json({ error: '400', message: 'Parameter "url" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://tikwm.com/api/?url=${tiktokUrl}`);

      const data = response.data.data;
      let extractedData;

      if (data.images && data.images.length > 0) {
        extractedData = {
          author: {
            id: data.author?.id || null,
            username: data.author?.unique_id || null,
            display: data.author?.nickname || null,
            avatar: data.author?.avatar || null,
          },
          images: data.images || [],
          music: data.music || null,
          caption: data.title || "No caption",
          likes: data.digg_count || 0,
          comments: data.comment_count || 0,
          shares: data.share_count || 0,
          views: data.play_count || 0,
        };
      } else {
        extractedData = {
          author: {
            id: data.author?.id || null,
            username: data.author?.unique_id || null,
            display: data.author?.nickname || null,
            avatar: data.author?.avatar || null,
          },
          video: data.play || null,
          music: data.music || null,
          caption: data.title || "No caption",
          likes: data.digg_count || 0,
          comments: data.comment_count || 0,
          shares: data.share_count || 0,
          views: data.play_count || 0,
        };
      }

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching information from the TikTok URL.' });
    }
  },

  getFYP: async (req, res) => {
    const { key } = req.query;

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const randomResponse = await axios.get('https://tiktok-random-video-generator.p.rapidapi.com/?minDuration=1&maxDuration=60', {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });

      const randomData = randomResponse.data.video;
      const { channelName, id } = randomData;

      const tiktokUrl = `https://www.tiktok.com/@${channelName}/video/${id}`;

      const response = await axios.get(`https://tikwm.com/api/?url=${tiktokUrl}`);

      const data = response.data.data;
      const extractedData = {
        author: {
          id: data.author?.id || null,
          username: data.author?.unique_id || null,
          display: data.author?.nickname || null,
          avatar: data.author?.avatar || null,
        },
        video: {
          video: data.play || null,
          caption: data.title || null,
          likes: data.digg_count || 0,
          comments: data.comment_count || 0,
          shares: data.share_count || 0,
          views: data.play_count || 0,
        },
      };

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching TikTok video information.' });
    }
  },

  getUser: async (req, res) => {
    const { username: tiktokUsername, key } = req.query;

    if (!tiktokUsername) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://tiktok-best-experience.p.rapidapi.com/user/${tiktokUsername}`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });

      const data = response.data.data;
      const extractedData = {
        username: data?.user.unique_id || null,
        full_name: data?.user.nickname || null,
        bio: data?.user.signature || null,
        profile_pic: data?.user?.avatar_larger?.url_list?.[0] || null,
        followers: data?.user.follower_count || 0,
        following: data?.user.following_count || 0,
        posts: data?.user.aweme_count || 0,
        hearts: data?.user.total_favorited || 0,
      };

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching informations from the TikTok Username.' });
    }
  },

  getTimeline: async (req, res) => {
    const { username: tiktokUsername, key } = req.query;

    if (!tiktokUsername) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://tiktok-best-experience.p.rapidapi.com/user/${username}/feed`, {	
        headers: {	
          'X-RapidAPI-Key': apiKeys.rapidApi	
        }	
      });

      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching informations from the TikTok Username.' });
    }
  }
};

const twitterController = {
  getMedia: async (req, res) => {
    const { url: twitterUrl, key } = req.query;

    if (!twitterUrl) {
      return res.status(400).json({ error: '400', message: 'Parameter "url" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://twitter-downloader-download-twitter-videos-gifs-and-images.p.rapidapi.com/tweetgrab?url=${twitterUrl}`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });
      const data = response.data;
      const truncateCaption = (caption) => {
        const httpsIndex = caption.indexOf('https');
        return httpsIndex === -1 ? caption : caption.substring(0, httpsIndex);
      };
      const extractedData = {
        author: {
          id: data?.user?.id || 0,
          username: data?.user?.screen_name || null,
          display: data?.user?.name || null,
          avatar: data?.user?.profile || null,
        },
        video: {
          video: data?.media?.video?.variants[3]?.src || null,
          caption: truncateCaption(data?.description || null),
          saves: data?.favorite_count || 0,
        }
      };

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching informations from the Twitter URL.' });
    }
  },

  getUser: async (req, res) => {
    const { username: twitterUsername, key } = req.query;

    if (!twitterUsername) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://twitter-api45.p.rapidapi.com/screenname.php?screenname=${twitterUsername}`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });

      const data = response.data;
      if (data.status === 'error') {
        return res.status(500).json({ error: '500', message: 'Error fetching the Twitter Username' });
      }

      const extractedData = {
        username: data.profile || null,
        full_name: data.name || null,
        bio: data.desc || null,
        profile_pic: data.avatar || null,
        followers: data.sub_count || 0,
        following: data.friends || 0,
        posts: data.statuses_count || 0,
        is_verified: data.blue_verified || false,
        created_at: data.created_at || null,
      };

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching the Twitter Username' });
    }
  },

  getTimeline: async (req, res) => {
    const { username: twitterUsername, key } = req.query;

    if (!twitterUsername) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://twitter-api45.p.rapidapi.com/timeline.php?screenname=${twitterUsername}`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });

      const data = response.data;
      if (data.status === 'error') {
        return res.status(500).json({ error: '500', message: 'Error fetching the Twitter Username' });
      }

      res.json(data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching the Twitter Username' });
    }
  }
};

const snapchatController = {
  getMedia: async (req, res) => {
    const { url: snapchatUrl, key } = req.query;

    if (!snapchatUrl) {
      return res.status(400).json({ error: '400', message: 'Parameter "url" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get('https://download-snapchat-video-spotlight-online.p.rapidapi.com/download', {
        params: { url: snapchatUrl },
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi,
        },
      });

      const data = response.data;
      const extractedData = {
        author: {
          username: data?.username || null,
        },
        video: {
          video: data?.story?.mediaUrl || null,
          caption: data?.title || null,
          views: data?.story?.viewCount || 0,
        },
      };

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching information from the Snapchat URL.' });
    }
  },

  getStory: async (req, res) => {
    const { username, key } = req.query;

    if (!username) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.post(`https://snapchat-story.p.rapidapi.com/?u=${username}`, {}, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi,
        }
      });

      const data = response.data;
      const storyEntries = data.story?.['0'] || [];
      const storyUrls = storyEntries.map(entry => entry.url);
      const storyTimes = storyEntries.map(entry => entry.time);

      const extractedData = {
        author: {
          username: username || null,
          display: data?.Name || null,
        },
        stories: {
          urls: storyUrls,
          times: storyTimes
        }
      };

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching information from the Snapchat Username.' });
    }
  },

  getUser: async (req, res) => {
    const { username, key } = req.query;

    if (!username) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const result = await axios.get(`https://story.snapchat.com/add/${username}`, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
      });

      const $ = cheerio.load(result.data);
      const data = $('#__NEXT_DATA__').html();
      const userProfile = JSON.parse(data).props.pageProps.userProfile;

      if (!userProfile) {
        return res.status(404).json({ error: '404', message: 'Account not found' });
      }

      let user;
      let display_name, snapcode, bio, avatar;
      
      if (userProfile.$case === 'publicProfileInfo') {
        user = userProfile.publicProfileInfo;
        display_name = user.title;
        snapcode = user.snapcodeImageUrl.replace("&type=SVG", "&type=PNG");
        bio = user.bio;
        avatar = user.profilePictureUrl;
      } else if (userProfile.$case === 'userInfo') {
        user = userProfile.userInfo;
        display_name = user.displayName;
        snapcode = user.snapcodeImageUrl.replace("&type=SVG", "&type=PNG");
        avatar = user.bitmoji3d.avatarImage.fallbackUrl;
        bio = null;
      }

      res.json({
        status: 'success',
        display_name: display_name,
        username: username,
        snapcode: snapcode,
        bio: bio,
        avatar: avatar,
        url: `https://story.snapchat.com/add/${username}`
      });
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching information from the Snapchat Username.' });
    }
  }
};

const onlyfansController = {
  getUser: async (req, res) => {
    const { username, key } = req.query;

    if (!username) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://coomer.su/api/v1/onlyfans/user/${username}`);

      const data = response.data;

      if (!Array.isArray(data)) {
        throw new Error('Unexpected response format');
      }

      const extractedData = data.map(entry => ({
        user: entry.user || null,
        content: entry.content || null,
        published: entry.published || null,
        image: entry.file?.path ? `https://img.coomer.su/thumbnail/data${entry.file.path}` : null
      }));

      res.json(extractedData);
    } catch (err) {
      res.status(500).json({ 
        error: '500', 
        message: 'Error fetching information from the OnlyFans API.',
        details: err.response ? err.response.data : err.message 
      });
    }
  }
};

const steamController = {
  getUser: async (req, res) => {
    const { id, key } = req.query;

    if (!id) {
      return res.status(400).json({ error: '400', message: 'Parameter "id" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=${apiKeys.steam}&steamids=${id}`);

      res.json(response.data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching Steam user information.' });
    }
  }
};

const youtubeController = {
  getChannel: async (req, res) => {
    const { username, key } = req.query;

    if (!username) {
      return res.status(400).json({ error: '400', message: 'Parameter "username" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://youtube-v2.p.rapidapi.com/channel/id?channel_name=${username}`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });

      const data = response.data;
      if (data.status === 'error') {
        return res.status(500).json({ error: '500', message: 'Error fetching the YouTube Username' });
      }

      res.json(data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching the YouTube Username' });
    }
  },

  getTimeline: async (req, res) => {
    const { id, key } = req.query;

    if (!id) {
      return res.status(400).json({ error: '400', message: 'Parameter "id" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://youtube-v2.p.rapidapi.com/channel/videos?channel_id=${id}`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });

      const data = response.data;
      if (data.status === 'error') {
        return res.status(500).json({ error: '500', message: 'Error fetching the YouTube Video' });
      }

      res.json(data);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error fetching the YouTube Video' });
    }
  }
}

const pinterestController = {
  getMedia: async (req, res) => {
    const { url: pinterestUrl, key } = req.query;

    if (!pinterestUrl) {
      return res.status(400).json({ error: '400', message: 'Parameter "url" is required' });
    }

    if (!key) {
      return res.status(400).json({ error: '400', message: 'Parameter "key" is required' });
    }

    try {
      const response = await axios.get(`https://pinterest-video-and-image-downloader.p.rapidapi.com/pinterest?url=${pinterestUrl}`, {
        headers: {
          'X-RapidAPI-Key': apiKeys.rapidApi
        }
      });

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
  instagramController,
  tiktokController,
  twitterController,
  snapchatController,
  onlyfansController,
  steamController,
  youtubeController,
  pinterestController
};