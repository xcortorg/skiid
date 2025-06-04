import axios from "axios"
import fs from "fs/promises"
import { NextResponse } from "next/server"
import path from "path"

const DATA_PATH = path.join(process.cwd(), "src/app/(routes)/status/data.json")
const MIN_INTERVAL = 5 * 60 * 1000

export async function GET() {
    try {
        let history = []
        try {
            history = JSON.parse(await fs.readFile(DATA_PATH, "utf-8"))
        } catch {}

        const lastCheck = history[history.length - 1]?.timestamp
        const timeSinceLastCheck = Date.now() - (lastCheck || 0)

        if (!lastCheck || timeSinceLastCheck >= MIN_INTERVAL) {
            const isUp = await axios
                .get("https://evict.bot", { timeout: 5000 })
                .then(() => true)
                .catch(() => false)

            history.push({ timestamp: Date.now(), isUp })

            const ninetyDaysAgo = Date.now() - 90 * 24 * 60 * 60 * 1000
            history = history.filter(
                (item: { timestamp: number }) => item.timestamp > ninetyDaysAgo
            )

            await fs.writeFile(DATA_PATH, JSON.stringify(history))
        }

        return NextResponse.json({ history })
    } catch (error) {
        return NextResponse.json({ error: "Failed to check status" }, { status: 500 })
    }
}
