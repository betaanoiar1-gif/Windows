import argparse
import json
from smartpc.engine import Engine
from smartpc.ui import run
from smartpc.windows import install_startup_task, remove_startup_task, startup_status


def main():
    p = argparse.ArgumentParser(description="SMARTPC AI — safety-first Windows optimization")
    p.add_argument("--background", action="store_true", help="observe only; no cleanup")
    p.add_argument("--inspect", action="store_true")
    p.add_argument("--optimize-safe", action="store_true")
    p.add_argument("--restore", metavar="TOKEN")
    p.add_argument("--install-startup", action="store_true")
    p.add_argument("--remove-startup", action="store_true")
    p.add_argument("--startup-status", action="store_true")
    args = p.parse_args()
    if args.background:
        Engine().inspect(include_ai=False)
        return 0
    if args.install_startup:
        install_startup_task(); print("Startup task installed."); return 0
    if args.remove_startup:
        remove_startup_task(); print("Startup task removal requested."); return 0
    if args.startup_status:
        print("installed" if startup_status() else "not-installed"); return 0
    engine = Engine()
    if args.restore:
        print(engine.restore(args.restore)); return 0
    if args.inspect:
        r = engine.inspect()
        print(json.dumps({"system": r["snapshot"].to_dict(), "diagnoses": [d.to_dict() for d in r["diagnoses"]], "candidate_count": len(r["candidates"]), "ai": r["ai"]}, ensure_ascii=False, indent=2))
        return 0
    if args.optimize_safe:
        r = engine.optimize_safe()
        print(json.dumps({"quarantined": len(r["moved"]), "before": r["before"].to_dict(), "after": r["after"].to_dict()}, indent=2))
        return 0
    return run()

if __name__ == "__main__":
    raise SystemExit(main())
