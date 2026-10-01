import os,sys,json,pathlib,subprocess,time
p=pathlib.Path('/mnt/c/Users/atiga/AppData/Local/hermes/cache/scratch/ceh-review-evals')
base=p.parent
env=os.environ.copy();env['TMPDIR']=str(base);env['PYTHONDONTWRITEBYTECODE']='1'
results=[]
for name,args in [('evals',['bash','evals/run.sh']),('adversarial',['bash','clearer-engineering/tests/run-adversarial-tests.sh']),('doc-audit',['bash','clearer-engineering/scripts/doc-audit.sh'])]:
    start=time.time()
    with (base/f'ceh-review-verified-{name}.log').open('w') as f:
        r=subprocess.run(args,cwd=p,env=env,stdout=f,stderr=subprocess.STDOUT)
    row={'name':name,'exit_code':r.returncode,'seconds':round(time.time()-start,2)};results.append(row);print(json.dumps(row),flush=True)
    (base/'ceh-review-verification-results.json').write_text(json.dumps(results,indent=2))
print('GIT_STATUS',subprocess.check_output(['git','status','--porcelain'],cwd=p,text=True))
