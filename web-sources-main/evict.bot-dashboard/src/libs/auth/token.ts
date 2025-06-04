"use client"

export function getUserToken(): string | null {
    return window.localStorage.getItem("userToken")
}

export function checkDashboardAuth(): boolean {
    return !!window.localStorage.getItem("userToken")
}

// export function setUserToken(token: string): void {
//     if (typeof window !== 'undefined') {
//         try {
//             localStorage.setItem("userToken", token)
//             tokenCache = token
//         } catch (error) {
//             console.error("Error setting token:", error)
//         }
//     }
// }

// export function clearUserToken(): void {
//     if (typeof window !== 'undefined') {
//         try {
//             localStorage.removeItem("userToken")
//             tokenCache = null
//         } catch (error) {
//             console.error("Error clearing token:", error)
//         }
//     }
// } 