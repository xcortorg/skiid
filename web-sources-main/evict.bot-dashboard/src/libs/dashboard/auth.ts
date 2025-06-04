export function checkDashboardAuth() {
    return true
}

export function getDashboardToken() {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('userToken')
}