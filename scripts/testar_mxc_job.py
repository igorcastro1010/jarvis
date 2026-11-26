"""Canário manual: apenas arquivos e processos temporários fictícios, sem inferência."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jarvis.codex_profile import build_profile

with tempfile.TemporaryDirectory(prefix='jarvis-mxc-') as tmp:
    root = Path(tmp); work = root/'projeto'; work.mkdir()
    outside = root/'fora.txt'; outside.write_text('teste', encoding='utf8')
    (work/'dentro.txt').write_text('teste', encoding='utf8')
    shutil.copy(ROOT/'jarvis/windows_job.py', work/'windows_job.py')
    (work/'prova.py').write_text('''import json,pathlib,subprocess,sys\nfrom windows_job import JobProcess\nr={}\nr["inside"]=pathlib.Path("dentro.txt").read_text()=="teste"\npathlib.Path("criado.txt").write_text("ok")\nr["write"]=pathlib.Path("criado.txt").read_text()=="ok"\ntry:\n pathlib.Path(sys.argv[1]).read_text(); r["outside_denied"]=False\nexcept OSError: r["outside_denied"]=True\nchild="import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); print(p.pid,flush=True); time.sleep(30)"\nparent="import subprocess,sys; p=subprocess.Popen([sys.executable,'-u','-c',%r]); print(p.pid,flush=True)" % child\nj=JobProcess.start([sys.executable,'-u','-c',parent],stdout=subprocess.PIPE,stderr=subprocess.PIPE)\ntry:\n child_pid=int(j.process.stdout.readline()); grandchild_pid=int(j.process.stdout.readline())\n j.process.wait(timeout=10)\n r["parent_exited"]=j.process.returncode==0\n r["descendants_in_job"]=child_pid>0 and grandchild_pid>0 and j.active_processes()>=2\n r["job_stopped"]=j.terminate() and j.active_processes()==0\nfinally:\n j.close(); j.process.stdout.close(); j.process.stderr.close()\nprint(json.dumps(r),flush=True)\n''', encoding='utf8')
    py = Path(sys._base_executable)
    profile = build_profile(work, py.parent, writable=True)
    cmd = ['codex','sandbox','-c','windows.sandbox=mxc','-c',profile,'--include-managed-config',
           '-P','jarvis','-C',str(work),str(py),str(work/'prova.py'),str(outside)]
    try:
        result = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        raise SystemExit('Sandbox excedeu o prazo; validação inconclusiva')
    if result.returncode:
        print('Sandbox recusou iniciar:', result.stderr.strip())
        raise SystemExit(result.returncode)
    try: checks = json.loads(result.stdout)
    except ValueError: raise SystemExit('Resposta inválida do teste no sandbox')
    print(json.dumps(checks, ensure_ascii=False))
    expected = {'inside','write','outside_denied','parent_exited','descendants_in_job','job_stopped'}
    if set(checks) != expected or not all(value is True for value in checks.values()):
        raise SystemExit('Validação incompleta ou falhou')
