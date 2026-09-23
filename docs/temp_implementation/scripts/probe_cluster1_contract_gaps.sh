#!/usr/bin/env bash
# Probes de contrato do Cluster 1 (R2/R5) — achados G1..G5 do Handoff 003.
# Roda apenas em fixtures descartáveis sob mktemp; nunca executa push.
# Uso: bash docs/temp_implementation/scripts/probe_cluster1_contract_gaps.sh
set -u

CEH_REPO="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
GATE="$CEH_REPO/clearer-engineering/scripts/safety-gate.py"
RUNNER="$CEH_REPO/clearer-engineering/scripts/test-runner.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "CEH_HEAD=$(git -C "$CEH_REPO" rev-parse HEAD)"
echo "CEH_DIRTY_FILES=$(git -C "$CEH_REPO" status --porcelain --untracked-files=all | wc -l)"
echo "HOST=$(uname -srm) PYTHON=$(python3 --version 2>&1)"
echo

decision() {
    python3 "$GATE" --check "$1" --env "${2:-development}" 2>/dev/null \
        | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['decision'], '|', d.get('use_case'))" || true
}

write_test() {
    printf 'import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.assertEqual(1, %s)\n' "$1" > tests/test_a.py
}

cd "$TMP"
git init -qb dev
git config user.name "CEH Probe"
git config user.email "ceh-probe@example.invalid"
printf '__pycache__/\n*.pyc\n.pytest_cache/\n' > .gitignore
mkdir -p .github/workflows tests
printf 'on: push\njobs:\n  t:\n    runs-on: x\n    steps:\n      - run: python3 -m unittest\n' > .github/workflows/ci.yml
touch tests/__init__.py requirements.txt
printf '__pycache__/\n' > .gitignore
write_test 1
git add .
git commit -qm "fixture: suíte verde"

echo "G1) Certificado escrito à mão, sem rodar testes:"
mkdir -p .ceh
printf '{"commit_hash":"%s","status":"PASS","exit_code":0,"canonical_verified":true,"command":"python3 -m unittest"}\n' \
    "$(git rev-parse HEAD)" > .ceh/last-ci-run.json
g1_res=$(decision 'git push origin dev')
echo "  gate: $g1_res"
if [[ "$g1_res" != *"allow"* ]]; then
    echo "ERRO G1: Esperado allow conforme modelo declarado (fora do modelo)" >&2
    exit 1
fi
rm -rf .ceh

echo "G2) HEAD com teste quebrado + correção apenas no worktree:"
write_test 2
git commit -qam "fixture: HEAD quebrado"
write_test 1
set +e
bash "$RUNNER" python3 -m unittest >/dev/null 2>&1
r_exit=$?
set -e
g2_res=$(decision 'git push origin dev')
if [ -f .ceh/last-ci-run.json ]; then
    echo "ERRO G2: Certificado não deveria ser emitido em worktree sujo" >&2
    exit 1
fi
echo "  runner_exit=$r_exit cert_emitido=nao (correto: worktree sujo) head=$(git rev-parse --short=8 HEAD)"
echo "  gate: $g2_res"
if [[ "$g2_res" != *"deny"* ]]; then
    echo "ERRO G2: Esperado deny quando não há certificado" >&2
    exit 1
fi
git checkout -q tests/test_a.py

echo "G3) Sem certificado, variantes de force push em development:"
for c in 'git push origin dev' 'git push -f origin dev' 'git push --force-with-lease origin dev' 'git push origin +dev'; do
    dec=$(decision "$c")
    printf '  %-42s gate: %s\n' "$c" "$dec"
    if [[ "$dec" != *"deny"* ]]; then
        echo "ERRO G3: $c deveria ser negado por falta de certificado" >&2
        exit 1
    fi
done

echo "G4) Certificado com aspas no comando executado:"
quoted_cmd="python3 -c 'print(\"x\")'"
mkdir -p .ceh
python3 -c 'import json, sys; json.dump({"canonical_test_command": sys.argv[1]}, open(".ceh/config.json", "w"))' "$quoted_cmd"
git add -f .ceh/config.json
git commit -qm "fixture: config canônico com aspas"
set +e
bash "$RUNNER" "$quoted_cmd" >/dev/null 2>&1
r4_exit=$?
set -e
if [ ! -f .ceh/last-ci-run.json ]; then
    echo "ERRO G4: Certificado deveria ter sido gerado para comando canônico com aspas" >&2
    exit 1
fi
printf '  json.load: '
python3 -c "import json; d = json.load(open('.ceh/last-ci-run.json')); assert d.get('canonical_verified') is True; print('OK')"
g4_res=$(decision 'git push origin dev')
echo "  gate: $g4_res"
if [[ "$g4_res" != *"allow"* ]]; then
    echo "ERRO G4: Gate deveria aprovar com certificado canônico válido" >&2
    exit 1
fi
rm -rf .ceh
git rm -qf .ceh/config.json
git commit -qm "fixture: limpa config"

echo "G5) Flags de interpretador fora da denylist (package.json):"
git checkout -q -b g5
printf 'on: push\njobs:\n  t:\n    runs-on: x\n    steps:\n      - run: npm test\n' > .github/workflows/ci.yml
python3 -c "import json; json.dump({'scripts': {'test': \"python3 -Ic 'exit(0)'\"}}, open('package.json', 'w'))"
git add -A
git commit -qm "fixture: test fake"
set +e
bash "$RUNNER" >/dev/null 2>&1
r5_exit=$?
set -e
g5_res=$(decision 'git push origin g5')
echo "  runner_exit=$r5_exit canonical_verified=$(python3 -c "import json; print(json.load(open('.ceh/last-ci-run.json'))['canonical_verified'])")"
echo "  gate: $g5_res"
if [[ "$g5_res" != *"allow"* ]]; then
    echo "ERRO G5: Esperado allow conforme modelo declarado (fora do modelo)" >&2
    exit 1
fi

echo
echo "TODOS OS PROBES G1-G5 VALIDADOS COM SUCESSO!"
