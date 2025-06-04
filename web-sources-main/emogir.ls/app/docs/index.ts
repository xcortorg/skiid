export const apiDocs = {
  openapi: "3.0.0",
  info: {
    title: "Emogir.ls API",
    version: "1.0.0",
    description: "API documentation for accessing your profile and links data",
  },
  servers: [
    {
      url: "https://emogir.ls/v1",
      description: "Production API",
    },
  ],
  security: [
    {
      bearerAuth: [],
    },
  ],
  paths: {
    "/{username}/profile": {
      get: {
        summary: "Get user profile",
        description: "Returns the specified user's profile information",
        parameters: [
          {
            name: "username",
            in: "path",
            required: true,
            description: "Username of the profile to retrieve",
            schema: {
              type: "string",
            },
          },
        ],
        examples: {
          curl: 'curl -X GET "https://emogir.ls/v1/johndoe/profile" -H "Authorization: Bearer YOUR_API_TOKEN"',
          javascript: `fetch('https://emogir.ls/v1/johndoe/profile', {
  headers: {
    'Authorization': 'Bearer YOUR_API_TOKEN'
  }
})`,
          python: `import requests

response = requests.get(
    'https://emogir.ls/v1/johndoe/profile',
    headers={'Authorization': 'Bearer YOUR_API_TOKEN'}
)`,
        },
        security: [{ bearerAuth: [] }],
        headers: {
          Authorization: {
            required: true,
            description: "Bearer {your-api-token}",
            example: "Bearer sk_live_abc123...",
          },
        },
        responses: {
          "200": {
            description: "Profile data retrieved successfully",
            content: {
              "application/json": {
                example: {
                  username: "johndoe",
                  name: "John Doe",
                  bio: "Software developer",
                  image: "https://example.com/avatar.jpg",
                  isPremium: true,
                  badges: ["PREMIUM", "VERIFIED"],
                },
              },
            },
          },
          "401": {
            description: "Invalid API key",
            content: {
              "application/json": {
                example: {
                  error: "Invalid API key",
                },
              },
            },
          },
          "429": {
            description: "Rate limit exceeded",
            content: {
              "application/json": {
                example: {
                  error: "Rate limit exceeded",
                  message: "Too many requests, please try again later",
                },
              },
            },
          },
        },
      },
    },
    "/{username}/links": {
      get: {
        summary: "Get user links",
        description: "Returns a paginated list of the specified user's links",
        parameters: [
          {
            name: "username",
            in: "path",
            required: true,
            description: "Username of the profile to retrieve links for",
            schema: {
              type: "string",
            },
          },
          {
            name: "limit",
            in: "query",
            description: "Number of links to return (max: 100)",
            schema: {
              type: "integer",
              default: 50,
              maximum: 100,
            },
          },
          {
            name: "offset",
            in: "query",
            description: "Number of links to skip",
            schema: {
              type: "integer",
              default: 0,
            },
          },
        ],
        examples: {
          curl: 'curl -X GET "https://emogir.ls/v1/johndoe/links?limit=50&offset=0" -H "Authorization: Bearer YOUR_API_TOKEN"',
          javascript: `fetch('https://emogir.ls/v1/johndoe/links?limit=50&offset=0', {
  headers: {
    'Authorization': 'Bearer YOUR_API_TOKEN'
  }
})`,
          python: `import requests

response = requests.get(
    'https://emogir.ls/v1/johndoe/links',
    headers={'Authorization': 'Bearer YOUR_API_TOKEN'},
    params={'limit': 50, 'offset': 0}
)`,
        },
        security: [{ bearerAuth: [] }],
        responses: {
          "200": {
            description: "Links retrieved successfully",
            content: {
              "application/json": {
                example: [
                  {
                    id: "link_123",
                    title: "My Website",
                    url: "https://example.com",
                    iconUrl: "https://example.com/icon.png",
                    enabled: true,
                    position: 0,
                    clicks: 42,
                  },
                ],
              },
            },
          },
        },
      },
    },
    "/{username}/links/{linkId}": {
      get: {
        summary: "Get specific link",
        description: "Returns details for a specific link",
        parameters: [
          {
            name: "username",
            in: "path",
            required: true,
            description: "Username of the profile to retrieve link from",
            schema: {
              type: "string",
            },
          },
          {
            name: "linkId",
            in: "path",
            required: true,
            description: "ID of the link to retrieve",
            schema: {
              type: "string",
            },
          },
        ],
        examples: {
          curl: 'curl -X GET "https://emogir.ls/v1/johndoe/links/link_123" -H "Authorization: Bearer YOUR_API_TOKEN"',
          javascript: `fetch('https://emogir.ls/v1/johndoe/links/link_123', {
  headers: {
    'Authorization': 'Bearer YOUR_API_TOKEN'
  }
})`,
          python: `import requests

response = requests.get(
    'https://emogir.ls/v1/johndoe/links/link_123',
    headers={'Authorization': 'Bearer YOUR_API_TOKEN'}
)`,
        },
        security: [{ bearerAuth: [] }],
        responses: {
          "200": {
            description: "Link retrieved successfully",
            content: {
              "application/json": {
                example: {
                  id: "link_123",
                  title: "My Website",
                  url: "https://example.com",
                  iconUrl: "https://example.com/icon.png",
                  enabled: true,
                  position: 0,
                  clicks: 42,
                },
              },
            },
          },
          "404": {
            description: "Link not found",
          },
          "401": {
            description: "Invalid API key",
          },
        },
      },
    },
    "/{username}/appearance": {
      get: {
        summary: "Get appearance settings",
        description: "Returns the specified user's appearance configuration",
        parameters: [
          {
            name: "username",
            in: "path",
            required: true,
            description: "Username of the profile to retrieve appearance for",
            schema: {
              type: "string",
            },
          },
        ],
        examples: {
          curl: 'curl -X GET "https://emogir.ls/v1/johndoe/appearance" -H "Authorization: Bearer YOUR_API_TOKEN"',
          javascript: `fetch('https://emogir.ls/v1/johndoe/appearance', {
  headers: {
    'Authorization': 'Bearer YOUR_API_TOKEN'
  }
})`,
          python: `import requests

response = requests.get(
    'https://emogir.ls/v1/johndoe/appearance',
    headers={'Authorization': 'Bearer YOUR_API_TOKEN'}
)`,
        },
        security: [{ bearerAuth: [] }],
        responses: {
          "200": {
            description: "Appearance settings retrieved successfully",
            content: {
              "application/json": {
                example: {
                  displayName: "John's Links",
                  bio: "Check out my links!",
                  avatar: "https://example.com/avatar.jpg",
                  banner: "https://example.com/banner.jpg",
                  backgroundUrl: "https://example.com/bg.jpg",
                  layoutStyle: "default",
                  containerBackgroundColor: "#000000",
                  glassEffect: true,
                  audioTracks: [
                    {
                      id: "track_1",
                      url: "https://example.com/song.mp3",
                      title: "My Song",
                      icon: "🎵",
                      order: 0,
                    },
                  ],
                },
              },
            },
          },
          "401": {
            description: "Invalid API key",
          },
        },
      },
    },
  },
  components: {
    securitySchemes: {
      bearerAuth: {
        type: "http",
        scheme: "bearer",
        bearerFormat: "JWT",
        description: "API token obtained from your dashboard",
      },
    },
  },
};
