"""Linux execution containment applied by the trusted C harness before calling f.
No network, exec, process creation, ptrace, or opening files is permitted afterwards.
This is defense in depth, not a promise of security against every native-code attack.
"""
C_SETUP = r'''
#include <seccomp.h>
#include <unistd.h>
#include <stdlib.h>
static void irsem_sandbox(void) {
    scmp_filter_ctx ctx=seccomp_init(SCMP_ACT_KILL_PROCESS);
    if(!ctx) _exit(120);
    const char *names[]={"read","write","close","brk","mmap","mprotect","munmap","madvise",
        "fstat","newfstatat","lseek","rt_sigaction","rt_sigprocmask","rt_sigreturn",
        "futex","clock_gettime","getpid","gettid","getrandom","exit","exit_group"};
    for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);i++) {
        int n=seccomp_syscall_resolve_name(names[i]);
        if(n>=0 && seccomp_rule_add(ctx,SCMP_ACT_ALLOW,n,0)<0) _exit(121);
    }
    if(seccomp_load(ctx)<0) _exit(122);
    seccomp_release(ctx);
}
'''


def probe(clang):
    import tempfile,signal
    from pathlib import Path
    from .common import run_process
    with tempfile.TemporaryDirectory(prefix='irsem-sandbox-') as tmp:
        p=Path(tmp); src=p/'probe.c'; exe=p/'probe'
        src.write_text(C_SETUP+'\n#include <sys/socket.h>\nint main(void){irsem_sandbox();return socket(AF_INET,SOCK_STREAM,0);}\n')
        build=run_process([clang,str(src),'-lseccomp','-o',str(exe)],60)
        if build.returncode!=0: return {'passed':False,'build':build.as_dict()}
        result=run_process([str(exe)],5)
        return {'passed':result.returncode==-signal.SIGSYS,'network_syscall_blocked':result.returncode==-signal.SIGSYS,
                'result':result.as_dict()}
