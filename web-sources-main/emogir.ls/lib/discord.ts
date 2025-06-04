export async function connectDiscord(code: string) {
  try {
    const tokenResponse = await fetch("https://discord.com/api/oauth2/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: "1344236586564587580",
        client_secret: "Cprg2urZWfmGZCHeFzrCIaWxxUrx2Lx2",
        grant_type: "authorization_code",
        code,
        redirect_uri: `${process.env.NEXTAUTH_URL}/settings/discord/callback`,
      }),
    });

    const tokens = await tokenResponse.json();

    const userResponse = await fetch("https://discord.com/api/users/@me", {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    });

    const user = await userResponse.json();

    return { tokens, user };
  } catch (error) {
    console.error("Discord connection error:", error);
    throw error;
  }
}

type DiscordEmbed = {
  title?: string;
  description?: string;
  color?: number;
  fields?: { name: string; value: string; inline?: boolean }[];
  timestamp?: string;
};

export async function sendDiscordWebhook(
  webhookUrl: string,
  content: string,
  embeds?: DiscordEmbed[],
) {
  try {
    const response = await fetch(webhookUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        content,
        embeds,
      }),
    });

    if (!response.ok) {
      throw new Error(`Discord webhook failed: ${response.statusText}`);
    }
  } catch (error) {
    console.error("Discord webhook error:", error);
    throw error;
  }
}
