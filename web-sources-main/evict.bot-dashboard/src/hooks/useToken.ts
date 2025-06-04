"use client"

import { useState, useEffect } from 'react'

export const useToken = () => {
    const [token, setToken] = useState<string | null>(() => {
        if (typeof window !== 'undefined') {
            return localStorage.getItem('userToken')
        }
        return null
    })

    useEffect(() => {
        const storedToken = localStorage.getItem('userToken')
        if (storedToken !== token) {
            setToken(storedToken)
        }
    }, [])

    return token
} 