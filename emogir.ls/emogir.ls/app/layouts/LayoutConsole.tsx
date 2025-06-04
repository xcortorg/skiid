"use client";

import { motion } from "framer-motion";
import React, { useState, useEffect, useRef } from "react";
import { DiscordData } from "@/app/types/discord";
import { Resizable } from "re-resizable";

interface ConsoleTheme {
  container?: {
    backgroundColor?: string;
    textColor?: string;
    fontFamily?: string;
    cursorColor?: string;
    borderColor?: string;
    glassEffect?: boolean;
    blur?: string;
  };
  header?: {
    show?: boolean;
    title?: string;
    controls?: {
      show?: boolean;
      color1?: string;
      color2?: string;
      color3?: string;
    };
    borderColor?: string;
  };
  prompt?: {
    user?: string;
    symbol?: string;
    userColor?: string;
    pathColor?: string;
    symbolColor?: string;
  };
  cursor?: {
    style?: "block" | "line" | "underscore";
    blinkSpeed?: "slow" | "normal" | "fast";
    color?: string;
  };
  text?: {
    commands?: {
      color?: string;
      prefix?: string;
    };
    success?: {
      color?: string;
      prefix?: string;
    };
    error?: {
      color?: string;
      prefix?: string;
    };
    info?: {
      color?: string;
      prefix?: string;
    };
    links?: {
      color?: string;
      hoverColor?: string;
    };
  };
  animation?: {
    typingSpeed?: number;
    initialDelay?: number;
    lineDelay?: number;
    enabled?: boolean;
  };
  window?: {
    title?: string;
    titleAlignment?: "left" | "center" | "right";
    resizable?: boolean;
    minWidth?: number;
    minHeight?: number;
    defaultSize?: { width: number; height: number };
  };
  statusBar?: {
    show?: boolean;
    height?: number;
    backgroundColor?: string;
    textColor?: string;
    items?: {
      time?: boolean;
      systemInfo?: boolean;
      customText?: string;
    };
  };
  lineNumbers?: {
    show?: boolean;
    color?: string;
    backgroundColor?: string;
    width?: number;
  };
  tabs?: {
    show?: boolean;
    items?: string[];
    activeTab?: number;
    backgroundColor?: string;
    activeColor?: string;
    textColor?: string;
  };
}

interface LayoutConsoleProps {
  userData: {
    username: string;
    displayName: string;
    bio: string;
    avatar: string;
    links: {
      id: number;
      title: string;
      url: string;
      iconUrl: string;
      clicks: number;
    }[];
    location?: string;
    timezone?: string;
    languages?: string[];
    skills?: string[];
    projects?: {
      name: string;
      description: string;
      url?: string;
    }[];
  };
  discordData: DiscordData | null;
  slug: string;
  theme?: ConsoleTheme;
}

type Commands = {
  [key: string]: {
    description: string;
    execute: () => (string | null)[];
  };
};

export default function LayoutConsole({
  userData,
  discordData,
  theme,
}: LayoutConsoleProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const [visibleLines, setVisibleLines] = useState<string[]>([]);
  const [currentLine, setCurrentLine] = useState(0);
  const [input, setInput] = useState("");
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [showSystemInfo, setShowSystemInfo] = useState(false);
  const [activeTab, setActiveTab] = useState(theme?.tabs?.activeTab || 0);
  const [windowSize, setWindowSize] = useState({
    width: theme?.window?.defaultSize?.width || 800,
    height: theme?.window?.defaultSize?.height || 500,
  });

  const commands: Commands = {
    help: {
      description: "Show available commands",
      execute: () => [
        "Available commands:",
        "  help        - Show this help message",
        "  clear       - Clear the terminal",
        "  about       - Show user information",
        "  links       - Show all links",
        "  projects    - Show user projects",
        "  skills      - Show user skills",
        "  stats       - Show profile statistics",
        "  system      - Show system information",
        "  discord     - Show Discord presence",
        "  contact     - Show contact information",
        "  time        - Show current time",
        "  banner      - Show ASCII art banner",
      ],
    },
    clear: {
      description: "Clear the terminal",
      execute: () => {
        setVisibleLines([]);
        return [];
      },
    },
    about: {
      description: "Show user information",
      execute: () =>
        [
          `Name: ${userData.displayName}`,
          `Username: @${userData.username}`,
          `Bio: ${userData.bio}`,
          userData.location ? `Location: ${userData.location}` : null,
          userData.timezone ? `Timezone: ${userData.timezone}` : null,
          userData.languages
            ? `Languages: ${userData.languages.join(", ")}`
            : null,
        ].filter(Boolean),
    },
    links: {
      description: "Show all links",
      execute: () => [
        "Links:",
        ...userData.links.map(
          (link) =>
            `  ${link.title.padEnd(10)} - ${link.url} (${link.clicks} clicks)`,
        ),
      ],
    },
    projects: {
      description: "Show user projects",
      execute: () =>
        userData.projects
          ? [
              "Projects:",
              ...userData.projects
                .map((project) => [
                  `  ${project.name}`,
                  `    ${project.description}`,
                  project.url ? `    URL: ${project.url}` : null,
                ])
                .flat()
                .filter(Boolean),
            ]
          : ["No projects found."],
    },
    skills: {
      description: "Show user skills",
      execute: () =>
        userData.skills
          ? ["Skills:", ...userData.skills.map((skill) => `  - ${skill}`)]
          : ["No skills listed."],
    },
    stats: {
      description: "Show profile statistics",
      execute: () => [
        "Profile Statistics:",
        `Total Links: ${userData.links.length}`,
        `Total Clicks: ${userData.links.reduce(
          (acc, link) => acc + link.clicks,
          0,
        )}`,
        `Average Clicks: ${Math.round(
          userData.links.reduce((acc, link) => acc + link.clicks, 0) /
            userData.links.length,
        )}`,
      ],
    },
    system: {
      description: "Show system information",
      execute: () => [
        "System Information:",
        `OS: Terminal v1.0.0`,
        `Browser: ${navigator.userAgent}`,
        `Resolution: ${window.innerWidth}x${window.innerHeight}`,
        `Time: ${new Date().toLocaleString()}`,
      ],
    },
    discord: {
      description: "Show Discord presence",
      execute: () => {
        if (!discordData?.presence) return ["Discord presence not available."];
        const activity = discordData.presence.activities?.[0];
        return [
          "Discord Presence:",
          `Status: ${discordData.presence.user.status}`,
          activity
            ? [
                `Activity: ${activity.name}`,
                activity.details ? `Details: ${activity.details}` : null,
                activity.state ? `State: ${activity.state}` : null,
              ].filter(Boolean)
            : [],
        ].flat();
      },
    },
    contact: {
      description: "Show contact information",
      execute: () => [
        "Contact Information:",
        `Name: ${userData.displayName}`,
        `Username: @${userData.username}`,
        ...userData.links
          .filter((link) =>
            ["twitter", "email", "discord"].includes(link.title.toLowerCase()),
          )
          .map((link) => `${link.title}: ${link.url}`),
      ],
    },
    time: {
      description: "Show current time",
      execute: () => [
        `Current Time: ${new Date().toLocaleString()}`,
        `Timezone: ${
          userData.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone
        }`,
      ],
    },
    banner: {
      description: "Show ASCII art banner",
      execute: () => [
        "╔════════════════════════════════════╗",
        `║            ${userData.displayName.padEnd(20)}║`,
        "║                                    ║",
        `║            @${userData.username.padEnd(19)}║`,
        "╚════════════════════════════════════╝",
      ],
    },
  };

  const initialLines = [
    `Terminal v1.0.0 (${new Date().toLocaleString()})`,
    "© 2024 Profile Console. All rights reserved.",
    "",
    `Welcome, ${userData.displayName}!`,
    'Type "help" for available commands.',
    "",
  ];

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [visibleLines]);

  useEffect(() => {
    if (theme?.animation?.enabled === false) {
      setVisibleLines(initialLines);
      return;
    }

    setVisibleLines([]);
    let mounted = true;

    const typeNextLine = (index: number) => {
      if (!mounted || index >= initialLines.length) return;

      setTimeout(() => {
        setVisibleLines((prev) => [...prev, initialLines[index]]);
        typeNextLine(index + 1);
      }, theme?.animation?.lineDelay || 500);
    };

    setTimeout(() => {
      typeNextLine(0);
    }, theme?.animation?.initialDelay || 1000);

    return () => {
      mounted = false;
    };
  }, []);

  const handleCommand = (cmd: string) => {
    const command = commands[cmd.toLowerCase()];
    if (command) {
      const output = command
        .execute()
        .filter((line): line is string => line !== null);
      setVisibleLines((prev) => [...prev, `> ${cmd}`, ...output]);
    } else {
      setVisibleLines((prev) => [
        ...prev,
        `> ${cmd}`,
        'Command not found. Type "help" for available commands.',
      ]);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleCommand(input);
      setCommandHistory((prev) => [...prev, input]);
      setInput("");
      setHistoryIndex(-1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (historyIndex < commandHistory.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setInput(commandHistory[commandHistory.length - 1 - newIndex]);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setInput(commandHistory[commandHistory.length - 1 - newIndex]);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setInput("");
      }
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Resizable
        size={windowSize}
        onResizeStop={(e, direction, ref, d) => {
          setWindowSize({
            width: windowSize.width + d.width,
            height: windowSize.height + d.height,
          });
        }}
        minWidth={theme?.window?.minWidth || 400}
        minHeight={theme?.window?.minHeight || 300}
        enable={
          theme?.window?.resizable
            ? {
                top: false,
                right: true,
                bottom: true,
                left: false,
                topRight: false,
                bottomRight: true,
                bottomLeft: false,
                topLeft: false,
              }
            : {}
        }
      >
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="w-full h-full overflow-hidden flex flex-col"
          style={{
            backgroundColor: theme?.container?.backgroundColor || "#000000",
            color: theme?.container?.textColor || "#00ff00",
            fontFamily: theme?.container?.fontFamily || "monospace",
            borderRadius: "8px",
            border: `1px solid ${theme?.container?.borderColor || "#333333"}`,
          }}
        >
          {theme?.header?.show !== false && (
            <div className="flex flex-col">
              <div className="flex items-center gap-2 p-3 border-b border-[#333333]">
                <span
                  className="text-sm opacity-50 ml-2"
                  style={{
                    textAlign: theme?.window?.titleAlignment || "left",
                  }}
                >
                  {theme?.window?.title || "terminal"}
                </span>
              </div>

              {theme?.tabs?.show && (
                <div
                  className="flex border-b border-[#333333]"
                  style={{
                    backgroundColor: theme?.tabs?.backgroundColor || "#1a1a1a",
                  }}
                >
                  {theme.tabs.items?.map((tab, index) => (
                    <div
                      key={tab}
                      className="px-4 py-2 cursor-pointer"
                      style={{
                        backgroundColor:
                          index === activeTab
                            ? theme?.tabs?.activeColor || "#2a2a2a"
                            : "transparent",
                        color: theme?.tabs?.textColor || "#ffffff",
                      }}
                      onClick={() => setActiveTab(index)}
                    >
                      {tab}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="flex-1 flex overflow-hidden">
            {theme?.lineNumbers?.show && (
              <div
                className="select-none py-4 text-right border-r"
                style={{
                  width: theme?.lineNumbers?.width || 50,
                  backgroundColor:
                    theme?.lineNumbers?.backgroundColor || "#1a1a1a",
                  color: theme?.lineNumbers?.color || "#666666",
                  borderColor: theme?.container?.borderColor || "#333333",
                }}
              >
                {visibleLines.map((_, i) => (
                  <div key={i} className="px-2">
                    {i + 1}
                  </div>
                ))}
              </div>
            )}

            <div
              ref={terminalRef}
              className="flex-1 p-4 space-y-1 overflow-y-auto"
            >
              {visibleLines.map((line, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="font-mono whitespace-pre-wrap"
                  style={{
                    color: line.startsWith("Error:")
                      ? theme?.text?.error?.color || "#ff0000"
                      : line.startsWith("Success:")
                        ? theme?.text?.success?.color || "#00ff00"
                        : theme?.container?.textColor || "#00ff00",
                  }}
                >
                  {line}
                </motion.div>
              ))}

              <div className="flex items-center gap-2 mt-2">
                <span style={{ color: theme?.prompt?.userColor || "#00ff00" }}>
                  {theme?.prompt?.user || "guest"}@profile
                </span>
                <span
                  style={{ color: theme?.prompt?.symbolColor || "#ffffff" }}
                >
                  :
                </span>
                <span style={{ color: theme?.prompt?.pathColor || "#0088ff" }}>
                  ~
                </span>
                <span
                  style={{ color: theme?.prompt?.symbolColor || "#ffffff" }}
                >
                  {theme?.prompt?.symbol || "$"}
                </span>
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  className="flex-1 bg-transparent outline-none"
                  style={{ color: theme?.container?.textColor || "#00ff00" }}
                  autoFocus
                />
              </div>
            </div>
          </div>

          {theme?.statusBar?.show && (
            <div
              className="flex items-center px-4 gap-4 border-t"
              style={{
                height: theme?.statusBar?.height || 25,
                backgroundColor: theme?.statusBar?.backgroundColor || "#1a1a1a",
                color: theme?.statusBar?.textColor || "#666666",
                borderColor: theme?.container?.borderColor || "#333333",
              }}
            >
              {theme?.statusBar?.items?.time && <StatusBarTime />}
              {theme?.statusBar?.items?.systemInfo && (
                <span>{`${navigator.platform} - ${window.innerWidth}x${window.innerHeight}`}</span>
              )}
              {theme?.statusBar?.items?.customText && (
                <span>{theme.statusBar.items.customText}</span>
              )}
            </div>
          )}
        </motion.div>
      </Resizable>
    </div>
  );
}

function StatusBarTime() {
  const [time, setTime] = useState(new Date().toLocaleTimeString());

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return <span>{time}</span>;
}
