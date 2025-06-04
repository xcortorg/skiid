import argparse
from loguru import logger
from rival.server import Server


def run():
    """Module entry point"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-host",
        "--host",
        nargs="?",
        help="the host for rival server",
        default="127.0.0.1",
    )

    parser.add_argument(
        "-p", "--port", nargs="?", help="The port for rival server", default=13254
    )

    parser.add_argument(
        "--version", action="store_true", help="logger.info the version"
    )
    args = parser.parse_args()

    # Setup config from arguments
    port = args.port
    try:
        port = int(port)
    except:
        raise ValueError("port should be an integer between range 1-65535")
    host = args.host
    if args.version:
        logger.info("rival version: unknown")
    else:
        logger.info("Starting server at port: ", port)
        server = Server(host=host, port=port)
        server.start()


if __name__ == "__main__":
    run()
