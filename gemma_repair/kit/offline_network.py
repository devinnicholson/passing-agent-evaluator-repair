import ctypes
import errno
import os
import platform

def disable_child_network():
    # Linux amd64 seccomp_data fields. AF_UNIX remains available for local IPC.
    if platform.machine() != "x86_64":
        raise RuntimeError("the egress filter requires Linux amd64")

    class Rule(ctypes.Structure):
        _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte),
                    ("jf", ctypes.c_ubyte), ("value", ctypes.c_uint32)]

    class Program(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ushort), ("rules", ctypes.POINTER(Rule))]

    deny = 0x00050000 | errno.EPERM
    rows = (Rule * 12)(
        Rule(0x20, 0, 0, 4),            # seccomp_data.arch
        Rule(0x15, 1, 0, 0xC000003E),   # AUDIT_ARCH_X86_64
        Rule(0x06, 0, 0, 0x80000000),   # kill unexpected ABI
        Rule(0x20, 0, 0, 0),            # seccomp_data.nr
        Rule(0x35, 4, 0, 0x40000000),   # reject x32 syscall numbers
        Rule(0x15, 3, 0, 425),          # reject io_uring_setup
        Rule(0x15, 0, 3, 41),           # socket syscall
        Rule(0x20, 0, 0, 16),           # seccomp_data.args[0]
        Rule(0x15, 2, 0, 1),            # AF_UNIX
        Rule(0x06, 0, 0, deny),
        Rule(0x06, 0, 0, 0x7FFF0000),   # allow other syscalls
        Rule(0x06, 0, 0, 0x7FFF0000),   # allow AF_UNIX
    )
    policy = Program(len(rows), rows)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0 or libc.prctl(22, 2, ctypes.byref(policy), 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "seccomp activation failed")
    for family in (2, 10):  # AF_INET and AF_INET6
        descriptor = libc.socket(family, 1, 0)
        if descriptor >= 0:
            os.close(descriptor)
            raise RuntimeError("the egress filter admitted an Internet socket")
        if ctypes.get_errno() != errno.EPERM:
            raise RuntimeError("the egress filter was not independently confirmed")
