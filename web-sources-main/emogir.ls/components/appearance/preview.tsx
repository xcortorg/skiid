import LayoutThree from "../../app/layouts/LayoutThree";

export function AppearancePreview({ state }: { state: any }) {
  return (
    <div className="w-[450px] sticky top-6 h-[calc(100vh-6rem)]">
      <div className="h-full rounded-lg border border-white/5 bg-black/20 backdrop-blur-sm overflow-hidden">
        <div className="p-3 border-b border-white/5 flex items-center justify-between">
          <span className="text-sm text-white/60">Preview</span>
          <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">
            Live
          </span>
        </div>
        <div className="h-[calc(100%-48px)] overflow-y-auto">
          <LayoutThree
            userData={{
              user: {
                id: "preview",
                name: state.profile.displayName || "Display Name",
                avatar: state.profile.avatar || "/default-avatar.png",
                banner: state.profile.banner,
                created_at: new Date().toISOString(),
              },
              badges: [],
              colors: {
                profile: {
                  type: "linear",
                  linear_color: state.theme.backgroundColor || "#000000",
                  gradient_colors: [],
                },
                elements: {
                  status: {
                    type: "linear",
                    color: state.theme.backgroundColor || "#000000",
                  },
                  bio: {
                    type: "linear",
                    color: state.text.bioColor || "#ffffff",
                  },
                },
              },
              presence: {
                status: "offline",
                activities: [],
              },
              discord_guild: {
                id: "123",
                name: "Test Server",
                icon: "https://cdn.discordapp.com/icons/123/123.png",
                presence_count: 100,
                member_count: 100,
                invite_url: state.discord.serverInvite || "",
              },
              bio: state.profile.bio || "Your bio goes here",
              background_url: state.container.backgroundUrl,
              glass_effect: state.container.glassEffect,
              audioPlayerEnabled: state.audio?.playerEnabled || false,
              audioTracks: (state.audio?.tracks || []).map((track: any) => ({
                url: track.url,
                title: track.title,
                icon: track.icon ?? undefined,
              })),
              click: {
                enabled: state.effects.clickEnabled,
                text: state.effects.clickText,
              },
              links: [],
              // @ts-ignore
              effects: {
                tiltDisabled: state.effects.tiltDisabled || false,
              },
              containerBackgroundColor:
                state.theme.backgroundColor || "#141010",
              containerBackdropBlur: state.container.backdropBlur || "8px",
              containerBorderColor: state.theme.borderColor || "#1a1a1a",
              containerBorderWidth: state.container.borderWidth || "1px",
              containerBorderRadius: state.container.borderRadius || "12px",
              containerGlowColor: state.theme.glowColor || "#ff3379",
              containerGlowIntensity: state.container.glowIntensity || "0.3",
              avatarSize: state.avatar.size || "96px",
              avatarBorderWidth: state.avatar.borderWidth || "2px",
              avatarBorderColor: state.avatar.borderColor || "#ff3379",
              avatarBorderRadius: state.avatar.borderRadius || "50%",
              avatarGlowColor: state.avatar.glowColor || "#ff3379",
              avatarGlowIntensity: state.avatar.glowIntensity || "0.3",
              titleColor: state.text.titleColor || "#ffffff",
              titleSize: state.text.titleSize || "24px",
              titleWeight: state.text.titleWeight || "600",
              usernameColor: state.text.usernameColor || "#999999",
              usernameSize: state.text.usernameSize || "16px",
              bioColor: state.text.bioColor || "#cccccc",
              bioSize: state.text.bioSize || "14px",
              linksBackgroundColor: state.links.backgroundColor || "#1a1a1a",
              linksHoverColor: state.links.hoverColor || "#2a2a2a",
              linksBorderColor: state.links.borderColor || "#333333",
              linksGap: state.links.gap || "8px",
              linksPrimaryTextColor: state.links.primaryTextColor || "#ffffff",
              linksSecondaryTextColor:
                state.links.secondaryTextColor || "#999999",
              linksHoverTextColor: state.links.hoverTextColor || "#ffffff",
              linksTextSize: state.links.textSize || "14px",
              linksIconSize: state.links.iconSize || "20px",
              linksIconColor: state.links.iconColor || "#ffffff",
              linksIconBgColor: state.links.iconBgColor || "#333333",
              linksIconBorderRadius: state.links.iconBorderRadius || "8px",
              font: state.typography?.font || "inter",
              fontSize: state.typography?.size || "md",
              fontWeight: state.typography?.weight || "normal",
              discordGuildBorderColor:
                state.discord.guildBorderColor || "#333333",
              discordGuildAvatarSize: state.discord.guildAvatarSize || "48px",
              discordGuildTitleColor:
                state.discord.guildTitleColor || "#ffffff",
              discordGuildButtonBgColor:
                state.discord.guildButtonBgColor || "#333333",
              discordGuildButtonHoverColor:
                state.discord.guildButtonHoverColor || "#444444",
              discordPresenceBgColor:
                state.discord.presenceBgColor || "#1a1a1a",
              discordPresenceBorderColor:
                state.discord.presenceBorderColor || "#333333",
              discordPresenceAvatarSize:
                state.discord.presenceAvatarSize || "32px",
              discordPresenceTextColor:
                state.discord.presenceTextColor || "#ffffff",
              discordPresenceSecondaryColor:
                state.discord.presenceSecondaryColor || "#999999",
              discordServerInvite: state.discord.serverInvite || "",
            }}
            discordData={null}
            slug="preview"
          />
        </div>
      </div>
    </div>
  );
}
