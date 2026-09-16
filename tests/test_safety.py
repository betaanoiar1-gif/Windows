from smartpc.models import Candidate,Action
from smartpc.safety import authorize

def test_windows_path_blocked():
    c=Candidate(r"C:\Windows\System32\kernel32.dll","temporary",10,100,action=Action.QUARANTINE)
    x=authorize(c,True)
    assert x.action==Action.KEEP

def test_temp_is_quarantine_in_auto():
    c=Candidate(r"C:\Users\test\AppData\Local\Temp\x.tmp","temporary",10,2)
    x=authorize(c,True)
    assert x.action==Action.QUARANTINE
