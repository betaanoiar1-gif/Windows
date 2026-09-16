import statistics
from .models import SystemSnapshot

class Baseline:
    def __init__(self, snapshots: list[SystemSnapshot]):
        self.snapshots = snapshots

    def summary(self) -> dict:
        if not self.snapshots:
            return {"samples": 0}
        return {
            "samples": len(self.snapshots),
            "cpu_median": round(statistics.median(x.cpu_percent for x in self.snapshots), 2),
            "ram_median": round(statistics.median(x.ram_percent for x in self.snapshots), 2),
            "disk_median": round(statistics.median(x.disk_percent for x in self.snapshots), 2),
            "free_disk_gb_median": round(statistics.median(x.disk_free_gb for x in self.snapshots), 2),
        }

    def deviation(self, current: SystemSnapshot) -> dict:
        s = self.summary()
        if not s.get("samples"):
            return {"cpu": 0.0, "ram": 0.0, "disk": 0.0}
        return {"cpu": current.cpu_percent - s["cpu_median"], "ram": current.ram_percent - s["ram_median"], "disk": current.disk_percent - s["disk_median"]}
