import argparse
import asyncio
import logging
import os
import sys
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Any, Dict, TextIO, Tuple

from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("ClusterManager")


class ClusterManager:
    def __init__(
        self,
        shards_per_cluster: int,
        num_clusters: int,
        heartbeat_host: str = "0.0.0.0",
        heartbeat_port: int = 8000,
    ) -> None:
        self.shards_per_cluster = shards_per_cluster
        self.num_clusters = num_clusters
        self.total_shards = shards_per_cluster * num_clusters
        self.heartbeat_host = heartbeat_host
        self.heartbeat_port = heartbeat_port
        self.clusters: Dict[int, Dict[str, Any]] = {}
        self.shard_info: Dict[int, Dict[int, Dict[str, Any]]] = {}
        self.timeout: timedelta = timedelta(seconds=30)

    async def start_cluster_process(
        self, cluster_id: int, start_shard: int, end_shard: int
    ) -> Tuple[asyncio.subprocess.Process, TextIO]:
        log_path = os.path.join("logs", f"cluster{cluster_id}.log")
        log_file = open(log_path, "a")
        process = await asyncio.create_subprocess_shell(
            f"{sys.executable} main.py --shard-start={start_shard} --shard-end={end_shard} --shard-count={self.total_shards} --heartbeat-host={self.heartbeat_host} --heartbeat-port={self.heartbeat_port}",
            stdout=log_file,
            stderr=log_file,
        )
        return process, log_file

    async def launch_clusters(self) -> None:
        os.makedirs("logs", exist_ok=True)
        for cluster_id in range(self.num_clusters):
            start_shard = cluster_id * self.shards_per_cluster
            end_shard = start_shard + self.shards_per_cluster

            process, log_file = await self.start_cluster_process(
                cluster_id, start_shard, end_shard
            )

            self.clusters[cluster_id] = {
                "process": process,
                "start_shard": start_shard,
                "end_shard": end_shard,
                "last_heartbeat": datetime.now(),
                "log_file": log_file,
            }
            self.shard_info[cluster_id] = {}
            logger.info(
                f"Launched cluster {cluster_id} for shards {start_shard}-{end_shard}"
            )

    async def handle_heartbeat(self, request: web.Request) -> web.Response:
        data = await request.json()
        shard_id = data.get("shard_id")
        if not isinstance(shard_id, int):
            return web.Response(status=200)

        now = datetime.now()
        cluster_id = shard_id // self.shards_per_cluster
        if cluster_id not in self.clusters:
            return web.Response(status=200)

        self.clusters[cluster_id]["last_heartbeat"] = now
        info = {
            "latency": data.get("latency"),
            "users": data.get("users"),
            "guilds": data.get("guilds"),
            "uptime": data.get("uptime"),
            "last_seen": now,
        }
        self.shard_info[cluster_id][shard_id] = info
        logger.info(
            f"Heartbeat: shard={shard_id} cluster={cluster_id} "
            f"latency={info['latency']} users={info['users']} guilds={info['guilds']} uptime={info['uptime']}"
        )
        return web.Response(status=200)

    async def handle_health(self, request: web.Request) -> web.Response:
        now = datetime.now()
        total_users = 0
        total_guilds = 0
        cluster_status: Dict[int, Any] = {}

        for cid, cluster in self.clusters.items():
            cluster_users = 0
            cluster_guilds = 0
            shards = []

            for sid, sinfo in sorted(self.shard_info[cid].items()):
                last_seen = sinfo["last_seen"]
                shards.append(
                    {
                        "id": sid,
                        "latency": sinfo.get("latency"),
                        "users": sinfo.get("users"),
                        "guilds": sinfo.get("guilds"),
                        "uptime": sinfo.get("uptime"),
                        "seconds_since_seen": (now - last_seen).total_seconds(),
                    }
                )
                cluster_users += sinfo.get("users", 0) or 0
                cluster_guilds += sinfo.get("guilds", 0) or 0

            total_users += cluster_users
            total_guilds += cluster_guilds
            last_hb = cluster["last_heartbeat"]
            alive = (now - last_hb) <= self.timeout

            cluster_status[cid] = {
                "start_shard": cluster["start_shard"],
                "end_shard": cluster["end_shard"],
                "last_heartbeat": last_hb.isoformat(),
                "seconds_since_heartbeat": (now - last_hb).total_seconds(),
                "alive": alive,
                "users": cluster_users,
                "guilds": cluster_guilds,
                "shards": shards,
            }

        return web.json_response(
            {"users": total_users, "guilds": total_guilds, "clusters": cluster_status}
        )

    async def restart_cluster(self, cid: int, info: Dict[str, Any]) -> None:
        logger.warning(
            f"Cluster {cid} missed heartbeat for over {self.timeout}. Restarting."
        )
        proc = info["process"]
        with suppress(ProcessLookupError):
            proc.terminate()
            await proc.wait()

        info["log_file"].close()

        process, log_file = await self.start_cluster_process(
            cid, info["start_shard"], info["end_shard"]
        )

        info.update(
            {
                "process": process,
                "last_heartbeat": datetime.now(),
                "log_file": log_file,
            }
        )

        self.shard_info[cid].clear()
        logger.info(f"Relaunched cluster {cid}")

    async def monitor_clusters(self) -> None:
        while True:
            now = datetime.now()
            for cid, info in list(self.clusters.items()):
                if now - info["last_heartbeat"] <= self.timeout:
                    continue

                try:
                    await self.restart_cluster(cid, info)
                except (OSError, IOError) as e:
                    logger.error(f"Error restarting cluster {cid}: {e}")

            await asyncio.sleep(60)

    async def report_status(self) -> None:
        while True:
            now = datetime.now()
            statuses = []

            for cid, info in self.clusters.items():
                last_hb = info["last_heartbeat"]
                alive = (now - last_hb) <= self.timeout
                statuses.append(
                    f"Cluster {cid}: {'alive' if alive else 'down'} - last heartbeat {(now - last_hb).total_seconds():.1f}s ago"
                )

            logger.info("Cluster statuses: " + "; ".join(statuses))
            await asyncio.sleep(30)

    async def start_server(self) -> None:
        app = web.Application()
        app.router.add_post("/heartbeat", self.handle_heartbeat)
        app.router.add_get("/health", self.handle_health)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.heartbeat_host, self.heartbeat_port)
        await site.start()
        logger.info(f"Server running on {self.heartbeat_host}:{self.heartbeat_port}")
        await asyncio.Event().wait()

    async def run(self) -> None:
        await self.launch_clusters()
        asyncio.create_task(self.monitor_clusters())
        asyncio.create_task(self.report_status())
        await self.start_server()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--shards-per-cluster", type=int, required=True)
    parser.add_argument("--num-clusters", type=int, required=True)
    parser.add_argument("--heartbeat-host", type=str, default="0.0.0.0")
    parser.add_argument("--heartbeat-port", type=int, default=8000)
    args = parser.parse_args()
    manager = ClusterManager(
        shards_per_cluster=args.shards_per_cluster,
        num_clusters=args.num_clusters,
        heartbeat_host=args.heartbeat_host,
        heartbeat_port=args.heartbeat_port,
    )
    asyncio.run(manager.run())
