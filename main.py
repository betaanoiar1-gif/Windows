import argparse
from smartpc.ui import run
from smartpc.engine import Engine

def main():
    p=argparse.ArgumentParser(); p.add_argument("--background",action="store_true"); args=p.parse_args()
    if args.background:
        # Startup task is observation-only until the AI/safety policy is explicitly configured.
        Engine().inspect(); return 0
    return run()

if __name__ == "__main__":
    raise SystemExit(main())
