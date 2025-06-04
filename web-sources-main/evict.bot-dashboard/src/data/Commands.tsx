import { Category, Command } from "@/types/Command";
import { BiCog, BiImage, BiInfoCircle, BiMicrophone, BiMusic, BiServer, BiShield, BiUser } from "react-icons/bi";
import { FaLastfm } from "react-icons/fa";
import { TbAlignLeft, TbCash } from "react-icons/tb";
import { SiFunimation } from "react-icons/si";
import { IoIosGift } from "react-icons/io";
import { CiStar } from "react-icons/ci";
import fallbackCommands from "./commands.json";

const apiKey = ""

const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes
let cachedCommands: Command[] | null = null;
let lastFetchTime: number | null = null;

async function getCommands(): Promise<Command[]> {
  try {
    if (cachedCommands && lastFetchTime && Date.now() - lastFetchTime < CACHE_DURATION) {
      console.info('Using cached commands data');
      return cachedCommands;
    }

    const response = await fetch('https://api.evict.bot/commands', {
      headers: {
        'Authorization': apiKey
      }
    });
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    
    const data = await response.json();
    cachedCommands = data.commands.map((command: any) => ({
      name: command.name,
      description: command.description,
      aliases: command.aliases || [],
      parameters: command.parameters?.map((param: any) => ({
        name: param.name,
        type: param.type,
        default: param.default || null,
        flags: param.flags ? {
          required: param.flags.required || [],
          optional: param.flags.optional || []
        } : null,
        optional: param.optional || false
      })) || [],
      category: command.category,
      permissions: command.permissions || [],
      donator: command.donator || false
    }));
    lastFetchTime = Date.now();
    
    console.info('Successfully fetched commands from API');
    if (!cachedCommands) throw new Error('Failed to process commands');
    return cachedCommands;

  } catch (error) {
    console.error('Failed to fetch from API, falling back to local data:', error);
    return fallbackCommands.commands as Command[];
  }
}

export let Commands: Command[] = fallbackCommands.commands as Command[];
export let Categories: Category[] = [];

const initializeCategories = (commands: Command[]) => [
    {
        name: "All",
        icon: <TbAlignLeft />,
        commands: commands,
    },
    {
        name: "Audio",
        icon: <BiMusic />,
        commands: commands.filter((command) => command.category === "Audio"),
    },
    {
        name: "Config",
        icon: <BiCog />,
        commands: commands.filter((command) => command.category === "Config"),
    },
    {
        name: "Economy",
        icon: <TbCash />,
        commands: commands.filter((command) => command.category === "Economy"),
    },
    {
        name: "Fun",
        icon: <SiFunimation />,
        commands: commands.filter((command) => command.category === "Fun"),
    },
    {
        name: "Information",
        icon: <BiInfoCircle />,
        commands: commands.filter((command) => command.category === "Information"),
    },
    {
        name: "Lastfm",
        icon: <FaLastfm />,
        commands: commands.filter((command) => command.category === "Lastfm"),
    },
    {
        name: "Moderation",
        icon: <BiShield />,
        commands: commands.filter((command) => command.category === "Moderation"),
    },
    {
        name: "Premium",
        icon: <CiStar />,
        commands: commands.filter((command) => command.category === "Premium"),
    },
    {
        name: "Roleplay",
        icon: <IoIosGift />,
        commands: commands.filter((command) => command.category === "Roleplay"),
    },
    {
        name: "Social",
        icon: <BiUser />,
        commands: commands.filter((command) => command.category === "Social"),
    },
    {
        name: "Utility",
        icon: <BiInfoCircle />,
        commands: commands.filter((command) => command.category === "Utility"),
    },
    {
        name: "VoiceMaster",
        icon: <BiMicrophone />,
        commands: commands.filter((command) => command.category === "VoiceMaster"),
    }
];

Categories = initializeCategories(Commands);

getCommands().then(commands => {
    Commands = commands;
    Categories = initializeCategories(commands);
});
