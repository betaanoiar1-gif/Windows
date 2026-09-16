import argparse
import json
from smartpc.engine import Engine
from smartpc.ui import run
from smartpc.windows import install_startup_task, remove_startup_task, startup_status


def main():
    p = argparse.ArgumentParser(description="SMARTPC AI — safety-first Windows optimization")
    p.add_argument("--background", action="store_true", help="observe only; no cleanup or network repair")
    p.add_argument("--inspect", action="store_true")
    p.add_argument("--network", action="store_true", help="inspect network health with real probes")
    p.add_argument("--network-plan", action="store_true", help="diagnose network and build a safe recovery plan")
    p.add_argument("--network-repair", choices=["flush_dns", "renew_dhcp", "reset_winsock", "reset_tcpip"], help="run one explicit network repair and verify it")
    p.add_argument("--optimize-safe", action="store_true")
    p.add_argument("--restore", metavar="TOKEN")
    p.add_argument("--install-startup", action="store_true")
    p.add_argument("--remove-startup", action="store_true")
    p.add_argument("--startup-status", action="store_true")
    args = p.parse_args()
    if args.background:
        Engine().inspect(include_ai=False, network_probes=False)
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
    if args.network_repair:
        print(json.dumps(engine.network_repair(args.network_repair), ensure_ascii=False, indent=2, default=str)); return 0
    if args.network_plan:
        from smartpc.network_recovery import diagnose_and_plan
        print(json.dumps(diagnose_and_plan(), ensure_ascii=False, indent=2)); return 0
    if args.network:
        r = engine.network_inspect()
        print(json.dumps({"network": r["network"].to_dict(), "diagnoses": r["diagnoses"], "recommended_repairs": r["recommended_repairs"]}, ensure_ascii=False, indent=2)); return 0
    if args.inspect:
        r = engine.inspect()
        print(json.dumps({"system": r["snapshot"].to_dict(), "diagnoses": [d.to_dict() for d in r["diagnoses"]], "candidate_count": len(r["candidates"]), "network": r["network"].to_dict(), "network_diagnoses": r["network_diagnoses"], "network_recommended_repairs": r["network_recommended_repairs"], "ai": r["ai"]}, ensure_ascii=False, indent=2))
        return 0
    if args.optimize_safe:
        r = engine.optimize_safe()
        print(json.dumps({"quarantined": len(r["moved"]), "before": r["before"].to_dict(), "after": r["after"].to_dict()}, indent=2))
        return 0
    return run()

if __name__ == "__main__":
    raise SystemExit(main())
