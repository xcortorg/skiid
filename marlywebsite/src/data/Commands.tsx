import { BaseCategory, Category, Command } from "@/types/Command"
import { BiMusic } from "react-icons/bi"
import { IoSettingsOutline } from "react-icons/io5"
import { LiaHammerSolid } from "react-icons/lia"
import { LuBookMinus, LuPaperclip } from "react-icons/lu"
import { PiPalette } from "react-icons/pi"
import { IoImageOutline } from "react-icons/io5";

export const getCategoriesFromCommands: (commands: Command[]) => Category[] = commands => {
    const categories: Category[] = []

    // First, group all commands by category
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

    // Sort categories by command count in descending order
    categories.sort((a, b) => {
        // Primary sort by command count
        const countDiff = b.commands.length - a.commands.length
        if (countDiff !== 0) return countDiff

        // Secondary sort by category name if counts are equal
        return a.name.localeCompare(b.name)
    })

    return categories
}

export const BaseCategories: BaseCategory[] = [
    {
        name: "Server",
        icon: <IoSettingsOutline />
    },
    {
        name: "Information",
        icon: <LuBookMinus />
    },
    {
        name: "Utility",
        icon: <LuPaperclip />
    },
    {
        name: "Fun",
        icon: <PiPalette />
    },
    {
        name: "Moderation",
        icon: <LiaHammerSolid />
    },
    {
        name: "Manipulation",
        icon: <IoImageOutline />
    },
    {
        name: "Music",
        icon: <BiMusic />
    }
]
