#!/usr/bin/env bash
# ==============================================================================
# test-runner.sh - Evidence-Capturing Test Runner for CLEARER Harness
# ==============================================================================
set -u

echo "=== [CEH Deterministic Test Runner] ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Working Directory: $(pwd)"
echo ""

TEST_CMD=""

AUTO_DETECTED=0

if [[ $# -gt 0 ]]; then
    TEST_CMD="$*"
else
    AUTO_DETECTED=1
    # Auto-detect test runner based on files
    if [[ -f "composer.json" ]]; then
        if [[ -f "vendor/bin/pest" ]] || grep -q '"pestphp/pest"' composer.json 2>/dev/null; then
            TEST_CMD="./vendor/bin/pest"
        elif [[ -f "vendor/bin/phpunit" ]] || [[ -f "phpunit.xml" ]]; then
            TEST_CMD="./vendor/bin/phpunit"
        elif [[ -f "artisan" ]]; then
            TEST_CMD="php artisan test"
        fi
    elif [[ -f "package.json" ]]; then
        if grep -q '"test"' package.json 2>/dev/null; then
            if [[ -f "pnpm-lock.yaml" ]]; then
                TEST_CMD="pnpm test"
            elif [[ -f "yarn.lock" ]]; then
                TEST_CMD="yarn test"
            elif [[ -f "bun.lockb" ]] || [[ -f "bun.lock" ]]; then
                TEST_CMD="bun test"
            else
                TEST_CMD="npm test"
            fi
        fi
    elif [[ -f "pytest.ini" ]] || [[ -f "conftest.py" ]] || [[ -d "tests" && ( -f "pyproject.toml" || -f "requirements.txt" ) ]]; then
        if command -v pytest >/dev/null 2>&1; then
            TEST_CMD="pytest"
        else
            TEST_CMD="python3 -m unittest"
        fi
    elif [[ -f "go.mod" ]]; then
        TEST_CMD="go test ./..."
    elif [[ -f "Cargo.toml" ]]; then
        TEST_CMD="cargo test"
    fi
fi

if [[ -z "$TEST_CMD" ]]; then
    echo "STATUS: NOT RUN"
    echo "REASON: No test suite or command detected in this workspace."
    echo "EXIT CODE: 1"
    exit 1
fi

RAW_TEST_CMD="$TEST_CMD"
CLEAN_RUNNER=$(echo "$TEST_CMD" | sed -E 's/^[[:space:]]*rtk([[:space:]]+proxy)?[[:space:]]+//')

CONFIG_CMD=""
if [[ -f ".ceh/config.json" ]]; then
    CONFIG_CMD=$(grep -o '"canonical_test_command"[[:space:]]*:[[:space:]]*"[^"]*"' .ceh/config.json 2>/dev/null | cut -d'"' -f4 || true)
fi

CANONICAL_VERIFIED=false
CANONICAL_REASON="FAIL-CLOSED: Validação canônica não iniciada"

# Validador de canonicidade com Fail-Closed estrito
VALIDATOR_RES=$(python3 - << 'PYEOF' "$CLEAN_RUNNER" "$AUTO_DETECTED" "$CONFIG_CMD"
import sys, os, re, json, shlex
from pathlib import Path

clean_runner = sys.argv[1].strip()
auto_detected = (sys.argv[2] == "1")
config_cmd = sys.argv[3].strip() if len(sys.argv) > 3 else ""
trivial_commands = {"true", "false", ":", "echo", "cat", "exit 0", "exit"}

def check_trivial_or_fake_pass(toks):
    """
    Verifica se uma lista de tokens representa um comando trivial, no-op ou saída simulada (fake pass).
    Retorna (is_trivial, reason).
    """
    if not toks:
        return True, "Comando vazio."

    wrapper_cmds = {
        "command", "builtin", "env", "exec", "nohup", "sudo", "doas",
        "nice", "ionice", "time"
    }
    unwrapped = list(toks)
    while unwrapped:
        first_u = unwrapped[0].lstrip("!")
        if first_u in wrapper_cmds or first_u.startswith("-") or "=" in first_u:
            unwrapped.pop(0)
        else:
            break

    if not unwrapped:
        return True, "Comando trivial ou wrapper vazio."

    first_clean = unwrapped[0].lstrip("!")
    base_first = Path(first_clean).name if "/" in first_clean else first_clean

    trivial_names = {"true", "false", ":", "echo", "cat", "exit", "exit 0"}
    if base_first in trivial_names or first_clean in trivial_names:
        return True, f"Comando trivial ('{first_clean}') detectado."

    # Veto incondicional a execução opaca inline (node -e, python -c, php -r, ruby -e, perl -e/-E)
    # A avaliação estática de código arbitrário em string inline é indecidível e vulnerável a fake-pass.
    if base_first in ("node", "nodejs"):
        for arg in unwrapped[1:]:
            if arg in ("-e", "--eval", "-p", "--print", "-pe", "-ep"):
                return True, "Execução opaca inline ('node -e' / 'node -p') proibida em scripts de teste. Utilize arquivos de teste dedicados (ex: 'node test.js') ou test runners oficiais (ex: 'node --test', 'jest', 'vitest')."
            if arg.startswith("--eval") or arg.startswith("--print"):
                return True, "Execução opaca inline ('node --eval' / 'node --print') proibida em scripts de teste. Utilize arquivos de teste dedicados (ex: 'node test.js') ou test runners oficiais (ex: 'node --test', 'jest', 'vitest')."
            if re.match(r"^-(?:e|p|pe|ep)", arg):
                return True, "Execução opaca inline ('node -e' / 'node -p') proibida em scripts de teste. Utilize arquivos de teste dedicados (ex: 'node test.js') ou test runners oficiais (ex: 'node --test', 'jest', 'vitest')."

    if base_first in ("python", "python3"):
        if any(arg == "-c" or arg.startswith("-c") for arg in unwrapped[1:]):
            return True, "Execução opaca inline ('python -c') proibida em scripts de teste. Utilize arquivos de teste dedicados ou test runners oficiais (ex: 'pytest', 'python -m unittest discover')."

    if base_first == "php":
        if any(arg == "-r" or arg.startswith("-r") for arg in unwrapped[1:]):
            return True, "Execução opaca inline ('php -r') proibida em scripts de teste. Utilize arquivos de teste dedicados ou test runners oficiais (ex: 'phpunit', 'pest', 'artisan test')."

    if base_first == "perl":
        arg_consuming = {"M", "m", "I", "F", "C", "D", "V", "x", "0", "i"}
        for arg in unwrapped[1:]:
            if arg in ("-e", "-E") or arg.startswith("--eval"):
                return True, "Execução opaca inline ('perl -e' / 'perl -E') proibida em scripts de teste. Utilize arquivos de teste dedicados (ex: 'perl test.t') ou test runners oficiais (ex: 'prove')."
            if arg.startswith("-") and not arg.startswith("--"):
                for ch in arg[1:]:
                    if ch in ("e", "E"):
                        return True, "Execução opaca inline ('perl -e' / 'perl -E') proibida em scripts de teste. Utilize arquivos de teste dedicados (ex: 'perl test.t') ou test runners oficiais (ex: 'prove')."
                    if ch in arg_consuming:
                        break

    if base_first == "ruby":
        for arg in unwrapped[1:]:
            if arg == "-e" or arg.startswith("--eval"):
                return True, "Execução opaca inline ('ruby -e') proibida em scripts de teste."
            if re.match(r"^-[pnaWwcCdt]*e", arg):
                return True, "Execução opaca inline ('ruby -e') proibida em scripts de teste."

    return False, ""

tokens = clean_runner.split()
is_triv, triv_reason = check_trivial_or_fake_pass(tokens)
if is_triv:
    print(json.dumps({"verified": False, "reason": triv_reason}))
    sys.exit(0)

compound_op_pattern = r"(\|\||&&|;|\||&|\n|\r|\$\(|`|\${|<|>|(?:^|\s)!(?:\s|\w|$))"
if re.search(compound_op_pattern, clean_runner):
    print(json.dumps({"verified": False, "reason": "Comandos encadeados com operadores de shell (||, &&, ;, |, &, !) são expressamente proibidos no test-runner."}))
    sys.exit(0)

def extract_ci_required_scripts(repo_path):
    wf_dir = repo_path / ".github" / "workflows"
    if not wf_dir.is_dir():
        return set(), set()
    req_npm = set()
    req_comp = set()

    files_to_process = list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml"))
    processed_files = set()

    while files_to_process:
        cur_file = files_to_process.pop(0)
        try:
            real_path = cur_file.resolve()
        except Exception:
            real_path = cur_file
        if real_path in processed_files:
            continue
        processed_files.add(real_path)

        try:
            content = cur_file.read_text(encoding="utf-8")
        except Exception:
            continue

        in_run_block = False
        run_block_indent = 0
        for raw_line in content.splitlines():
            # Suporte a Composite Actions locais: uses: ./(...)
            m_uses = re.match(r"^\s*(?:-\s*)?uses:\s*(\./[^\s#]+)", raw_line)
            if m_uses:
                rel_action = m_uses.group(1).strip()
                action_path = (repo_path / rel_action).resolve()
                candidate_files = []
                if action_path.is_file():
                    candidate_files.append(action_path)
                elif action_path.is_dir():
                    for act_name in ("action.yml", "action.yaml"):
                        act_file = action_path / act_name
                        if act_file.is_file():
                            candidate_files.append(act_file)
                for cf in candidate_files:
                    if cf.resolve() not in processed_files and cf not in files_to_process:
                        files_to_process.append(cf)

            m_run = re.match(r"^(\s*)(?:-\s*)?run:\s*(.*)$", raw_line)
            if m_run:
                indent = len(m_run.group(1))
                cmd = m_run.group(2).strip()
                if cmd in ("|", ">", "|-", ">-"):
                    in_run_block = True
                    run_block_indent = indent
                    continue
                else:
                    in_run_block = False
                    _parse_cmd_for_scripts(cmd, req_npm, req_comp)
            elif in_run_block:
                current_indent = len(raw_line) - len(raw_line.lstrip())
                if current_indent > run_block_indent and raw_line.strip():
                    _parse_cmd_for_scripts(raw_line.strip(), req_npm, req_comp)
                elif raw_line.strip():
                    in_run_block = False

    return req_npm, req_comp

def _parse_cmd_for_scripts(cmd_line, req_npm, req_comp):
    clean = cmd_line.strip("'\"")
    for sub in re.split(r"&&|;", clean):
        toks = sub.strip().split()
        if not toks:
            continue
        wrapper_prefixes = {
            "command", "builtin", "env", "exec", "nohup", "sudo", "doas",
            "nice", "ionice", "time"
        }
        while toks:
            t = toks[0]
            if t in wrapper_prefixes or "=" in t or t.startswith("-"):
                toks.pop(0)
            else:
                break
        if not toks:
            continue
        first = toks[0]
        if first in ("npm", "pnpm", "yarn", "bun"):
            if len(toks) >= 2:
                if toks[1] == "run" and len(toks) >= 3:
                    s = toks[2]
                    if s not in ("install", "ci", "build"):
                        req_npm.add(s)
                elif toks[1] not in ("install", "ci", "build"):
                    req_npm.add(toks[1])
        elif first == "composer":
            if len(toks) >= 2:
                if toks[1] == "run-script" and len(toks) >= 3:
                    req_comp.add(toks[2])
                elif toks[1] not in ("install", "update", "dump-autoload"):
                    req_comp.add(toks[1])

# 1. Inspeção de scripts em package.json e composer.json
def inspect_package_script(cmd_str):
    parts = cmd_str.split()
    if not parts:
        return True, "", set(), ""
    pkg_mgrs = {"npm", "pnpm", "yarn", "bun"}
    shell_executors = {"bash", "sh", "zsh", "dash", "ksh"}
    prohibited_tokens = ("$(", "`", "${", "<(", ">(")
    wrapper_cmds = {
        "command", "builtin", "env", "exec", "nohup", "sudo", "doas",
        "nice", "ionice", "time"
    }

    if parts[0] in pkg_mgrs:
        script_name = None
        if len(parts) >= 2:
            if parts[1] == "test":
                script_name = "test"
            elif parts[1] == "run" and len(parts) >= 3:
                script_name = parts[2]
        if script_name and Path("package.json").is_file():
            try:
                pkg_data = json.loads(Path("package.json").read_text(encoding="utf-8"))
                scripts = pkg_data.get("scripts", {})
                visited = set()
                to_check = [s for s in (f"pre{script_name}", script_name, f"post{script_name}") if s in scripts or s == script_name]
                while to_check:
                    curr = to_check.pop(0)
                    if curr in visited:
                        continue
                    visited.add(curr)
                    if curr not in scripts:
                        return False, f"Script '{curr}' não encontrado em package.json.", visited, "npm"
                    body = scripts[curr]
                    if any(token in body for token in prohibited_tokens):
                        return False, f"Construção de shell não suportada (subshell/process substitution/expansão) detectada no script '{curr}' de package.json: '{body}'.", visited, "npm"
                    if "||" in body:
                        return False, f"Script '{curr}' em package.json contém operador '||' de mascaramento: '{body}'.", visited, "npm"
                    if ";" in body:
                        return False, f"Script '{curr}' em package.json contém operador ';' de encadeamento sem validação: '{body}'.", visited, "npm"
                    if "|" in body:
                        return False, f"Script '{curr}' em package.json contém pipe '|' que oculta exit code: '{body}'.", visited, "npm"
                    if re.search(r"(?<!&)&(?!&)", body):
                        return False, f"Script '{curr}' em package.json contém operador '&' em background: '{body}'.", visited, "npm"
                    if re.search(r"(?:^|\s|&&|\|\||;|\||&)!(\s|\w|$)", body):
                        return False, f"Script '{curr}' em package.json contém operador de negação/inversão de exit code '!': '{body}'.", visited, "npm"
                    for sc in body.split("&&"):
                        sc_clean = sc.strip()
                        if not sc_clean:
                            return False, f"Subcomando vazio detectado em agregação '&&' no script '{curr}'.", visited, "npm"
                        try:
                            sc_toks = shlex.split(sc_clean)
                        except Exception as e:
                            return False, f"Falha léxica ao analisar subcomando '{sc_clean}' no script '{curr}': {str(e)}.", visited, "npm"
                        if not sc_toks:
                            continue
                        if any(t.lstrip("!") == "eval" for t in sc_toks):
                            return False, f"Comando opaco 'eval' proibido no script '{curr}' de package.json.", visited, "npm"
                        for idx, tok in enumerate(sc_toks):
                            tok_clean = tok.lstrip("!")
                            cmd_base = Path(tok_clean).name if "/" in tok_clean else tok_clean
                            if cmd_base in shell_executors:
                                if any(arg == "-c" or arg.startswith("-c") for arg in sc_toks[idx+1:]):
                                    return False, f"Execução opaca de shell ('{tok} -c') proibida no script '{curr}' de package.json.", visited, "npm"
                        unwrapped = list(sc_toks)
                        while unwrapped:
                            first_u = unwrapped[0].lstrip("!")
                            if first_u in wrapper_cmds or first_u.startswith("-") or "=" in first_u:
                                unwrapped.pop(0)
                            else:
                                break
                        if not unwrapped:
                            return False, f"Comando trivial ou wrapper vazio detectado no script '{curr}' de package.json: '{sc_clean}'.", visited, "npm"
                        first_clean = unwrapped[0].lstrip("!")
                        base_first = Path(first_clean).name if "/" in first_clean else first_clean
                        is_triv, triv_reason = check_trivial_or_fake_pass(sc_toks)
                        if is_triv:
                            return False, f"Subcomando trivial ou no-op no script '{curr}' de package.json: {triv_reason}", visited, "npm"
                        if len(unwrapped) >= 2 and base_first in pkg_mgrs:
                            sub_target = None
                            if unwrapped[1] == "test":
                                sub_target = "test"
                            elif unwrapped[1] == "run" and len(unwrapped) >= 3:
                                sub_target = unwrapped[2]
                            elif unwrapped[1] not in ("install", "ci", "build"):
                                sub_target = unwrapped[1]
                            if sub_target:
                                for sub_s in (f"pre{sub_target}", sub_target, f"post{sub_target}"):
                                    if (sub_s in scripts or sub_s == sub_target) and sub_s not in visited and sub_s not in to_check:
                                        to_check.append(sub_s)
                return True, "", visited, "npm"
            except Exception as e:
                return False, f"Falha ao validar package.json: {str(e)}", set(), "npm"

    if parts[0] == "composer" and Path("composer.json").is_file():
        try:
            comp_data = json.loads(Path("composer.json").read_text(encoding="utf-8"))
            comp_scripts = comp_data.get("scripts", {})
            target = "test"
            if len(parts) >= 3 and parts[1] == "run-script":
                target = parts[2]
            to_check = [target]
            visited = set()
            while to_check:
                cur_target = to_check.pop(0)
                if cur_target in visited:
                    continue
                visited.add(cur_target)
                if cur_target not in comp_scripts:
                    return False, f"Script '{cur_target}' referenciado não foi encontrado em composer.json.", visited, "composer"
                raw_target = comp_scripts[cur_target]
                items = raw_target if isinstance(raw_target, list) else [str(raw_target)]
                for item in items:
                    if any(token in item for token in prohibited_tokens):
                        return False, f"Construção de shell não suportada detectada no script '{cur_target}' de composer.json: '{item}'.", visited, "composer"
                    if "||" in item or ";" in item or "|" in item or re.search(r"(?<!&)&(?!&)", item) or re.search(r"(?:^|\s|&&|\|\||;|\||&)!(\s|\w|$)", item):
                        return False, f"Script '{cur_target}' em composer.json contém operador de mascaramento/negação: '{item}'.", visited, "composer"
                    for sc in item.split("&&"):
                        sc_clean = sc.strip()
                        if not sc_clean:
                            continue
                        try:
                            sc_toks = shlex.split(sc_clean)
                        except Exception as e:
                            return False, f"Falha léxica ao analisar subcomando '{sc_clean}' em composer.json: {str(e)}.", visited, "composer"
                        if not sc_toks:
                            continue
                        if any(t.lstrip("!") == "eval" for t in sc_toks):
                            return False, f"Comando opaco 'eval' proibido no script '{cur_target}' de composer.json.", visited, "composer"
                        for idx, tok in enumerate(sc_toks):
                            tok_clean = tok.lstrip("!")
                            cmd_base = Path(tok_clean).name if "/" in tok_clean else tok_clean
                            if cmd_base in shell_executors:
                                if any(arg == "-c" or arg.startswith("-c") for arg in sc_toks[idx+1:]):
                                    return False, f"Execução opaca de shell ('{tok} -c') proibida no script '{cur_target}' de composer.json.", visited, "composer"
                        unwrapped = list(sc_toks)
                        while unwrapped:
                            first_u = unwrapped[0].lstrip("!")
                            if first_u in wrapper_cmds or first_u.startswith("-") or "=" in first_u:
                                unwrapped.pop(0)
                            else:
                                break
                        if not unwrapped:
                            return False, f"Comando trivial ou wrapper vazio detectado no script '{cur_target}' de composer.json: '{sc_clean}'.", visited, "composer"
                        first_clean = unwrapped[0].lstrip("!")
                        base_first = Path(first_clean).name if "/" in first_clean else first_clean
                        is_triv, triv_reason = check_trivial_or_fake_pass(sc_toks)
                        if is_triv:
                            return False, f"Subcomando trivial ou no-op no script '{cur_target}' de composer.json: {triv_reason}", visited, "composer"
                        # Suporte a aliases do Composer: @script, @composer run-script <script>, composer run-script <script>
                        if first_clean.startswith("@"):
                            ref = first_clean[1:]
                            if ref == "composer" and len(unwrapped) >= 2:
                                sub = unwrapped[2] if (len(unwrapped) >= 3 and unwrapped[1] == "run-script") else unwrapped[1]
                                if sub not in visited and sub not in to_check:
                                    to_check.append(sub)
                            elif ref in comp_scripts:
                                if ref not in visited and ref not in to_check:
                                    to_check.append(ref)
                            elif ref not in ("php", "putenv"):
                                return False, f"Script referenciado '{first_clean}' não foi encontrado em composer.json.", visited, "composer"
                        elif base_first == "composer" and len(unwrapped) >= 2:
                            sub = unwrapped[2] if (len(unwrapped) >= 3 and unwrapped[1] == "run-script") else unwrapped[1]
                            if sub in comp_scripts and sub not in visited and sub not in to_check:
                                to_check.append(sub)
            return True, "", visited, "composer"
        except Exception as e:
            return False, f"Falha ao validar composer.json: {str(e)}", set(), "composer"
    return True, "", set(), parts[0]

pkg_ok, pkg_err, reachable_scripts, pkg_type = inspect_package_script(clean_runner)
if not pkg_ok:
    print(json.dumps({"verified": False, "reason": pkg_err}))
    sys.exit(0)

# Confronta jobs da esteira de CI com os scripts cobertos pela execução
req_npm, req_comp = extract_ci_required_scripts(Path.cwd())
if pkg_type == "npm" and req_npm:
    missing = req_npm - reachable_scripts
    if missing:
        print(json.dumps({"verified": False, "reason": f"A suíte executada ('{clean_runner}') não cobre os jobs/scripts exigidos pela CI (.github/workflows): {sorted(missing)}. O agregador deve cobrir todos os jobs declarados."}))
        sys.exit(0)

if pkg_type == "composer" and req_comp:
    missing = req_comp - reachable_scripts
    if missing:
        print(json.dumps({"verified": False, "reason": f"A suíte executada ('{clean_runner}') não cobre os jobs/scripts exigidos pela CI (.github/workflows): {sorted(missing)}. O agregador deve cobrir todos os jobs declarados."}))
        sys.exit(0)

# 2. Correspondência canônica com .ceh/config.json
if config_cmd:
    cfg_tokens = config_cmd.split()
    cfg_first = cfg_tokens[0] if cfg_tokens else ""
    if cfg_first not in trivial_commands and config_cmd not in trivial_commands:
        if clean_runner == config_cmd:
            print(json.dumps({"verified": True, "reason": f"Corresponde exatamente a canonical_test_command ('{config_cmd}')."}))
            sys.exit(0)
        else:
            print(json.dumps({"verified": False, "reason": f"Comando '{clean_runner}' não corresponde à suíte agregadora canônica ('{config_cmd}')."}))
            sys.exit(0)

# 3. Auto-detecção sem argumentos explícitos
if auto_detected:
    print(json.dumps({"verified": True, "reason": "Suíte canônica auto-detectada para o repositório."}))
    sys.exit(0)

# 4. Homologação estrita de runners padrão sem argumentos parciais de arquivo/filtro
parts = clean_runner.split()
if not parts:
    print(json.dumps({"verified": False, "reason": "Comando vazio."}))
    sys.exit(0)

cmd_name = parts[0]
args = parts[1:]

if cmd_name == "pytest":
    for a in args:
        if a.endswith(".py") or "/" in a or a.startswith("-k") or a.startswith("-m") or a == "--filter":
            print(json.dumps({"verified": False, "reason": f"Argumento parcial ou filtro de teste detectado no pytest: '{a}'. A suíte canônica exige execução integral."}))
            sys.exit(0)
    print(json.dumps({"verified": True, "reason": "pytest integral."}))
    sys.exit(0)

if cmd_name in ("python", "python3") and len(args) >= 2 and args[0] == "-m" and args[1] == "unittest":
    extra_args = args[2:]
    if not extra_args or extra_args[0] == "discover":
        for a in extra_args:
            if a.endswith(".py") or a.startswith("-k"):
                print(json.dumps({"verified": False, "reason": f"Alvo individual de teste detectado no unittest: '{a}'. A suíte canônica exige execução integral."}))
                sys.exit(0)
        print(json.dumps({"verified": True, "reason": "unittest discover integral."}))
        sys.exit(0)
    else:
        for a in extra_args:
            if a not in ("-v", "-q"):
                print(json.dumps({"verified": False, "reason": f"Alvo individual de teste detectado no unittest: '{a}'. Use 'discover' para suíte integral."}))
                sys.exit(0)
        print(json.dumps({"verified": True, "reason": "unittest integral."}))
        sys.exit(0)

if cmd_name in ("npm", "pnpm", "yarn", "bun"):
    if len(args) == 1 and args[0] == "test":
        print(json.dumps({"verified": True, "reason": f"{cmd_name} test integral."}))
        sys.exit(0)
    print(json.dumps({"verified": False, "reason": f"Argumentos adicionais detectados em '{clean_runner}'. Execução parcial não autoriza push."}))
    sys.exit(0)

if cmd_name == "composer" and len(args) == 1 and args[0] == "test":
    print(json.dumps({"verified": True, "reason": "composer test integral."}))
    sys.exit(0)

if cmd_name in ("phpunit", "./vendor/bin/phpunit", "vendor/bin/phpunit", "pest", "./vendor/bin/pest", "vendor/bin/pest"):
    for a in args:
        if a.endswith(".php") or "/" in a or a in ("--filter", "-k"):
            print(json.dumps({"verified": False, "reason": f"Alvo individual ou filtro detectado no {cmd_name}: '{a}'."}))
            sys.exit(0)
    print(json.dumps({"verified": True, "reason": f"{cmd_name} integral."}))
    sys.exit(0)

if (cmd_name == "php" and len(args) >= 2 and args[0] in ("artisan", "./artisan") and args[1] == "test") or \
   (cmd_name in ("artisan", "./artisan") and len(args) >= 1 and args[0] == "test"):
    extra = args[2:] if cmd_name == "php" else args[1:]
    for a in extra:
        if a.startswith("--filter") or a.endswith(".php") or "/" in a:
            print(json.dumps({"verified": False, "reason": f"Filtro ou arquivo específico detectado no artisan test: '{a}'."}))
            sys.exit(0)
    print(json.dumps({"verified": True, "reason": "artisan test integral."}))
    sys.exit(0)

if cmd_name == "go" and len(args) >= 1 and args[0] == "test":
    if args[1:] == ["./..."]:
        print(json.dumps({"verified": True, "reason": "go test ./... integral."}))
        sys.exit(0)
    target_str = " ".join(args[1:])
    print(json.dumps({"verified": False, "reason": f"Alvo parcial detectado no go test: '{target_str}'. A suíte canônica exige './...'."}))
    sys.exit(0)

if cmd_name == "cargo" and len(args) == 1 and args[0] == "test":
    print(json.dumps({"verified": True, "reason": "cargo test integral."}))
    sys.exit(0)

if cmd_name == "prove":
    for a in args:
        if a.endswith(".t") or "/" in a or a in ("--filter", "-k"):
            print(json.dumps({"verified": False, "reason": f"Alvo individual ou filtro detectado no prove: '{a}'."}))
            sys.exit(0)
    print(json.dumps({"verified": True, "reason": "prove integral."}))
    sys.exit(0)

print(json.dumps({"verified": False, "reason": f"Comando '{clean_runner}' não é reconhecido como runner canônico oficial."}))
sys.exit(0)
PYEOF
2>&1)
VALIDATOR_EXIT=$?

if [[ $VALIDATOR_EXIT -eq 0 ]]; then
    CANONICAL_VERIFIED=$(python3 -c 'import sys, json; data=json.loads(sys.argv[1]); print("true" if data.get("verified") else "false")' "$VALIDATOR_RES" 2>/dev/null || echo "false")
    CANONICAL_REASON=$(python3 -c 'import sys, json; data=json.loads(sys.argv[1]); print(data.get("reason", ""))' "$VALIDATOR_RES" 2>/dev/null || echo "")
else
    CANONICAL_VERIFIED=false
    CANONICAL_REASON="FAIL-CLOSED: Falha de execução no scanner de canonicidade ($VALIDATOR_RES)"
fi

if [[ "$CANONICAL_VERIFIED" == "false" ]]; then
    echo "[CEH WARNING] ⚠️ O comando '$TEST_CMD' não é reconhecido como runner canônico oficial."
    if [[ -n "$CANONICAL_REASON" ]]; then
        echo "[CEH WARNING] Motivo: $CANONICAL_REASON"
    fi
    echo "[CEH WARNING] Este comando NÃO concederá certificado válido de liberação para git push."
fi

# Runtime Adapter: Detect if test command needs container dispatch
DOCKER_RUNNING=0
ACTIVE_COMPOSE_SERVICES=()

if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
        DOCKER_RUNNING=1
        if [[ -f "docker-compose.yml" || -f "docker-compose.yaml" || -f "compose.yaml" || -f "compose.yml" ]]; then
            ACTIVE_COMPOSE=$(docker compose ps --services --filter "status=running" 2>/dev/null || true)
            if [[ -n "$ACTIVE_COMPOSE" ]]; then
                while IFS= read -r s; do
                    [[ -n "$s" ]] && ACTIVE_COMPOSE_SERVICES+=("$s")
                done <<< "$ACTIVE_COMPOSE"
            fi
        fi
    fi
fi

# If containers are actively running and the command is a bare host command, adapt it
if [[ ${#ACTIVE_COMPOSE_SERVICES[@]} -gt 0 ]]; then
    if [[ ! "$TEST_CMD" =~ (docker|docker-compose|sail) ]]; then
        if [[ " ${ACTIVE_COMPOSE_SERVICES[*]} " =~ " laravel.test " ]]; then
            if [[ -f "vendor/bin/sail" ]]; then
                echo "[CEH RUNTIME ADAPTER] 🐳 Containers Laravel Sail ativos detectados. Despachando via Sail..."
                TEST_CMD="./vendor/bin/sail test"
            else
                echo "[CEH RUNTIME ADAPTER] 🐳 Containers Compose ativos detectados. Despachando via 'laravel.test'..."
                TEST_CMD="docker compose exec -T laravel.test $TEST_CMD"
            fi
        elif [[ " ${ACTIVE_COMPOSE_SERVICES[*]} " =~ " app " ]]; then
            echo "[CEH RUNTIME ADAPTER] 🐳 Container 'app' ativo detectado. Despachando via container..."
            TEST_CMD="docker compose exec -T app $TEST_CMD"
        fi
    fi
elif [[ -f "docker-compose.yml" || -f "docker-compose.yaml" || -f "compose.yaml" || -f "compose.yml" ]]; then
    if [[ ! "$TEST_CMD" =~ (docker|docker-compose|sail) ]]; then
        echo "[CEH RUNTIME ADAPTER] ℹ️ Projeto possui Docker configurado, mas os containers estão desligados."
        echo "[CEH RUNTIME ADAPTER] Executando diretamente no Host Nativo..."
    fi
fi

# Token economy proxy: if rtk is available, wrap test command to cut output by up to 80%
if command -v rtk >/dev/null 2>&1; then
    if [[ ! "$TEST_CMD" =~ ^[[:space:]]*rtk[[:space:]] ]]; then
        TEST_CMD="rtk $TEST_CMD"
    fi
fi

echo "=========================================="
echo "COMMAND:   $TEST_CMD"
echo "=========================================="
echo ""

# Execute command and capture output and exit code
OUTPUT_FILE=$(mktemp)
START_TIME=$(date +%s%N 2>/dev/null || date +%s)

set +e
eval "$TEST_CMD" > "$OUTPUT_FILE" 2>&1
EXIT_CODE=$?
set -e

END_TIME=$(date +%s%N 2>/dev/null || date +%s)

cat "$OUTPUT_FILE"
echo ""
echo "=========================================="
echo "EXIT CODE: $EXIT_CODE"
if [[ $EXIT_CODE -eq 0 ]]; then
    echo "STATUS:    PASS"
else
    echo "STATUS:    FAIL"
fi
echo "=========================================="

# Emit Pre-Push CI Clearance Certificate
CEH_DIR=".ceh"
mkdir -p "$CEH_DIR" 2>/dev/null || true
if [[ -d "$CEH_DIR" ]]; then
    CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "untracked")
    NOW_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    STATUS_STR="FAIL"
    [[ $EXIT_CODE -eq 0 ]] && STATUS_STR="PASS"

    cat << EOF > "$CEH_DIR/last-ci-run.json"
{
  "commit_hash": "$CURRENT_COMMIT",
  "timestamp": "$NOW_ISO",
  "command": "$TEST_CMD",
  "normalized_runner": "$RAW_TEST_CMD",
  "canonical_verified": $CANONICAL_VERIFIED,
  "status": "$STATUS_STR",
  "exit_code": $EXIT_CODE
}
EOF
fi

rm -f "$OUTPUT_FILE"
exit $EXIT_CODE
