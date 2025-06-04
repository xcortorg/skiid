"use server"

import { signIn } from "@/auth"

export async function signInWithDiscord(redirectTo: string) {
    await signIn("discord", { redirectTo })
}
