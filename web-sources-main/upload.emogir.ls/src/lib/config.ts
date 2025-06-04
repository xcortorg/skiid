export const config = {
    accountId: process.env.CF_ACCOUNT_ID!,
    accessKeyId: process.env.R2_ACCESS_KEY_ID!,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
    bucketName: process.env.R2_BUCKET_NAME!,
    authorizedUsers: {
      'user1': {
        apiKey: 'your-api-key-1',
        subdomain: 'kei.is-a-femboy.lol'
      },
      'user2': {
        apiKey: 'your-api-key-2',
        subdomain: 'adam.emogir.ls'
      }
    }
  };