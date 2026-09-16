from .models import Diagnosis, SystemSnapshot


def health_score(snapshot: SystemSnapshot, diagnoses: list[Diagnosis]) -> int:
    score = 100
    penalties = {"safe": 0, "low": 5, "medium": 12, "high": 25, "critical": 50}
    for d in diagnoses:
        score -= penalties.get(d.severity.value, 10)
    if snapshot.disk_percent >= 95: score -= 15
    elif snapshot.disk_percent >= 90: score -= 8
    if snapshot.ram_percent >= 95: score -= 10
    return max(0, min(100, score))
