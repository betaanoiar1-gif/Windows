import argparse
import json

from smartpc.engine import Engine
from smartpc.ui import run
from smartpc.windows import install_startup_task, maintenance_status, remove_startup_task, startup_status


def _dump(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def main():
    p = argparse.ArgumentParser(description="SMARTPC AI — safety-first autonomous Windows optimization")
    p.add_argument("--background", action="store_true", help="run one autonomous maintenance cycle")
    p.add_argument("--observe-only", action="store_true", help="run read-only background observation")
    p.add_argument("--inspect", action="store_true", help="inspect system and network evidence")
    p.add_argument("--deep-disk-scan", action="store_true", help="deep C: drive reclaimable-data inventory; no changes")
    p.add_argument("--network", action="store_true", help="inspect network health")
    p.add_argument("--network-plan", action="store_true", help="diagnose network and show a safe recovery plan")
    p.add_argument("--network-repair", choices=["flush_dns", "renew_dhcp", "reset_winsock", "reset_tcpip"], help="run one explicit network repair and verify it")
    p.add_argument("--confirm", action="store_true", help="explicitly authorize medium-risk network repair")
    p.add_argument("--no-ai", action="store_true", help="disable the optional AI advisory request")
    p.add_argument("--no-network-probes", action="store_true", help="skip external DNS/HTTPS/ping probes")
    p.add_argument("--optimize-safe", action="store_true", help="quarantine locally-authorized temporary files")
    p.add_argument("--restore", metavar="TOKEN", help="restore a quarantined file")
    p.add_argument("--install-startup", action="store_true")
    p.add_argument("--remove-startup", action="store_true")
    p.add_argument("--startup-status", action="store_true")
    args = p.parse_args()

    # Read-only observation must win if both flags are supplied. The startup
    # task intentionally includes --observe-only and must never mutate files.
    if args.observe_only:
        Engine().inspect(include_ai=False, network_probes=False)
        return 0
    if args.background:
        result = Engine().autonomous_maintenance()
        _dump({
            "mode": result["mode"],
            "pressure_before": result["pressure_before"],
            "prediction": result["prediction"],
            "pressure_after": result["pressure_after"],
            "triggered": result["triggered"],
            "quarantined": len(result["moved"]),
            "skipped_reason": result["skipped_reason"],
        })
        return 0
    if args.install_startup:
        install_startup_task()
        print("SMARTPC AI autonomous startup + maintenance tasks installed.")
        return 0
    if args.remove_startup:
        results = remove_startup_task()
        print("SMARTPC AI startup + maintenance tasks removed/requested.")
        return 0 if results is None or all(r is None or r.returncode == 0 for r in results) else 2
    if args.startup_status:
        print(json.dumps({"observation": startup_status(), "maintenance": maintenance_status()}))
        return 0

    engine = Engine()
    probes = not args.no_network_probes
    if args.restore:
        print(engine.restore(args.restore))
        return 0
    if args.deep_disk_scan:
        r = engine.deep_disk_scan()
        _dump({"summary": r["summary"], "top_candidates": [c.to_dict() for c in r["candidates"][:100]]})
        return 0
    if args.network_repair:
        result = engine.network_repair(args.network_repair, confirm_medium=args.confirm, verify=probes)
        _dump(result)
        return 0 if result["result"].get("ok") else 2
    if args.network_plan:
        r = engine.network_inspect(probes=probes)
        _dump({"health": r["health"].to_dict(), "connectivity": r["connectivity"].to_dict() if r["connectivity"] else None, "advanced": r["advanced"], "diagnoses": r["diagnoses"], "recommended_repairs": r["recommended_repairs"], "recovery_plan": r["recovery_plan"]})
        return 0
    if args.network:
        r = engine.network_inspect(probes=probes)
        _dump({"network": r["network"].to_dict(), "health": r["health"].to_dict(), "connectivity": r["connectivity"].to_dict() if r["connectivity"] else None, "advanced": r["advanced"], "diagnoses": r["diagnoses"], "recommended_repairs": r["recommended_repairs"], "recovery_plan": r["recovery_plan"]})
        return 0
    if args.inspect:
        r = engine.inspect(include_ai=not args.no_ai, network_probes=probes)
        _dump({"system": r["snapshot"].to_dict(), "health_score": r["health_score"], "baseline": r["baseline"], "diagnoses": [d.to_dict() for d in r["diagnoses"]], "candidate_count": len(r["candidates"]), "disk_cleanup": r["disk_cleanup"], "network": r["network"].to_dict(), "network_health": r["network_health"].to_dict(), "network_connectivity": r["network_connectivity"].to_dict() if r["network_connectivity"] else None, "network_advanced": r["network_advanced"], "network_diagnoses": r["network_diagnoses"], "network_recommended_repairs": r["network_recommended_repairs"], "ai": r["ai"]})
        return 0
    if args.optimize_safe:
        r = engine.optimize_safe()
        _dump({"quarantined": len(r["moved"]), "before": r["before"].to_dict(), "after": r["after"].to_dict()})
        return 0
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
