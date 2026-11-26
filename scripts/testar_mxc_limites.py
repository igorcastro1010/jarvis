"""Teste restrito MXC: dados falsos e listener local; nenhuma credencial real."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jarvis.codex_profile import build_profile

with tempfile.TemporaryDirectory(prefix='jarvis-mxc-limites-') as tmp:
    root=Path(tmp); work=root/'projeto'; work.mkdir(); private=root/'privado'; private.mkdir()
    target=private/'auth.json'; target.write_text('credencial-ficticia',encoding='utf8')
    (work/'dentro.txt').write_text('ok',encoding='utf8')
    hardlink=work/'atalho-hardlink.json'
    try: hardlink.hardlink_to(target); hardlink_created=True
    except OSError: hardlink_created=False
    runner = '''import json,pathlib,socket,sys\nroot=pathlib.Path(sys.argv[1]); work=pathlib.Path.cwd(); r={}\ndef blocked_read(path):\n try: path.read_text(); return False\n except OSError: return True\ndef blocked_write(path):\n try: path.write_text('mudado'); return False\n except OSError: return True\nr["leitura_credencial_ficticia_negada"]=blocked_read(root/"privado"/"auth.json")\nr["leitura_indireta_negada"]=blocked_read(work/".."/"privado"/"auth.json")\nr["escrita_externa_negada"]=blocked_write(root/"privado"/"novo.txt")\nr["escrita_credencial_negada"]=blocked_write(root/"privado"/"auth.json")\nr["hardlink_negado"]=blocked_read(work/"atalho-hardlink.json") if sys.argv[3]=="1" else None\ns=socket.socket(); s.settimeout(2)\ntry: r["loopback_negado"]=s.connect_ex(("127.0.0.1",int(sys.argv[2])))!=0\nfinally: s.close()\nprint(json.dumps(r),flush=True)\n'''
    (work/'verificar.py').write_text(runner,encoding='utf8')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0)); listener.listen(1)
        py=Path(sys._base_executable); profile=build_profile(work,py.parent,writable=True)
        cmd=['codex','sandbox','-c','windows.sandbox=mxc','-c',profile,'-c','permissions.jarvis.network.enabled=false',
             '--include-managed-config','-P','jarvis','-C',str(work),str(py),str(work/'verificar.py'),str(root),str(listener.getsockname()[1]),'1' if hardlink_created else '0']
        result=subprocess.run(cmd,cwd=work,capture_output=True,text=True,timeout=30)
    if result.returncode:
        print('sandbox recusou:',result.stderr.strip()); raise SystemExit(result.returncode)
    checks=json.loads(result.stdout)
    checks['credencial_ficticia_preservada']=target.read_text(encoding='utf8')=='credencial-ficticia'
    checks['arquivo_externo_nao_criado']=not (private/'novo.txt').exists()
    print(json.dumps(checks,ensure_ascii=False))
    if not all(value is True for value in checks.values()): raise SystemExit('Isolamento incompleto ou não comprovado')
