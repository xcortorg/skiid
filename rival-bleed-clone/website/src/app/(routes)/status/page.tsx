"use client";
import { TbCloudDataConnection } from "react-icons/tb";
import { MdOutlineTimeline } from "react-icons/md";
import { ImConnection } from "react-icons/im";
import { HiServerStack } from "react-icons/hi2";
import { FaUsers } from "react-icons/fa";
import useAxios, { RefetchOptions } from "axios-hooks";
import moment from "moment";
import Loader from "@/components/(global)/Loader";
import { useEffect, useState } from "react";
import { RefreshCwIcon } from "lucide-react";
import { AxiosPromise, AxiosRequestConfig } from "axios";

const fetchShard = async (shardId: number) => {
    const response = await fetch(`/shards`);
    if (!response.ok) {
        console.error('Failed to fetch shard data');
        return null;
    }
    const data = await response.json();
    const shards: IShard[] = Object.keys(data).map((key) => {
        const shard: IShard = {
            shard_id: data[key].shard_id,
            shard_name: data[key].shard_name,
            status: data[key].status,
            guilds: data[key].guilds,
            users: data[key].users,
            latency: data[key].latency,
            guild_ids: data[key].guild_ids,
            uptime: data[key].uptime,
        };
        return shard;
    });
    return shards.find((shard) => shard.shard_id === shardId);
}

export default function Status() {
    const [{ data, loading, error }, refetch] = useAxios({
        url: "/api/status",
    });

    let shards: IShard[] = [];

    if (!error && data) {
        shards = Object.keys(data).map((key) => {
            const shard: IShard = {
                shard_id: data[key].shard_id,
                shard_name: data[key].shard_name,
                status: data[key].status,
                guilds: data[key].guilds,
                users: data[key].users,
                latency: data[key].latency,
                guild_ids: data[key].guild_ids,
                uptime: data[key].uptime,
            };
            return shard;
        });
    }

    return (
        <>
            {error && (
                <div className="flex items-center justify-center text-white">
                    <p className="text-2xl">Error: {error.message}</p>
                </div>
            )}
            {loading && <Loader />}
            {!error && !loading && (
                <main className="mt-20 mx-10">
                    <section className="max-w-5xl mx-auto w-full pb-20 -mt-[4rem]">
                        <div className="flex flex-row justify-between gap-20">
                            <div className="flex flex-row items-center gap-2 text-white">
                                <div className="flex flex-row justify-center items-center w-12 h-12 bg-generic-200 rounded-full">
                                    <TbCloudDataConnection className="w-6 h-6" />
                                </div>
                                <h1 className="text-3xl font-bold">Shards</h1>
                            </div>
                        </div>
                        <div className="grid grid-cols-1 gap-4 mt-10 lg:flex-row sm:grid-cols-2 md:grid-cols-3">
                            {shards &&
                                shards.map((shard: IShard) => (
                                    <Shard key={shard.shard_id} shard={shard} refetch={refetch} />
                                ))}
                        </div>
                    </section>
                </main>
            )}
        </>
    );
}

const Shard = ({ shard, refetch }: { shard: IShard, refetch: (config?: string | AxiosRequestConfig<any> | undefined, options?: RefetchOptions) => AxiosPromise<any> }) => {
    const uptime = new Date(shard.uptime * 1000);
    const [counter, setCounter] = useState(0);

    const handleRefreshClick = async () => {
        const refreshed = await fetchShard(shard.shard_id);
        if (!refreshed) return
        shard = refreshed;
        setCounter(0)
    };

    useEffect(() => {
        const interval = setInterval(() => {
            setCounter((prevCounter) => prevCounter + 1);
        }, 1000);

        return () => {
            clearInterval(interval);
        };
    }, []);

    return (
        <div
            className={`flex flex-col py-6 rounded-3xl bg-generic-200 border transition-shadow duration-200 ease-linear border-generic-300 text-white ${shard.status !== "Operational" ? "bg-red-500" : "bg-generic-200"}`}
        >
            <div className="h-full flex flex-col justify-between">
                <div className="px-6">
                    <div className="flex items-start justify-between gap-x-4">
                        <div className="flex items-center gap-2">
                            <p className="text-xl font-semibold inline-flex items-center">
                                Shard {shard.shard_id}
                            </p>
                        </div>
                        <div
                            className={`flex justify-center items-center ${shard.status !== "Operational" ? "text-red-500" : "bg-generic-400"} border border-generic-300 rounded-xl px-2 py-1 gap-2`}
                        >
                            <div
                                className={`w-4 h-4 ${shard.status !== "Operational" ? "bg-red-500" : "bg-green-500"} rounded-full animate-pulse`}
                            ></div>
                            <p
                                className={`text-sm font-semibold inline-flex items-center ${shard.status !== "Operational" ? "text-red-500" : "text-green-500"}`}
                            >
                                {shard.status}
                            </p>
                        </div>
                    </div>
                    <div className="flex flex-row gap-2 items-center">
                        <RefreshCwIcon className="text-generic-pink hover:text-white hover:cursor-pointer" size={12} onClick={() => handleRefreshClick()}/>
                        <p className="text-sm text-generic-pink">
                            {counter == 0 ? "Just Now" : counter + "s ago"}
                        </p>
                    </div>
                </div>
                <hr className="border-t border-generic-300 w-full my-4" />
                <div className="grid grid-cols-2 gap-4 px-6">
                    <div className="flex flex-col gap-2">
                        <p className="text-md text-generic-600">Uptime</p>
                        <div className="flex flex-row gap-2 items-center">
                            <MdOutlineTimeline className="text-generic-600" />
                            <p className="text-md font-semibold">
                                {shard.status != 'Operational' ? "N/A" : moment
                                        .duration(uptime.getTime() - Date.now())
                                        .humanize()}
                            </p>
                        </div>
                    </div>
                    <div className="flex flex-col gap-2">
                        <p className="text-md text-generic-600">Latency</p>
                        <div className="flex flex-row gap-2 items-center">
                            <ImConnection className="text-generic-600" />
                            <p className="text-md font-semibold">
                                {shard.latency >= 10000 ? "N/A" : `${shard.latency}ms`}
                            </p>
                        </div>
                    </div>
                    <div className="flex flex-col gap-2">
                        <p className="text-md text-generic-600">Servers</p>
                        <div className="flex flex-row gap-2 items-center">
                            <HiServerStack className="text-generic-600" />
                            <p className="text-md font-semibold">
                                {shard.guilds.toLocaleString()}
                            </p>
                        </div>
                    </div>
                    <div className="flex flex-col gap-2">
                        <p className="text-md text-generic-600">Users</p>
                        <div className="flex flex-row gap-2 items-center">
                            <FaUsers className="text-generic-600" />
                            <p className="text-md font-semibold">
                                {shard.users.toLocaleString()}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

interface IShard {
    shard_id: number;
    shard_name: string;
    status: string;
    guilds: number;
    users: number;
    latency: number;
    guild_ids: number[];
    uptime: number;
}