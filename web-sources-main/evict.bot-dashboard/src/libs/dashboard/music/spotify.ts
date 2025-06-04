import SpotifyWebApi from 'spotify-web-api-node';

export async function getSpotifyTrackId(artist: string, title: string) {
  const spotify = new SpotifyWebApi({
    clientId: process.env.AUTH_SPOTIFY_ID,
    clientSecret: process.env.AUTH_SPOTIFY_SECRET
  });

  const auth = await spotify.clientCredentialsGrant();
  spotify.setAccessToken(auth.body.access_token);

  try {
    const searchResult = await spotify.searchTracks(`track:${title} artist:${artist}`, {
      limit: 1
    });

    if (searchResult.body.tracks?.items.length) {
      return searchResult.body.tracks.items[0].id;
    }
    
    return null;
  } catch (error) {
    console.error('Failed to get Spotify track ID:', error);
    return null;
  }
} 