import { BaseCategory, Category, Command } from "@/types/Command"
import { BiMusic } from "react-icons/bi"
import { IoSettingsOutline } from "react-icons/io5"
import { TbAlignLeft } from "react-icons/tb"
import { FaRegStar } from "react-icons/fa6"
import { FaLastfm } from "react-icons/fa6"
import { GiCrystalGrowth } from "react-icons/gi"
import { TbNumber123 } from "react-icons/tb"
import { TbMessageQuestion } from "react-icons/tb"
import { CgAlignBottom } from "react-icons/cg"
import { FaPaperclip } from "react-icons/fa"
import { PiMicrophoneFill } from "react-icons/pi"

export const getCategoriesFromCommands: (commands: Command[]) => Category[] = commands => {
    const categories: Category[] = []

    categories.push({
        name: "All",
        icon: BaseCategories.find(c => c.name === "All")?.icon,
        commands: commands
    })

    commands.forEach(command => {
        if (command.name === "help") return

        const category = categories.find(c => c.name === command.category)

        if (!category) {
            categories.push({
                name: command.category,
                icon: BaseCategories.find(c => c.name === command.category)?.icon,
                commands: [command]
            })
        } else {
            category.commands.push(command)
        }
    })

    categories.sort((a, b) => b.commands.length - a.commands.length)

    return categories
}

export const BaseCategories: BaseCategory[] = [
    {
        name: "All",
        icon: <TbAlignLeft />
    },
    {
        name: "Music",
        icon: <BiMusic />
    },
    {
        name: "Servers",
        icon: <IoSettingsOutline />
    },
    {
        name: "StarBoard",
        icon: <FaRegStar />
    },
    {
        name: "LastFM",
        icon: <FaLastfm />
    },
    {
        name: "Level",
        icon: <GiCrystalGrowth />
    },
    {
        name: "Counters",
        icon: <TbNumber123 />
    },
    {
        name: "Snipe",
        icon: <TbMessageQuestion />
    },
    {
        name: "Information",
        icon: <CgAlignBottom />
    },
    {
        name: "Miscellaneous",
        icon: <FaPaperclip />
    },
    {
        name: "VoiceMaster",
        icon: <PiMicrophoneFill />
    }
]
