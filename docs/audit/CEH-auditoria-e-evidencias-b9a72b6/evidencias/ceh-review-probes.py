import os, sys, tempfile, subprocess, pathlib, json
repo=pathlib.Path('/mnt/c/Users/atiga/AppData/Local/hermes/cache/scratch/ceh-review-linux')
base=repo.parent
runner=repo/'clearer-engineering/scripts/test-runner.sh'
sys.path.insert(0,str(repo/'clearer-engineering/scripts'))
from ceh_core.engine import Request,evaluate
results=[]
def cmd(args,cwd,env=None):
    return subprocess.run(args,cwd=cwd,env=env,text=True,capture_output=True)
def init(p):
    for args in [['git','init','-b','dev'],['git','config','user.name','Review'],['git','config','user.email','review@example.invalid']]:
        r=cmd(args,p); assert r.returncode==0,r.stderr
    (p/'.github/workflows').mkdir(parents=True)
    (p/'.github/workflows/ci.yml').write_text('name: CI\n')
    (p/'.gitignore').write_text('.ceh/last-ci-run.json\n.ceh/last-ci-run.log\n')
def commit(p):
    assert cmd(['git','add','.'],p).returncode==0
    r=cmd(['git','commit','-m','fixture'],p); assert r.returncode==0,r.stderr
with tempfile.TemporaryDirectory(prefix='ceh-review-pytest-',dir=base) as t:
    p=pathlib.Path(t);init(p)
    (p/'pytest.ini').write_text('[pytest]\n')
    (p/'test_smoke.py').write_text('import unittest\nclass Smoke(unittest.TestCase):\n    def test_smoke(self):\n        self.assertTrue(True)\n')
    (p/'tests').mkdir(); (p/'tests/test_fails.py').write_text('def test_fails():\n    assert False, "THIS TEST MUST FAIL"\n')
    commit(p)
    e=os.environ.copy();e['PATH']='/usr/bin:/bin';e['HOME']=str(p);e['TMPDIR']=str(base)
    r=cmd(['bash',str(runner)],p,e)
    cert=json.loads((p/'.ceh/last-ci-run.json').read_text()) if (p/'.ceh/last-ci-run.json').exists() else None
    gate=evaluate(Request(command='git push origin dev',cwd=p,explicit_env='development'))
    results.append({'probe':'pytest_fallback','exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'certificate':cert,'gate':vars(gate)})
with tempfile.TemporaryDirectory(prefix='ceh-review-post-test-',dir=base) as t:
    p=pathlib.Path(t);init(p)
    (p/'.ceh').mkdir();(p/'.ceh/config.json').write_text(json.dumps({'canonical_test_command':'bash tests.sh'}))
    (p/'source.txt').write_text('COMMITTED\n')
    (p/'tests.sh').write_text('printf "GENERATED CHANGE\\n" > source.txt\ngrep -qx "GENERATED CHANGE" source.txt\nprintf "PASS assertion evaluated generated source\\n"\n')
    commit(p)
    r=cmd(['bash',str(runner)],p)
    cert=json.loads((p/'.ceh/last-ci-run.json').read_text()) if (p/'.ceh/last-ci-run.json').exists() else None
    gate=evaluate(Request(command='git push origin dev',cwd=p,explicit_env='development'))
    results.append({'probe':'post_test_dirty','exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'certificate':cert,'git_status':cmd(['git','status','--porcelain'],p).stdout,'gate':vars(gate)})
with tempfile.TemporaryDirectory(prefix='ceh-review-runtime-',dir=base) as t:
    p=pathlib.Path(t);init(p)
    (p/'.ceh').mkdir();(p/'.ceh/config.json').write_text(json.dumps({'canonical_test_command':'bash canonical.sh'}))
    (p/'canonical.sh').write_text('printf "Canonical suite MUST FAIL\\n"\nexit 9\n')
    (p/'compose.yaml').write_text('services: {}\n')
    (p/'vendor/bin').mkdir(parents=True);(p/'vendor/bin/sail').write_text('#!/bin/sh\nprintf "DIFFERENT Sail test command passed\\n"\nexit 0\n');(p/'vendor/bin/sail').chmod(0o755)
    commit(p)
    b=p/'mock-bin';b.mkdir();docker=b/'docker';docker.write_text('#!/bin/sh\nif [ "$1" = "info" ]; then exit 0; fi\nif [ "$1" = "compose" ] && [ "$2" = "ps" ]; then printf "laravel.test\\n"; exit 0; fi\nexit 1\n');docker.chmod(0o755)
    (p/'.gitignore').write_text((p/'.gitignore').read_text()+'mock-bin/\n');commit(p)
    e=os.environ.copy();e['PATH']=str(b)+':/usr/bin:/bin';e['HOME']=str(p);e['TMPDIR']=str(base)
    r=cmd(['bash',str(runner)],p,e)
    cert=json.loads((p/'.ceh/last-ci-run.json').read_text()) if (p/'.ceh/last-ci-run.json').exists() else None
    gate=evaluate(Request(command='git push origin dev',cwd=p,explicit_env='development'))
    canonical_direct=cmd(['bash','canonical.sh'],p)
    results.append({'probe':'runtime_replaces_canonical','exit':r.returncode,'canonical_direct_exit':canonical_direct.returncode,'stdout':r.stdout,'stderr':r.stderr,'certificate':cert,'gate':vars(gate)})
(base/'ceh-review-probes.json').write_text(json.dumps(results,indent=2,ensure_ascii=False))
for x in results: print(json.dumps(x,ensure_ascii=False,indent=2))
