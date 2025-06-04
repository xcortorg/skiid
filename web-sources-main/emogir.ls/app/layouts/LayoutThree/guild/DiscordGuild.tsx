import Image from "next/image";
import { motion } from "framer-motion";

const safeColor = (color: string | undefined, defaultColor: string): string => {
  if (!color) return defaultColor;
  return color;
};

export interface GuildData {
  id?: string;
  name?: string;
  icon?: string;
  description?: string;
  presence_count?: number;
  member_count?: number;
  invite_url: string;
}

interface DiscordGuildProps {
  guildData: GuildData;
  theme: {
    discordGuildBgColor?: string;
    discordGuildBorderColor?: string;
    discordGuildAvatarSize?: string;
    discordGuildTitleColor?: string;
    discordGuildButtonBgColor?: string;
    discordGuildButtonHoverColor?: string;
    discordAnimationsEnabled?: boolean;
    discord?: {
      guild?: {
        title?: {
          color?: string;
          size?: string;
          weight?: string;
        };
        description?: {
          color?: string;
        };
        stats?: {
          color?: string;
          dotColor?: {
            online?: string;
            offline?: string;
          };
        };
      };
    };
    [key: string]: any;
  };
}

export const DiscordGuild = ({ guildData, theme }: DiscordGuildProps) => (
  <motion.div
    initial={theme.discordAnimationsEnabled ? { opacity: 0, y: 20 } : false}
    animate={theme.discordAnimationsEnabled ? { opacity: 1, y: 0 } : false}
    className="mb-6 p-3 sm:p-4 rounded-xl border"
    style={{
      backgroundColor: safeColor(theme?.discordGuildBgColor, "#1a1a1a"),
      borderColor: safeColor(theme?.discordGuildBorderColor, "#333333"),
    }}
  >
    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4">
      {guildData.icon && (
        <Image
          unoptimized
          src={`https://cdn.discordapp.com/icons/${guildData.id}/${guildData.icon}.png?size=96`}
          alt={guildData.name || ""}
          width={48}
          height={48}
          style={{
            width: theme?.discordGuildAvatarSize || "48px",
            height: theme?.discordGuildAvatarSize || "48px",
            borderRadius: "0.75rem",
          }}
          className="mx-auto sm:mx-0"
        />
      )}
      <div className="flex-1 min-w-0 text-center sm:text-left">
        <div className="flex items-center justify-center sm:justify-start gap-2 flex-wrap">
          <h3
            style={{
              color: safeColor(
                theme?.discordGuildTitleColor ||
                  theme?.discord?.guild?.title?.color,
                "white",
              ),
              fontSize: theme?.discord?.guild?.title?.size || "1rem",
              fontWeight: theme?.discord?.guild?.title?.weight || "500",
            }}
            className="truncate"
          >
            {guildData.name || ""}
          </h3>
          <div
            className="px-2 py-0.5 rounded text-xs"
            style={{
              backgroundColor: "rgba(88, 101, 242, 0.1)",
              color: "#5865F2",
            }}
          >
            Discord Server
          </div>
        </div>
        {guildData.description && (
          <p
            className="text-sm mt-1 line-clamp-2"
            style={{
              color: safeColor(
                theme?.discord?.guild?.description?.color,
                "rgba(255, 255, 255, 0.6)",
              ),
            }}
          >
            {guildData.description}
          </p>
        )}
        <div
          className="flex gap-4 mt-2 text-sm justify-center sm:justify-start flex-wrap"
          style={{
            color: safeColor(
              theme?.discord?.guild?.stats?.color,
              "rgba(255, 255, 255, 0.6)",
            ),
          }}
        >
          <div className="flex items-center gap-1">
            <div
              className="w-2 h-2 rounded-full"
              style={{
                backgroundColor: safeColor(
                  theme?.discord?.guild?.stats?.dotColor?.online,
                  "#22c55e",
                ),
              }}
            />
            {guildData.presence_count?.toLocaleString() || "0"} online
          </div>
          <div className="flex items-center gap-1">
            <div
              className="w-2 h-2 rounded-full"
              style={{
                backgroundColor: safeColor(
                  theme?.discord?.guild?.stats?.dotColor?.offline,
                  "rgba(255, 255, 255, 0.3)",
                ),
              }}
            />
            {guildData.member_count?.toLocaleString() || "0"} members
          </div>
        </div>
      </div>
      <a
        href={guildData.invite_url}
        target="_blank"
        rel="noopener noreferrer"
        className="w-full sm:w-auto px-4 py-2 transition-colors rounded-lg text-sm font-medium text-center mt-3 sm:mt-0"
        style={{
          backgroundColor: safeColor(
            theme?.discordGuildButtonBgColor,
            "#5865F2",
          ),
          color: "#ffffff",
        }}
        onMouseOver={(e) => {
          e.currentTarget.style.backgroundColor = safeColor(
            theme?.discordGuildButtonHoverColor,
            "#4752C4",
          );
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = safeColor(
            theme?.discordGuildButtonBgColor,
            "#5865F2",
          );
        }}
      >
        Join
      </a>
    </div>
  </motion.div>
);
