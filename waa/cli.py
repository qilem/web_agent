import argparse
from pathlib import Path

from .agent import Agent


def main():
    argparser = argparse.ArgumentParser(
        prog="waa",
        description="Web-App Agent - An LLM-powered agent for building web applications"
    )
    argparser.add_argument(
        "-w",
        "--working-dir",
        type=str,
        default=".",
        help="Working directory containing .waa configuration"
    )
    argparser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    args = argparser.parse_args()

    working_dir = Path(args.working_dir)
    agent = Agent(working_dir, debug=args.debug)
    agent.run()


if __name__ == "__main__":
    main()
