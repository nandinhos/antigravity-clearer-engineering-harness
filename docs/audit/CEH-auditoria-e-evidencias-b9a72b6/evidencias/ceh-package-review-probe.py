import os, sys, json, tempfile, subprocess, importlib.util
from pathlib import Path
sys.dont_write_bytecode = True
repo=Path('C:/Users/atiga/AppData/Local/hermes/cache/scratch/ceh-review-20260930')
root=Path(tempfile.mkdtemp(prefix='ceh-pack-review-', dir='C:/Users/atiga/AppData/Local/hermes/cache/scratch'))
print('SCRATCH', root)
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
rc=load('rc',repo/'clearer-engineering/scripts/rc_aliases.py')
pkg=load('pkg',repo/'clearer-engineering/tools/package.py')
conf=repo/'clearer-engineering/config/aliases.sh'
body='\n'.join(x for x in conf.read_text(encoding='utf-8').splitlines() if x.startswith('alias '))
# CLI only operates on disposable output directory.
out=root/'owned-output';out.mkdir();(out/'user-sentinel.txt').write_text('preserve me')
p=subprocess.run([sys.executable,str(repo/'clearer-engineering/tools/package.py'),'--all','--out',str(root/'all'),'--json'],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
print('ALL',p.returncode,p.stdout,p.stderr)
p=subprocess.run([sys.executable,str(repo/'clearer-engineering/tools/package.py'),'--host','muse','--out',str(out),'--json'],capture_output=True,text=True)
print('DESTRUCTIVE_OUT',p.returncode,'sentinel_exists', (out/'user-sentinel.txt').exists())
print('VERSIONS', json.loads((root/'all/antigravity/plugin.json').read_text())['version'],json.loads((root/'all/muse/manifest.json').read_text())['version'])
print('ANTIGRAVITY_EVAL_ALIAS_TARGET_EXISTS', (root/'all/antigravity/evals/run.sh').exists())
# Compare repeat content determinism via direct functions writing only scratch.
out2=root/'muse2';h2,n2=pkg.package_host('muse',out2)
print('REPEAT_MUSE_HASH_EQUAL',pkg.calculate_package_hash(out)[0]==h2,'count',n2)
# Marker matching in strings erases a real user config line.
embedded=f'echo "{rc.START_MARKER}"\nexport USER_SETTING=keep\necho "{rc.END_MARKER}"\n'
print('EMBEDDED_MARKER_CLEAN',repr(rc.clean_rc_content(embedded,str(conf))))
# Two valid managed blocks: installer retains both; cleaner removes only first.
block=rc.install_rc_content('',str(conf),body)
duplicated=block+block
updated=rc.install_rc_content(duplicated,str(conf),body)
cleaned=rc.clean_rc_content(updated,str(conf))
print('DUPLICATE_BLOCKS_INSTALL',updated.count(rc.START_MARKER),'CLEAN',cleaned.count(rc.START_MARKER))
# Real CLI rc round trip on Windows.
rcpath=root/'sample.bashrc';original=b'export USER_SETTING=keep\n'
rcpath.write_bytes(original)
for action,args in [('install-rc',[body]),('clean-rc',[])]:
    p=subprocess.run([sys.executable,str(repo/'clearer-engineering/scripts/rc_aliases.py'),action,str(rcpath),str(conf),*args],capture_output=True,text=True)
    print('RC_CLI',action,p.returncode,p.stderr)
print('RC_ROUNDTRIP_BYTES',repr(original),repr(rcpath.read_bytes()),original==rcpath.read_bytes())
# Test clean package commands without invoking a host/LLM.
settings=json.loads((root/'all/claude-code/.claude/settings.json').read_text())
cmd=settings['hooks']['PreToolUse'][0]['hooks'][0]['command']
print('CLAUDE_COMMAND',cmd,'exists_at_project_cwd',(root/'fresh-project/scripts/safety-gate.py').exists())
print('REPO_STATUS',subprocess.run(['git','-C',str(repo),'status','--short'],capture_output=True,text=True).stdout)
