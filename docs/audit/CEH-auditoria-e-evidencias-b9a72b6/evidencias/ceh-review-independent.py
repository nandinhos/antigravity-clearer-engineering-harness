import os,sys,json,pathlib,tempfile,subprocess,importlib.util,shutil
sys.dont_write_bytecode=True
base=pathlib.Path('C:/Users/atiga/AppData/Local/hermes/cache/scratch')
repo=base/'ceh-review-20260930'
sys.path.insert(0,str(repo/'clearer-engineering/scripts'))
from ceh_core.engine import Request,evaluate
from hook_context import handle_hook_lifecycle
results=[]
with tempfile.TemporaryDirectory(prefix='ceh-parent-confirm-',dir=base) as tmp:
    p=pathlib.Path(tmp)
    def git(*args):
        return subprocess.check_output(['git','-C',str(p),*args],text=True,stderr=subprocess.DEVNULL).strip()
    git('init','-b','dev');git('config','user.name','Readonly Review Fixture');git('config','user.email','review@example.invalid')
    (p/'sample.txt').write_text('first\n');git('add','.');git('commit','-m','first');git('branch','unchecked')
    (p/'sample.txt').write_text('second\n');git('add','.');git('commit','-m','second')
    (p/'.github/workflows').mkdir(parents=True);(p/'.github/workflows/ci.yml').write_text('name: CI\n')
    (p/'customer.db').mkdir();(p/'customer.db/data.txt').write_text('harmless sentinel')
    def check(label,command,env='production'):
        d=evaluate(Request(command=command,cwd=p,explicit_env=env))
        row={'label':label,'command':command,'decision':d.decision,'environment':d.environment,'use_case':d.use_case}
        results.append(row);print(json.dumps(row,ensure_ascii=False))
    check('no_certificate_control','git push origin HEAD:dev')
    check('absolute_git_no_certificate','/usr/bin/git push origin HEAD:dev')
    check('redirect_control','cat sample.txt > .ceh/last-ci-run.json')
    check('redirect_adjacent','cat sample.txt>.ceh/last-ci-run.json')
    check('redirect_outer_shell',"bash -c 'echo ok' > .ceh/last-ci-run.json")
    check('redirect_outer_subshell','(echo ok) > .ceh/last-ci-run.json')
    check('production_prefix_control','env APP_ENV=production php artisan migrate:fresh',None)
    check('production_prefix_shell',"env APP_ENV=production bash -c 'php artisan migrate:fresh'",None)
    check('reset_control','git reset --hard HEAD')
    check('reset_option_order','git reset HEAD --hard')
    check('rm_directory_dot','rm -rf customer.db')
    check('rm_directory_control','rm -rf customer')
    (p/'.ceh').mkdir()
    (p/'.ceh/last-ci-run.json').write_text(json.dumps({'commit_hash':git('rev-parse','HEAD'),'status':'PASS','exit_code':0,'canonical_verified':True,'command':'SYNTHETIC fixture, not CI execution'}))
    check('force_control','git push --force origin HEAD:dev')
    check('force_grouped_flags','git push -vf origin HEAD:dev')
    check('nonhead_refspec_control','git push origin unchecked:dev')
    git('config','remote.origin.push','unchecked:refs/heads/dev')
    check('nonhead_refspec_git_config','git push origin')
    check('matching_refspec_colon','git push origin :')
    for command in ['cat sample.txt>.ceh/last-ci-run.json',"env APP_ENV=production bash -c 'php artisan migrate:fresh'"]:
        payload={'toolCall':{'name':'run_command','args':{'CommandLine':command,'Cwd':str(p)}}}
        response,exitcode=handle_hook_lifecycle(json.dumps(payload),evaluate)
        results.append({'label':'antigravity_lifecycle','command':command,'response':response,'exit_code':exitcode});print(json.dumps(results[-1],ensure_ascii=False))
    spec=importlib.util.spec_from_file_location('rc_aliases_review',repo/'clearer-engineering/scripts/rc_aliases.py');rc=importlib.util.module_from_spec(spec);spec.loader.exec_module(rc)
    embedded=f'echo "{rc.START_MARKER}"\nexport USER_SETTING=keep\necho "{rc.END_MARKER}"\n'
    clean=rc.clean_rc_content(embedded,str(repo/'clearer-engineering/config/aliases.sh'))
    results.append({'label':'aliases_string_markers','before':embedded,'after':clean,'user_setting_preserved':'USER_SETTING' in clean});print(json.dumps(results[-1]))
    owned=p/'package-output';owned.mkdir();sentinel=owned/'user-sentinel.txt';sentinel.write_text('mine')
    r=subprocess.run([sys.executable,str(repo/'clearer-engineering/tools/package.py'),'--host','muse','--out',str(owned),'--json'],capture_output=True,text=True)
    results.append({'label':'package_destination_sentinel','exit_code':r.returncode,'sentinel_exists':sentinel.exists(),'manifest_version':json.loads((owned/'manifest.json').read_text())['version']});print(json.dumps(results[-1]))
(base/'ceh-review-independent-results.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
print('NO_DESTRUCTIVE_PAYLOAD_EXECUTED; NO_PUSH_EXECUTED; SYNTHETIC_CERTIFICATE_IS_TEST_FIXTURE_ONLY')
