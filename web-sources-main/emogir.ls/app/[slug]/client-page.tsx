"use client";

import { useState, use, useEffect } from "react";
import LayoutOne from "../layouts/LayoutOne";
import LayoutTwo from "../layouts/LayoutTwo";
import LayoutThree from "../layouts/LayoutThree";
import LayoutConsole from "../layouts/LayoutConsole";
import LayoutFemboy from "../layouts/LayoutFemboy";
import {
  DiscordData,
  LayoutConsoleProps,
  LayoutFemboyProps,
  LayoutThreeProps,
  LayoutOneProps,
  LayoutTwoProps,
  UserData,
} from "@/types/slugs";
import { notFound } from "next/navigation";
import Turnstile from "react-turnstile";
import { Input } from "@/components/ui/input";
import { AlertTriangle } from "lucide-react";

interface ExtendedUserData {
  user: {
    id: string;
    name: string;
    avatar: string;
    banner: string | null;
    created_at: string;
  };
  colors: {
    profile: {
      type: "linear" | "gradient";
      linear_color: string;
      gradient_colors: any[];
    };
    elements: {
      status: { type: "linear"; color: string };
      bio: { type: "linear"; color: string };
    };
  };
  presence: {
    status: string;
    activities: any[];
  };
  background_url: string | null;
  glass_effect: boolean;
  bio: string;
  links: {
    type: string;
    url: string;
  }[];
  click: {
    enabled: boolean;
    text: string;
  };
  onboarding: boolean;
}

enum LayoutType {
  One = 1,
  Two = 2,
  Three = 3,
  Console = 4,
  Femboy = 5,
}

const transformUserDataForLayout = (
  data: any,
  discordData: DiscordData | null,
  layoutType: LayoutType,
) => {
  const baseUserData: UserData = {
    username: data?.username || "",
    displayName: data?.displayName || "",
    bio: data?.bio || "",
    avatar: data?.avatar || "",
    links: (data?.links || []).map((link: any) => ({
      id: link.id || "",
      title: link.type || "",
      url: link.url || "",
      enabled: link.enabled || false,
      clicks: 0,
      position: 0,
      iconUrl: `https://r.emogir.ls/assets/icons/svg/${(
        link.type || "default"
      ).toLowerCase()}.svg`,
      backgroundColor: data.appearance?.linksBackgroundColor,
      hoverColor: data.appearance?.linksHoverColor,
      borderColor: data.appearance?.linksBorderColor,
      gap: data.appearance?.linksGap,
      primaryTextColor: data.appearance?.linksPrimaryTextColor,
      secondaryTextColor: data.appearance?.linksSecondaryTextColor,
      hoverTextColor: data.appearance?.linksHoverTextColor,
      textSize: data.appearance?.linksTextSize,
      iconSize: data.appearance?.linksIconSize,
      iconColor: data.appearance?.linksIconColor,
      iconBgColor: data.appearance?.linksIconBgColor,
      iconBorderRadius: data.appearance?.linksIconBorderRadius,
    })),
  };

  switch (layoutType) {
    case LayoutType.Console:
      return {
        ...baseUserData,
        location: data?.location,
        timezone: data?.timezone,
        languages: data?.languages || [],
        skills: data?.skills || [],
        projects: data?.projects || [],
      } as LayoutConsoleProps["userData"];

    case LayoutType.Three:
      return {
        user: {
          id: data?.id || "",
          name: data.user.name || "",
          avatar: data?.avatar || null,
          banner: data?.banner || null,
          created_at: data?.createdAt || new Date().toISOString(),
        },
        badges: data.badges || [],
        colors: {
          profile: {
            type: "linear",
            linear_color: data?.appearance?.themeAccentColor || "#000000",
            gradient_colors: [],
          },
          elements: {
            status: {
              type: "linear",
              color: data?.appearance?.themeAccentColor || "#000000",
            },
            bio: {
              type: "linear",
              color: data?.appearance?.bioColor || "#ffffff",
            },
          },
        },
        presence: {
          status: data?.presence?.status || "offline",
          activities: data?.presence?.activities || [],
        },
        discord_guild: {
          invite_url: data?.appearance?.discordServerInvite,
        },
        bio: data?.bio || "",
        background_url: data?.appearance?.backgroundUrl || null,
        glass_effect: data?.appearance?.glassEffect || false,
        audioPlayerEnabled: data?.appearance?.audioPlayerEnabled || false,
        audioTracks: data?.appearance?.audioTracks || [],
        click: {
          enabled: data?.appearance?.clickEffectEnabled || false,
          text: data?.appearance?.clickEffectText || "click",
        },
        links:
          data.links?.map((link: any) => ({
            type: link.title,
            url: link.url,
            enabled: link.enabled,
          })) || [],
        theme: {
          effects: {
            tiltDisabled: data?.appearance?.tiltDisabled || false,
          },
          containerBackgroundColor:
            data?.appearance?.containerBackgroundColor || "#141010",
          containerBackdropBlur:
            data?.appearance?.containerBackdropBlur || "8px",
          containerBorderColor:
            data?.appearance?.containerBorderColor || "#1a1a1a",
          containerBorderWidth: data?.appearance?.containerBorderWidth || "1px",
          containerBorderRadius:
            data?.appearance?.containerBorderRadius || "12px",
          containerGlowColor: data?.appearance?.containerGlowColor || "#ff3379",
          containerGlowIntensity:
            data?.appearance?.containerGlowIntensity || "0.3",
          avatarSize: data?.appearance?.avatarSize || "96px",
          avatarBorderWidth: data?.appearance?.avatarBorderWidth || "2px",
          avatarBorderColor: data?.appearance?.avatarBorderColor || "#ff3379",
          avatarBorderRadius: data?.appearance?.avatarBorderRadius || "50%",
          avatarGlowColor: data?.appearance?.avatarGlowColor || "#ff3379",
          avatarGlowIntensity: data?.appearance?.avatarGlowIntensity || "0.3",
          titleColor: data?.appearance?.titleColor || "#ffffff",
          titleSize: data?.appearance?.titleSize || "24px",
          titleWeight: data?.appearance?.titleWeight || "600",
          usernameColor: data?.appearance?.usernameColor || "#999999",
          usernameSize: data?.appearance?.usernameSize || "16px",
          bioColor: data?.appearance?.bioColor || "#cccccc",
          bioSize: data?.appearance?.bioSize || "14px",
          linksBackgroundColor:
            data?.appearance?.linksBackgroundColor || "#1a1a1a",
          linksHoverColor: data?.appearance?.linksHoverColor || "#2a2a2a",
          linksBorderColor: data?.appearance?.linksBorderColor || "#333333",
          linksGap: data?.appearance?.linksGap || "8px",
          linksPrimaryTextColor:
            data?.appearance?.linksPrimaryTextColor || "#ffffff",
          linksSecondaryTextColor:
            data?.appearance?.linksSecondaryTextColor || "#999999",
          linksHoverTextColor:
            data?.appearance?.linksHoverTextColor || "#ffffff",
          linksTextSize: data?.appearance?.linksTextSize || "14px",
          linksIconSize: data?.appearance?.linksIconSize || "20px",
          linksIconColor: data?.appearance?.linksIconColor || "#ffffff",
          linksIconBgColor: data?.appearance?.linksIconBgColor || "#333333",
          linksIconBorderRadius:
            data?.appearance?.linksIconBorderRadius || "8px",
          font: data?.appearance?.font || "inter",
          fontSize: data?.appearance?.fontSize || "md",
          fontWeight: data?.appearance?.fontWeight || "normal",
          discordPresenceBgColor:
            data?.appearance?.discordPresenceBgColor || "#1a1a1a",
          discordPresenceBorderColor:
            data?.appearance?.discordPresenceBorderColor || "#333333",
          discordPresenceAvatarSize:
            data?.appearance?.discordPresenceAvatarSize || "32px",
          discordPresenceTextColor:
            data?.appearance?.discordPresenceTextColor || "#ffffff",
          discordPresenceSecondaryColor:
            data?.appearance?.discordPresenceSecondaryColor || "#999999",
          discordGuildBgColor:
            data?.appearance?.discordGuildBgColor || "#1a1a1a",
          discordGuildBorderColor:
            data?.appearance?.discordGuildBorderColor || "#333333",
          discordGuildAvatarSize:
            data?.appearance?.discordGuildAvatarSize || "48px",
          discordGuildTitleColor:
            data?.appearance?.discordGuildTitleColor || "#ffffff",
          discordGuildButtonBgColor:
            data?.appearance?.discordGuildButtonBgColor || "#333333",
          discordGuildButtonHoverColor:
            data?.appearance?.discordGuildButtonHoverColor || "#444444",
          discordServerInvite: data?.appearance?.discordServerInvite || "",
        },
      } as LayoutThreeProps["userData"];

    case LayoutType.Two:
    case LayoutType.One:
    case LayoutType.Femboy:
      return {
        ...baseUserData,
        username: data.user?.name || data.username || "",
        displayName: data.displayName || data.user?.name || "",
        presence: {
          status: data?.presence?.status || "offline",
          activities: data?.presence?.activities || [],
        },
        badges: data.badges || [],
      };

    default:
      return baseUserData;
  }
};

export default function ClientPage({ slug }: { slug: string }) {
  const [userData, setUserData] = useState<any>(null);
  const [discordData, setDiscordData] = useState<DiscordData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isPinProtected, setIsPinProtected] = useState(false);
  const [pin, setPin] = useState("");
  const [pinError, setPinError] = useState("");
  const [accountStatus, setAccountStatus] = useState<string | null>(null);

  const fetchData = async (pinCode?: string) => {
    try {
      const sanitizedSlug = decodeURIComponent(slug).replace(/^@/, "");
      const url = new URL(
        `/api/profile/${sanitizedSlug}`,
        window.location.origin,
      );
      if (pinCode) {
        url.searchParams.set("pin", pinCode);
      }

      const response = await fetch(url);

      if (response.status === 403) {
        const data = await response.json();
        
        if (data.status && ["BANNED", "DISABLED", "RESTRICTED"].includes(data.status)) {
          setAccountStatus(data.status);
          setLoading(false);
          return;
        }
        
        if (data.pinProtected) {
          setIsPinProtected(true);
          if (pinCode) {
            setPinError("Invalid PIN");
            setPin("");
          }
          setLoading(false);
          return;
        }
      }

      if (!response.ok) {
        throw new Error("Failed to fetch user");
      }

      const data = await response.json();
      setUserData(data);
      setIsPinProtected(false);

      const discordResponse = await fetch(`/api/account/discord/${data.id}`);
      if (discordResponse.ok) {
        const discordData = await discordResponse.json();
        if (discordData?.id) {
          const detailedDiscordResponse = await fetch(`/api/discord/user/${discordData.id}`);
          if (detailedDiscordResponse.ok) {
            const detailedData = await detailedDiscordResponse.json();
            setDiscordData({
              ...discordData,
              detailed: detailedData.data
            });
          }

          console.log("Attempting WebSocket connection...");
          const ws = new WebSocket(
            `wss://logs.emogir.ls/presence?userId=${discordData.id}`,
          );

          ws.onopen = () => {
            console.log("WebSocket Connected Successfully");
          };

          ws.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data);

              const transformedActivities =
                data.activities?.map((activity: any) => {
                  if (activity.name === "Spotify") {
                    const isLocalFile = !activity.track_id;
                    return {
                      ...activity,
                      type: "ActivityType.listening",
                      name: "Spotify",
                      details:
                        activity.track_title ||
                        activity.details ||
                        "Unknown Track",
                      state:
                        activity.track_artist ||
                        activity.state ||
                        "Unknown Artist",
                      large_image: activity.album_cover_url || null,
                      small_image: "spotify:icon",
                      large_text: activity.track_album || "Spotify",
                      small_text: "Spotify",
                      timestamps: activity.timestamps || {
                        start: Date.now(),
                        end: null,
                      },
                      album: activity.track_album || "Unknown Album",
                      assets: {
                        ...activity.assets,
                        large_image: activity.album_cover_url || "spotify:icon",
                        small_image: "spotify:icon",
                      },
                      isLocalFile,
                    };
                  }

                  return {
                    ...activity,
                    large_image: activity.assets?.large_image,
                    small_image: activity.assets?.small_image,
                    large_text: activity.assets?.large_text,
                    small_text: activity.assets?.small_text,
                  };
                }) || [];

              setUserData((prev: any) => ({
                ...prev,
                presence: {
                  status: data.status,
                  activities: transformedActivities,
                },
              }));
            } catch (error) {
              console.error("Error parsing WebSocket message:", error);
            }
          };

          ws.onerror = (error) => {
            console.error("WebSocket Error:", error);
          };

          ws.onclose = (event) => {
            console.log(
              "WebSocket Disconnected - Code:",
              event.code,
              "Reason:",
              event.reason,
            );
          };

          return () => {
            console.log("Cleaning up WebSocket connection...");
            if (ws.readyState === WebSocket.OPEN) {
              ws.close();
            }
          };
        }
      }
    } catch (error) {
      console.error("Error:", error);
      notFound();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [slug]);

  const handlePinSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPinError("");

    if (!pin || pin.length !== 6) {
      setPinError("PIN must be 6 digits");
      return;
    }

    setLoading(true);
    await fetchData(pin);
  };

  const handleTurnstileSuccess = async (token: string) => {
    try {
      const response = await fetch("/api/views", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          slug,
          token,
        }),
      });

      const data = await response.json();
      console.log("API response:", data);

      if (!response.ok) {
        throw new Error(data.error || "Failed to record view");
      }

      return data;
    } catch (error) {
      console.error("Error recording view:", error);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-black/90">
        <div className="relative flex flex-col items-center gap-4">
          <div className="w-16 h-16 rounded-full border-4 border-white/10 border-t-white/90 animate-spin" />
          <div className="text-white/60 text-sm font-medium animate-pulse">
            Loading profile...
          </div>
        </div>
      </div>
    );
  }

  if (accountStatus) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-black/90">
        <div className="w-full max-w-md p-6 bg-white/[0.02] rounded-xl border border-white/5 text-center">
          <div className="flex justify-center mb-4">
            <AlertTriangle className="h-12 w-12 text-red-500" />
          </div>
          <h2 className="text-xl font-medium text-white/90 mb-2">
            Account Suspended
          </h2>
          <p className="text-white/60 mb-4">
            {accountStatus === "BANNED" 
              ? "This account has been banned for violating our terms of service."
              : accountStatus === "RESTRICTED"
              ? "This account has been restricted and is currently under review."
              : "This account has been temporarily disabled."}
          </p>
          <div className="pt-2 border-t border-white/10">
            <p className="text-sm text-white/40">
              If you believe this is an error, please contact support.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (isPinProtected) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-black/90">
        <div className="w-full max-w-md p-6 bg-white/[0.02] rounded-xl border border-white/5">
          <form onSubmit={handlePinSubmit} className="space-y-4">
            <div className="text-center">
              <h2 className="text-xl font-medium text-white/90">
                PIN Protected Profile
              </h2>
              <p className="mt-2 text-sm text-white/60">
                Enter the 6-digit PIN to view this profile
              </p>
            </div>

            <div className="space-y-2">
              <Input
                type="password"
                maxLength={6}
                placeholder="Enter PIN"
                value={pin}
                onChange={(e) => {
                  const value = e.target.value.replace(/\D/g, "").slice(0, 6);
                  setPin(value);
                  setPinError("");
                }}
                className="bg-white/5 border-white/10 text-center text-xl tracking-widest"
              />
              {pinError && (
                <p className="text-sm text-red-500 text-center">{pinError}</p>
              )}
            </div>

            <button
              type="submit"
              className="w-full py-2 px-4 bg-white/10 hover:bg-white/20 
                       text-white/90 rounded-lg transition-colors duration-200"
            >
              Submit
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (!userData) {
    notFound();
  }

  const layoutType = getLayoutType(
    userData?.appearance?.layoutStyle || "three",
  );
  const transformedData = transformUserDataForLayout(
    userData,
    discordData,
    layoutType,
  );

  return (
    <div>
      <Turnstile
        sitekey="0x4AAAAAABBcyUXhbkKp7YBX"
        onVerify={handleTurnstileSuccess}
        theme="light"
        size="invisible"
        execution="render"
        refreshExpired="manual"
      />
      {layoutType === LayoutType.Console && (
        <LayoutConsole
          userData={transformedData as LayoutConsoleProps["userData"]}
          discordData={discordData}
          slug={slug}
          theme={userData?.appearance}
        />
      )}
      {layoutType === LayoutType.Femboy && (
        <LayoutFemboy
          userData={transformedData as LayoutFemboyProps["userData"]}
          discordData={discordData}
          theme={userData?.appearance}
        />
      )}
      {layoutType === LayoutType.Three && (
        <LayoutThree
          // @ts-ignore
          userData={transformedData as LayoutThreeProps["userData"]}
          discordData={discordData}
          slug={slug}
          theme={userData?.appearance}
        />
      )}
      {layoutType === LayoutType.Two && (
        <LayoutTwo
          userData={transformedData as LayoutTwoProps["userData"]}
          discordData={discordData}
          slug={slug}
          theme={userData?.appearance}
        />
      )}
      {layoutType === LayoutType.One && (
        <LayoutOne
          userData={transformedData as LayoutOneProps["userData"]}
          discordData={discordData}
          slug={slug}
          theme={userData?.appearance}
        />
      )}
    </div>
  );
}

function getLayoutType(style?: string): LayoutType {
  if (!style) return LayoutType.Three;

  switch (style.toLowerCase()) {
    case "console":
      return LayoutType.Console;
    case "femboy":
      return LayoutType.Femboy;
    case "three":
      return LayoutType.Three;
    case "two":
      return LayoutType.Two;
    case "one":
      return LayoutType.One;
    default:
      return LayoutType.Three;
  }
}
