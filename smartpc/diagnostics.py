import os, platform, psutil

def report():
    root=os.environ.get("SystemDrive","C:")+"\\"
    d=psutil.disk_usage(root)
    return {
      "os":platform.platform(),"python":platform.python_version(),"cpu_logical":psutil.cpu_count(),
      "memory_gb":round(psutil.virtual_memory().total/1024**3,2),"disk_total_gb":round(d.total/1024**3,2),
      "disk_free_gb":round(d.free/1024**3,2),"boot_time":psutil.boot_time()
    }
