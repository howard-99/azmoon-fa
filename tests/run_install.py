#!/usr/bin/env python3
"""Interactive installer integration harness; only on disposable CI Ubuntu runners."""
import os, pty, select, sys, time
if os.environ.get('CI') != 'true' or os.geteuid() != 0:
    sys.exit('Only a disposable CI runner may execute this harness.')
prompts = [
 ('نام کوتاه مؤسسه:', 'DEMO'), ('نام کامل مؤسسه:', 'آموزشگاه نمونه'),
 ('آدرس سامانه با', 'http://127.0.0.1:8098'), ('شبکه مجاز', '127.0.0.0/8'),
 ('نام کاربری مدیر', 'manager'), ('رمز مدیر (', 'Test-Admin-Only-123!'),
 ('تکرار رمز مدیر:', 'Test-Admin-Only-123!'), ('شروع نصب؟', 'y'),
]
pid, fd = pty.fork()
if pid == 0:
    os.execvp('bash', ['bash', 'install.sh'])
position = 0; pending = ''; deadline = time.monotonic() + 1800
while time.monotonic() < deadline:
    ready, _, _ = select.select([fd], [], [], 1)
    if ready:
        try: chunk = os.read(fd, 65536)
        except OSError: break
        if not chunk: break
        sys.stdout.buffer.write(chunk); sys.stdout.buffer.flush()
        pending += chunk.decode('utf-8', errors='replace')
        if position < len(prompts) and prompts[position][0] in pending:
            os.write(fd, (prompts[position][1]+'\n').encode('utf-8'))
            position += 1; pending = ''
else:
    os.kill(pid, 15); sys.exit('Installer timed out')
_, status = os.waitpid(pid, 0)
if position != len(prompts): sys.exit('Installer stopped before all prompts')
sys.exit(os.waitstatus_to_exitcode(status))
