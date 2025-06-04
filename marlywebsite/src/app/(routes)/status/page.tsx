"use client"
//import Loader from "@/components/(global)/Loader"
import { AxiosPromise, AxiosRequestConfig } from "axios"
import useAxios, { RefetchOptions } from "axios-hooks"
import { Search } from "lucide-react"
import moment from "moment"
import { useEffect, useState } from "react"
import { FaUsers } from "react-icons/fa"
import { GrRefresh } from "react-icons/gr"
import { HiMiniSignal, HiServerStack } from "react-icons/hi2"
import { ImConnection } from "react-icons/im"
import { MdOutlineTimeline } from "react-icons/md"
import { PiWifiSlashBold } from "react-icons/pi"
import { TbCloudDataConnection } from "react-icons/tb"

interface IShard {
    id: string
    guilds: number
    users: number
    ping: number
    uptime: number
}

export default function Status() {
    const [{ data, loading, error }, refetch] = useAxios({
        baseURL: "https://network.skunkk.xyz",
        url: "/status"
    })
    const [highlightedShardId, setHighlightedShardId] = useState<string | null>(null)
    const [serverId, setServerId] = useState("")

    let shards: IShard[] = []

    if (!error && data) {
        shards = data.shards.map((shard: any) => ({
            id: shard.shard_id.toString(),
            guilds: shard.server_count,
            users: shard.cached_user_count,
            ping: shard.latency,
            uptime: shard.uptime
        }))
    }

    const handleSearch = () => {
        if (!serverId) {
            setHighlightedShardId(null)
            return
        }
        try {
            const shardId = (BigInt(serverId) >> BigInt(22)) % BigInt(shards.length)
            const shardIdString = shardId.toString()
            console.log('Calculated Shard ID:', shardIdString)
            console.log('Available Shards:', shards.map(s => s.id))
            setHighlightedShardId(shardIdString)
            
            setTimeout(() => {
                const element = document.getElementById(`shard-${shardIdString}`)
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'center' })
                }
            }, 100)
        } catch (error) {
            console.error("Invalid server ID")
            setHighlightedShardId(null)
        }
    }

    useEffect(() => {
        console.log('Highlighted Shard ID:', highlightedShardId)
    }, [highlightedShardId])

    return (
        <>
            {error && (
                <main className="pt-20 mx-10">
                    <section className="max-w-5xl mx-auto w-full pb-20 -mt-[4rem]">
                        <div className="flex flex-row justify-between gap-20">
                            <div className="flex flex-row items-center gap-2 text-white">
                                <div className="flex flex-row justify-center items-center w-12 h-12 bg-marly-200 rounded-full">
                                    <TbCloudDataConnection className="w-6 h-6" />
                                </div>
                                <h1 className="text-3xl font-bold">Shards</h1>
                            </div>
                        </div>
                        <div className="flex flex-col items-center justify-center pb-[40vh] pt-20">
                            <PiWifiSlashBold className="text-6xl text-[#4F4F4F]" />
                            <p className="text-2xl font-medium text-[#969696]">No Status Found</p>
                        </div>
                    </section>
                </main>
            )}
            {/* {loading && <Loader />} */}
            {!error && !loading && (
                <main className="pt-20 mx-10">
                    <section className="max-w-5xl mx-auto w-full pb-20 -mt-[4rem]">
                        <div className="flex flex-row justify-between items-center">
                            <div className="flex flex-row items-center gap-2 text-white">
                                <div className="flex flex-row justify-center items-center w-12 h-12 bg-marly-300 rounded-full">
                                    <HiMiniSignal className="w-7 h-7 text-marly-main" />
                                </div>
                                <h1 className="text-3xl font-bold">Shards</h1>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="relative flex items-center">
                                    <input
                                        type="text"
                                        value={serverId}
                                        onChange={(e) => setServerId(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                                handleSearch()
                                            }
                                        }}
                                        placeholder="Enter your Server ID"
                                        className="w-60 px-4 py-2 bg-marly-400 border border-marly-card-border rounded-2xl text-white placeholder:text-marly-main focus:outline-none focus:ring-2 focus:ring-marly-main"
                                    />
                                </div>
                                <button 
                                    onClick={handleSearch}
                                    className="flex items-center justify-center w-11 h-11 rounded-2xl border border-marly-card-border bg-marly-200 hover:bg-marly-300 transition-colors"
                                >
                                    <Search className="text-marly-main" size={20} />
                                </button>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 gap-4 mt-10 lg:flex-row sm:grid-cols-2 md:grid-cols-3">
                            {shards.map((shard, index) => {
                                console.log(`Comparing shard ${shard.id} with highlighted ${highlightedShardId}`)
                                return (
                                    <Shard 
                                        key={index} 
                                        shard={shard} 
                                        refetch={refetch}
                                        isHighlighted={highlightedShardId !== null && highlightedShardId === shard.id}
                                    />
                                )
                            })}
                        </div>
                    </section>
                </main>
            )}
        </>
    )
}

const Shard = ({
    shard,
    refetch,
    isHighlighted
}: {
    shard: IShard
    refetch: (
        config?: string | AxiosRequestConfig<any> | undefined,
        options?: RefetchOptions
    ) => AxiosPromise<any>
    isHighlighted: boolean
}) => {
    const [counter, setCounter] = useState(0)
    const uptime = new Date(shard.uptime * 1000)

    const getShardStatus = () => {
        if (shard.ping > 3000) {
            return {
                text: "Starting",
                color: "text-yellow-500",
                bgColor: "bg-yellow-500"
            };
        }
        return {
            text: "Operational",
            color: "text-green-500",
            bgColor: "bg-green-500"
        };
    };

    const status = getShardStatus();

    useEffect(() => {
        if (isHighlighted) {
            console.log(`Shard ${shard.id} is highlighted`)
        }
    }, [isHighlighted, shard.id])

    useEffect(() => {
        const interval = setInterval(() => {
            setCounter(prevCounter => prevCounter + 1)
        }, 1000)

        return () => {
            clearInterval(interval)
        }
    }, [])

    return (
        <div
            id={`shard-${shard.id}`}
            className={`flex flex-col py-6 rounded-3xl bg-marly-200 border transition-all duration-200 ease-linear ${
                isHighlighted 
                    ? 'border-green-500 ring-2 ring-green-500 shadow-lg' 
                    : 'border-marly-card-border'
            } text-white`}>
            <div className="h-full flex flex-col justify-between">
                <div className="px-6">
                    <div className="flex items-start justify-between gap-x-4">
                        <div className="flex items-center gap-2">
                            <p className="text-xl font-semibold inline-flex items-center">
                                Shard {shard.id}
                            </p>
                        </div>
                        <div
                            className={`flex justify-center items-center bg-marly-200 border border-marly-card-border rounded-xl px-2 py-1 gap-2`}>
                            <div
                                className={`w-4 h-4 ${status.bgColor} rounded-full animate-pulse`}></div>
                            <p className={`text-lg font-normal inline-flex items-center ${status.color}`}>
                                {status.text}
                            </p>
                        </div>
                    </div>
                    <div className="flex flex-row gap-2 items-center">
                        <GrRefresh 
                            className="text-marly-main opacity-50" 
                            size={20} 
                        />
                        <p className="text-sm text-marly-main">
                            {counter == 0 ? "Just Now" : counter + "s ago"}
                        </p>
                    </div>
                </div>
                <hr className="border-t border-marly-300 w-full my-4" />
                <div className="grid grid-cols-2 gap-4 px-6">
                    <div className="flex flex-col gap-2">
                        <p className="text-md text-marly-main">Uptime</p>
                        <div className="flex flex-row gap-2 items-center">
                            <MdOutlineTimeline className="text-marly-main" />
                            <p className="text-md font-semibold">
                                {shard.uptime == 0
                                    ? "N/A"
                                    : moment.duration(uptime.getTime() - Date.now()).humanize()}
                            </p>
                        </div>
                    </div>
                    <div className="flex flex-col gap-2">
                        <p className="text-md text-marly-main">Latency</p>
                        <div className="flex flex-row gap-2 items-center">
                            <ImConnection className="text-marly-main" />
                            <p className="text-md font-semibold">{shard.ping}ms</p>
                        </div>
                    </div>
                    <div className="flex flex-col gap-2">
                        <p className="text-md text-marly-main">Servers</p>
                        <div className="flex flex-row gap-2 items-center">
                            <HiServerStack className="text-marly-main" />
                            <p className="text-md font-semibold">{shard.guilds.toLocaleString()}</p>
                        </div>
                    </div>
                    <div className="flex flex-col gap-2">
                        <p className="text-md text-marly-main">Users</p>
                        <div className="flex flex-row gap-2 items-center">
                            <FaUsers className="text-marly-main" />
                            <p className="text-md font-semibold">{shard.users.toLocaleString()}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}