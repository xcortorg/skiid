"use client"
import { AxiosPromise } from "axios"
import useAxios from "axios-hooks"
import { AnimatePresence, motion } from "framer-motion"
import { CircuitBoardIcon, GaugeCircleIcon, RefreshCwIcon, ServerIcon } from "lucide-react"
import { useMemo } from "react"
import { FaUsers } from "react-icons/fa"
import { ImConnection } from "react-icons/im"
import { PiWifiSlashBold } from "react-icons/pi"

const fadeInUp = {
    initial: { opacity: 0, y: 20 },
    animate: { 
        opacity: 1, 
        y: 0,
        transition: {
            duration: 0.5,
            ease: [0.25, 0.1, 0, 1]
        }
    },
    exit: {
        opacity: 0,
        y: 10,
        transition: {
            duration: 0.3,
            ease: [0.25, 0.1, 0, 1]
        }
    }
}

const stagger = {
    animate: {
        transition: {
            staggerChildren: 0.1,
            delayChildren: 0.3
        }
    }
}

interface ICluster {
    status: string
    latency: number
    guilds: number
    users: number
    shards: {
        ids: number[]
        count: number
        latencies: { [key: string]: number }
    }
}

interface IStatusResponse {
    status: string
    clusters: { [key: string]: ICluster }
    total: {
        guilds: number
        users: number
        shards: number
        clusters: number
        latency: number
    }
}

export default function Status() {
    const [{ data, loading, error }, refetch] = useAxios<IStatusResponse>({
        baseURL: process.env.NODE_ENV === 'development' ? 'https://api-dev.evict.bot' : 'https://api.evict.bot',
        url: "/status"
    })

    const clusters = useMemo(() => {
        if (!data) return []
        return Object.entries(data.clusters).map(([id, cluster]) => ({
            id,
            ...cluster
        }))
    }, [data])

    const overview = useMemo(() => ({
        avgLatency: data?.total.latency ?? 0,
        totalServers: data?.total.guilds ?? 0,
        totalUsers: data?.total.users ?? 0,
        totalShards: data?.total.shards ?? 0,
        totalClusters: data?.total.clusters ?? 0,
        status: data?.status ?? "offline"
    }), [data])

    const OverviewCard = () => (
        <motion.div 
            variants={fadeInUp}
            className="w-full rounded-3xl bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 border border-white/[0.05] p-6 shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]"
        >
            <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-6">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-white/5 border border-evict-primary/20">
                        <GaugeCircleIcon className="w-6 h-6 text-evict-primary/80" />
                    </div>
                    <h2 className="text-xl font-semibold text-white">Status Overview</h2>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-black/20 border border-white/5 rounded-xl sm:ml-auto">
                    <div className={`w-2 h-2 ${overview.status === "online" ? "bg-green-500" : "bg-red-500"} rounded-full animate-pulse`}></div>
                    <p className={`text-sm font-medium ${overview.status === "online" ? "text-green-500" : "text-red-500"}`}>
                        {overview.status === "online" ? "All Systems Operational" : "System Disruption"}
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="flex flex-col gap-2 p-4 rounded-lg bg-black/20 border border-white/5">
                    <div className="flex items-center gap-2 text-evict-primary/80">
                        <ImConnection className="w-4 h-4"/>
                        <span className="text-sm">Average Latency</span>
                    </div>
                    <p className="text-2xl font-medium text-white">{overview.avgLatency.toFixed(2)}ms</p>
                </div>
                <div className="flex flex-col gap-2 p-4 rounded-lg bg-black/20 border border-white/5">
                    <div className="flex items-center gap-2 text-evict-primary/80">
                        <ServerIcon className="w-4 h-4"/>
                        <span className="text-sm">Total Servers</span>
                    </div>
                    <p className="text-2xl font-medium text-white">{overview.totalServers.toLocaleString()}</p>
                </div>
                <div className="flex flex-col gap-2 p-4 rounded-lg bg-black/20 border border-white/5">
                    <div className="flex items-center gap-2 text-evict-primary/80">
                        <FaUsers className="w-4 h-4"/>
                        <span className="text-sm">Total Users</span>
                    </div>
                    <p className="text-2xl font-medium text-white">{overview.totalUsers.toLocaleString()}</p>
                </div>
            </div>
        </motion.div>
    )

    const ClusterCard = ({ cluster, id }: { cluster: ICluster & { id: string }, id: string }) => (
        <motion.div
            variants={fadeInUp}
            className="group relative bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 rounded-3xl p-6 hover:bg-white/[0.04] transition-all duration-300 border border-white/[0.05] shadow-[inset_0px_0px_1px_rgba(255,255,255,0.1)]"
        >
            <div className="flex items-center justify-between gap-x-4 mb-4">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-white/5 border border-evict-primary/20">
                        <CircuitBoardIcon className="w-5 h-5 text-evict-primary/80" />
                    </div>
                    <div>
                        <p className="text-xl font-semibold text-white">Cluster {id}</p>
                        <div className="flex items-center gap-2 mt-1">
                            <div className={`w-1.5 h-1.5 ${cluster.status === "online" ? "bg-green-500" : "bg-red-500"} rounded-full animate-pulse`}></div>
                            <p className={`text-xs ${cluster.status === "online" ? "text-green-500" : "text-red-500"}`}>
                                {cluster.status === "online" ? "Operational" : "Offline"}
                            </p>
                        </div>
                    </div>
                </div>
                
                <motion.button 
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={(e) => {
                        e.preventDefault()
                        refetch()
                    }}
                    className="group p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 transition-all duration-200"
                >
                    <RefreshCwIcon className="w-4 h-4 text-evict-primary/60 group-hover:text-evict-primary/80 transition-colors" />
                </motion.button>
            </div>

            <div className="flex flex-col gap-4 mb-2">
                <div className="flex items-center gap-2">
                    <div className="w-1 h-1 bg-evict-primary/40 rounded-full"></div>
                    <div className="flex items-center gap-1.5">
                        <p className="text-xs text-white/60">{cluster.latency.toFixed(2)}ms latency</p>
                        <span className="text-white/20">•</span>
                        <p className="text-xs text-white/60">{cluster.guilds.toLocaleString()} servers</p>
                        <span className="text-white/20">•</span>
                        <p className="text-xs text-white/60">{cluster.users.toLocaleString()} users</p>
                    </div>
                </div>
            </div>

            <div className="space-y-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <CircuitBoardIcon className="w-4 h-4 text-evict-primary/60" />
                        <p className="text-sm text-evict-primary/80">Shard Distribution</p>
                    </div>
                    <p className="text-xs text-white/40">{Object.keys(cluster.shards.latencies).length} of {cluster.shards.count} active</p>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {Object.entries(cluster.shards.latencies).map(([shardId, latency]) => (
                        <div key={shardId} className="flex items-center justify-between p-2.5 bg-black/20 rounded-lg border border-white/5">
                            <div className="flex items-center gap-2">
                                <div className="w-1 h-1 bg-evict-primary/40 rounded-full"></div>
                                <p className="text-xs text-white/60">#{shardId}</p>
                            </div>
                            <p className="text-xs font-medium text-white">{latency.toFixed(1)}ms</p>
                        </div>
                    ))}
                </div>
            </div>
        </motion.div>
    )

    return (
        <AnimatePresence mode="wait">
            {error ? (
                <motion.main
                    key="error"
                    initial={fadeInUp.initial}
                    animate={fadeInUp.animate}
                    exit={fadeInUp.exit}
                    className="pt-20 mx-4 sm:mx-10"
                >
                    <section className="max-w-7xl mx-auto w-full pb-20">
                        <div className="flex flex-col items-center justify-center py-20">
                            <div className="p-6 rounded-2xl bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 border border-white/[0.05] mb-4">
                                <PiWifiSlashBold className="w-12 h-12 text-evict-primary/80" />
                            </div>
                            <h3 className="text-xl font-medium text-white mb-2">Connection Error</h3>
                            <p className="text-white/60">Unable to fetch status information</p>
                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={() => refetch()}
                                className="mt-6 px-6 py-2 bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] rounded-xl text-white/80 font-medium transition-colors"
                            >
                                Try Again
                            </motion.button>
                        </div>
                    </section>
                </motion.main>
            ) : loading ? (
                <motion.main
                    key="loading"
                    initial={fadeInUp.initial}
                    animate={fadeInUp.animate}
                    exit={fadeInUp.exit}
                    className="pt-20 mx-4 sm:mx-10"
                >
                    <section className="max-w-7xl mx-auto w-full pb-20">
                        <div className="w-full rounded-3xl bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 border border-white/[0.05] p-6">
                            <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-6 animate-pulse">
                                <div className="flex items-center gap-3">
                                    <div className="w-11 h-11 bg-white/20 rounded-xl"></div>
                                    <div className="h-7 w-40 bg-white/20 rounded-lg"></div>
                                </div>
                                <div className="h-8 w-36 bg-white/20 rounded-xl sm:ml-auto"></div>
                            </div>
                            
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                {[...Array(3)].map((_, i) => (
                                    <div key={i} className="flex flex-col gap-3 p-4 rounded-lg bg-black/20 border border-white/5 animate-pulse">
                                        <div className="flex items-center gap-2">
                                            <div className="w-4 h-4 bg-white/20 rounded"></div>
                                            <div className="h-4 w-24 bg-white/20 rounded"></div>
                                        </div>
                                        <div className="h-8 w-20 bg-white/20 rounded"></div>
                                        <div className="h-3 w-32 bg-white/20 rounded"></div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="grid grid-cols-1 gap-6 mt-8 sm:grid-cols-2 lg:grid-cols-3">
                            {[...Array(3)].map((_, i) => (
                                <div key={i} className="rounded-3xl bg-white/[0.02] backdrop-blur-md backdrop-saturate-150 border border-white/[0.05] p-6 animate-pulse">
                                    <div className="flex items-center justify-between gap-4 mb-6">
                                        <div className="flex items-center gap-3">
                                            <div className="w-11 h-11 bg-white/20 rounded-xl"></div>
                                            <div>
                                                <div className="h-7 w-32 bg-white/20 rounded-lg mb-2"></div>
                                                <div className="h-4 w-24 bg-white/20 rounded"></div>
                                            </div>
                                        </div>
                                        <div className="w-10 h-10 bg-white/20 rounded-lg"></div>
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                                        {[...Array(2)].map((_, j) => (
                                            <div key={j} className="flex flex-col gap-3 p-4 rounded-lg bg-black/20 border border-white/5">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-4 h-4 bg-white/20 rounded"></div>
                                                    <div className="h-4 w-20 bg-white/20 rounded"></div>
                                                </div>
                                                <div className="h-5 w-16 bg-white/20 rounded"></div>
                                            </div>
                                        ))}
                                    </div>

                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <div className="w-4 h-4 bg-white/20 rounded"></div>
                                                <div className="h-4 w-28 bg-white/20 rounded"></div>
                                            </div>
                                            <div className="h-4 w-20 bg-white/20 rounded"></div>
                                        </div>
                                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                            {[...Array(4)].map((_, k) => (
                                                <div key={k} className="h-10 bg-black/20 rounded-lg border border-white/5"></div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                </motion.main>
            ) : (
                <motion.div
                    key="content"
                    initial="hidden"
                    animate="visible"
                    exit="exit"
                    variants={{
                        hidden: { opacity: 0 },
                        visible: { 
                            opacity: 1,
                            transition: {
                                staggerChildren: 0.1,
                                delayChildren: 0.2
                            }
                        },
                        exit: { opacity: 0 }
                    }}
                >
                    <motion.div 
                        variants={fadeInUp}
                        className="relative border-b border-white/5 bg-black/20"
                    >
                        <div className="absolute inset-0 top-0 bg-[url('/noise.png')] opacity-5" />
                        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 pt-24 relative">
                            <motion.div className="text-center">
                                <motion.span 
                                    variants={fadeInUp}
                                    className="text-4xl sm:text-5xl md:text-6xl font-bold mb-4 md:mb-6 bg-gradient-to-r from-white to-evict-primary bg-clip-text text-transparent block"
                                >
                                    System Status
                                </motion.span>
                                <motion.p 
                                    variants={fadeInUp}
                                    className="text-base sm:text-lg text-white/60 max-w-3xl mx-auto"
                                >
                                    Real-time monitoring of clusters, shards, and performance metrics.
                                </motion.p>
                            </motion.div>
                        </div>
                    </motion.div>

                    <main className="relative">
                        <div className="absolute inset-0 z-0 pointer-events-none bg-gradient-to-br from-white/5 via-transparent to-zinc-400/5 mix-blend-overlay" />
                        
                        <motion.section 
                            variants={stagger}
                            className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-[70px] min-h-[calc(100vh-300px)]"
                        >
                            <OverviewCard />
                            <div className="grid grid-cols-1 gap-6 mt-8 sm:grid-cols-2 lg:grid-cols-3">
                                {clusters.map((cluster, i) => (
                                    <ClusterCard key={cluster.id} cluster={cluster} id={cluster.id} />
                                ))}
                            </div>
                        </motion.section>
                    </main>
                </motion.div>
            )}
        </AnimatePresence>
    )
}
