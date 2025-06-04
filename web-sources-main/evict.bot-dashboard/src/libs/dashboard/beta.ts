interface BetaResponse {
    has_access: boolean;
}

interface ErrorResponse {
    error: string;
}

export async function checkBetaAccess(): Promise<BetaResponse> {
    const token = localStorage.getItem('userToken')
    if (!token) {
        throw new Error("Unauthorized")
    }

    const response = await fetch(`https://api.evict.bot/beta`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })

    if (!response.ok) {
        if (response.status === 401) {
            throw new Error("Unauthorized")
        }
        const error = await response.json() as ErrorResponse
        throw new Error(error.error || 'Failed to check beta access')
    }

    const data = await response.json()
    return data
}