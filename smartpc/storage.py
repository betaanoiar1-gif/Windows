import hashlib
import os
import shutil
import tempfile
import time
from pathlib import Path
from .models import Candidate, Action, Risk

SAFE_DIR_NAMES={"Temp","tmp","Cache","cache"}

def _age_days(path: Path)->float:
    try:return max(0,(time.time()-path.stat().st_mtime)/86400)
    except OSError:return 0

def scan_temp() -> list[Candidate]:
    roots={Path(tempfile.gettempdir())}
    local=os.environ.get("LOCALAPPDATA")
    if local: roots.add(Path(local)/"Temp")
    out=[]; seen=set()
    for root in roots:
        if not root.exists(): continue
        try:
            for p in root.rglob("*"):
                try:
                    if not p.is_file() or p in seen: continue
                    seen.add(p); s=p.stat().st_size
                    out.append(Candidate(str(p),"temporary",s,_age_days(p),Risk.SAFE,Action.QUARANTINE,"Temporary-directory file",True))
                except (OSError,PermissionError): pass
        except (OSError,PermissionError): pass
    return out

def hash_file(path: Path, chunk=1024*1024):
    h=hashlib.sha256()
    with path.open("rb") as f:
        while b:=f.read(chunk): h.update(b)
    return h.hexdigest()

def safe_quarantine(candidates, quarantine: Path, limit=5000):
    quarantine.mkdir(parents=True,exist_ok=True); moved=[]
    for c in candidates[:limit]:
        src=Path(c.target)
        if c.action!=Action.QUARANTINE or not src.is_file(): continue
        try:
            dest=quarantine/(hashlib.sha1(str(src).encode()).hexdigest()+"_"+src.name)
            shutil.move(str(src),str(dest)); moved.append((str(src),str(dest)))
        except (OSError,PermissionError): pass
    return moved
