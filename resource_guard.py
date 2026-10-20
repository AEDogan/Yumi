"""Windows commit reserve and hard limits for Yumi-owned processes only."""
import ctypes,os
from ctypes import wintypes as w
GiB=1024**3
class Performance(ctypes.Structure):
    _fields_=[('cb',w.DWORD)]+[(n,ctypes.c_size_t) for n in ['CommitTotal','CommitLimit','CommitPeak','PhysicalTotal','PhysicalAvailable','SystemCache','KernelTotal','KernelPaged','KernelNonpaged','PageSize']]+[(n,w.DWORD) for n in ['HandleCount','ProcessCount','ThreadCount']]
class Basic(ctypes.Structure):
    _fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),('LimitFlags',w.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',w.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',w.DWORD),('SchedulingClass',w.DWORD)]
class IO(ctypes.Structure):
    _fields_=[(n,ctypes.c_ulonglong) for n in ['ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount']]
class Extended(ctypes.Structure):
    _fields_=[('BasicLimitInformation',Basic),('IoInfo',IO)]+[(n,ctypes.c_size_t) for n in ['ProcessMemoryLimit','JobMemoryLimit','PeakProcessMemoryUsed','PeakJobMemoryUsed']]
def memory_status():
    if os.name!='nt':raise RuntimeError('Bellek koruması bu sistemde doğrulanmadı.')
    p=Performance();p.cb=ctypes.sizeof(p)
    if not ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(p),p.cb):raise ctypes.WinError()
    return {'commit_free':(p.CommitLimit-p.CommitTotal)*p.PageSize,'commit_limit':p.CommitLimit*p.PageSize,'physical_free':p.PhysicalAvailable*p.PageSize}
def pressure(status=None,extra_bytes=0):
    s=memory_status() if status is None else status
    reserve=max(12*GiB,int(s['commit_limit']*.15))
    return s['commit_free']-extra_bytes<reserve or s['physical_free']-extra_bytes<4*GiB
def require_capacity(extra_bytes=0):
    if pressure(extra_bytes=extra_bytes):raise RuntimeError('Diğer programlara bellek bırakmak için bu işlem başlatılmadı. Kullanılabilir bellek azaldı; Gemini metin sohbetini kullanabilirsin.')
class MemoryJob:
    def __init__(self,total_bytes=6*GiB,process_bytes=4*GiB):
        if os.name!='nt':raise RuntimeError('Yerel bellek sınırı bu sistemde doğrulanmadı.')
        k=ctypes.WinDLL('kernel32',use_last_error=True);self.k=k
        k.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR];k.CreateJobObjectW.restype=w.HANDLE
        k.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD];k.SetInformationJobObject.restype=w.BOOL
        k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE];k.AssignProcessToJobObject.restype=w.BOOL
        k.GetCurrentProcess.restype=w.HANDLE
        k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
        k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
        self.handle=k.CreateJobObjectW(None,None)
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
        info=Extended();info.BasicLimitInformation.LimitFlags=0x100|0x200|0x2000|0x400
        info.ProcessMemoryLimit=process_bytes;info.JobMemoryLimit=total_bytes
        if not k.SetInformationJobObject(self.handle,9,ctypes.byref(info),ctypes.sizeof(info)):
            error=ctypes.get_last_error();self.close();raise ctypes.WinError(error)
    def attach(self,pid=None):
        process=self.k.GetCurrentProcess() if pid is None else self.k.OpenProcess(0x100|0x1,False,pid)
        if not process:raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not self.k.AssignProcessToJobObject(self.handle,process):raise ctypes.WinError(ctypes.get_last_error())
        finally:
            if pid is not None:self.k.CloseHandle(process)
    def close(self):
        if self.handle:self.k.CloseHandle(self.handle);self.handle=None
