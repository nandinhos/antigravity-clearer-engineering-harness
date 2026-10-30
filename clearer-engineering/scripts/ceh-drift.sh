#!/usr/bin/env bash
# ==============================================================================
# CLEARER Engineering Harness (CEH) — Drift Auditor (SDD 2.0 / Ponytail Mode)
# ==============================================================================
# Audita divergências (drift) entre documentos de arquitetura/design e o código real,
# operando sob demanda via Git CLI (sem daemons, sem watchers, 100% POSIX).
# ==============================================================================

set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
RESET='\033[0m'

TARGET_PATH=""
BASE_REF=""
STRICT_MODE=false

usage() {
  cat <<EOF
${BOLD}CLEARER Engineering Harness — Drift Auditor (ceh-drift)${RESET}

Uso:
  $0 [opções]

Opções:
  -t, --target <caminho>   Diretório ou arquivo de especificação/documentação a auditar
                           (Padrão: autodetecta 'docs/designs', '.spec' ou 'docs')
  -b, --base <ref>         Referência Git de comparação (Ex: HEAD~1, origin/main, main)
                           (Padrão: compara alterações da working tree e staged contra HEAD)
  -s, --strict             Modo estrito: falha com código 1 caso haja referências quebradas
                           ou código alterado sem atualização do documento correspondente
  -h, --help               Exibe esta mensagem de ajuda

Exemplos:
  $0
  $0 --target docs/designs/
  $0 --base origin/main --strict
EOF
  exit 0
}

# Parsing de argumentos
while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--target)
      TARGET_PATH="${2:-}"
      shift 2
      ;;
    -b|--base)
      BASE_REF="${2:-}"
      shift 2
      ;;
    -s|--strict)
      STRICT_MODE=true
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo -e "${RED}Opção inválida: $1${RESET}" >&2
      usage
      ;;
  esac
done

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 1. Resolver diretório/arquivos de documentação alvo
DOC_FILES=()

if [[ -n "$TARGET_PATH" ]]; then
  if [[ -f "$TARGET_PATH" ]]; then
    DOC_FILES+=("$TARGET_PATH")
  elif [[ -d "$TARGET_PATH" ]]; then
    while IFS= read -r f; do
      [[ -n "$f" ]] && DOC_FILES+=("$f")
    done < <(find "$TARGET_PATH" -type f \( -name "*.md" -o -name "*.markdown" \) 2>/dev/null || true)
  else
    echo -e "${RED}Erro: Caminho alvo '$TARGET_PATH' não encontrado.${RESET}" >&2
    exit 2
  fi
else
  # Autodescoberta padrão
  CANDIDATE_DIRS=("docs/designs" ".spec" "docs")
  for c_dir in "${CANDIDATE_DIRS[@]}"; do
    if [[ -d "$REPO_ROOT/$c_dir" ]]; then
      while IFS= read -r f; do
        [[ -n "$f" ]] && DOC_FILES+=("$f")
      done < <(find "$REPO_ROOT/$c_dir" -type f \( -name "*.md" -o -name "*.markdown" \) 2>/dev/null || true)
      break
    fi
  done
fi

if [[ ${#DOC_FILES[@]} -eq 0 ]]; then
  echo -e "${CYAN}ceh-drift:${RESET} Nenhum documento de especificação/design encontrado para auditoria. Tudo limpo."
  exit 0
fi

# 2. Obter lista de arquivos alterados no Git (Working Tree / Staged / Base)
CHANGED_FILES=()
if [[ -n "$BASE_REF" ]]; then
  while IFS= read -r f; do
    [[ -n "$f" ]] && CHANGED_FILES+=("$f")
  done < <(git -C "$REPO_ROOT" diff --name-only "$BASE_REF"...HEAD 2>/dev/null || git -C "$REPO_ROOT" diff --name-only "$BASE_REF" 2>/dev/null || true)
else
  # Padrão: modificações não commitadas (working tree + staged)
  while IFS= read -r f; do
    [[ -n "$f" ]] && CHANGED_FILES+=("$f")
  done < <(git -C "$REPO_ROOT" status --porcelain 2>/dev/null | awk '{print $2}' || true)
fi

DRIFT_COUNT=0
BROKEN_REFS=0

echo -e "${BOLD}${CYAN}======================================================================${RESET}"
echo -e "${BOLD}${CYAN}   CLEARER ENGINEERING HARNESS — AUDITORIA DE DRIFT (ceh-drift)        ${RESET}"
echo -e "${BOLD}${CYAN}======================================================================${RESET}"
echo -e "Repositório:     $(basename "$REPO_ROOT")"
echo -e "Documentos:      ${#DOC_FILES[@]} inspecionados"
echo -e "Arquivos no Git: ${#CHANGED_FILES[@]} modificados observados"
echo -e "${CYAN}----------------------------------------------------------------------${RESET}"

# 3. Inspecionar cada documento
for doc in "${DOC_FILES[@]}"; do
  rel_doc="${doc#"$REPO_ROOT"/}"

  # Extrai potenciais referências de caminhos de arquivos citados no markdown
  # Procura por strings com extensão comum ou padrão path/to/file
  # shellcheck disable=SC2016
  mapfile -t REFS < <(grep -oE '`[a-zA-Z0-9_\.\/-]+\.[a-zA-Z0-9]+`|\[[^]]+\]\(([^)]+)\)' "$doc" 2>/dev/null | \
    sed -E 's/^`//; s/`$//; s/^\[[^]]+\]\(([^)#]+).*$/\1/' | \
    grep -vE '^(http|https|mailto|ftp):' | \
    grep -vE '\.(png|jpg|jpeg|gif|svg|ico)$' | \
    sort -u || true)

  for ref in "${REFS[@]}"; do
    clean_ref="${ref#./}"
    clean_ref="${clean_ref#/}"
    
    # 3.1 Checagem de existência física do arquivo referenciado
    target_fs="$REPO_ROOT/$clean_ref"
    if [[ ! -e "$target_fs" && ! -e "$doc/../$clean_ref" ]]; then
      # Só reporta se parecer um caminho relativo viável (tem barra ou extensão típica de código)
      if [[ "$clean_ref" == *"/"* || "$clean_ref" =~ \.(py|php|js|ts|sh|go|rs|json|yaml|yml)$ ]]; then
        echo -e "${RED}[QUEBRA DE REFERÊNCIA]${RESET} $rel_doc cita '${clean_ref}', mas arquivo não existe no filesystem."
        BROKEN_REFS=$((BROKEN_REFS + 1))
      fi
    fi

    # 3.2 Checagem de drift com Git: o arquivo citado mudou, mas o documento não?
    if [[ ${#CHANGED_FILES[@]} -gt 0 ]]; then
      for changed in "${CHANGED_FILES[@]}"; do
        if [[ "$changed" == "$clean_ref" || "$changed" == *"/$clean_ref" ]]; then
          # O arquivo de código mudou. Verificar se o próprio documento também foi modificado
          doc_was_updated=false
          for doc_changed in "${CHANGED_FILES[@]}"; do
            if [[ "$doc_changed" == "$rel_doc" ]]; then
              doc_was_updated=true
              break
            fi
          done

          if [[ "$doc_was_updated" == false ]]; then
            echo -e "${YELLOW}[DRIFT DETECTADO]${RESET} Código '$changed' foi modificado, mas a especificação '$rel_doc' não foi atualizada."
            DRIFT_COUNT=$((DRIFT_COUNT + 1))
          fi
        fi
      done
    fi
  done
done

echo -e "${CYAN}----------------------------------------------------------------------${RESET}"
if [[ $DRIFT_COUNT -eq 0 && $BROKEN_REFS -eq 0 ]]; then
  echo -e "${GREEN}✓ Nenhum drift ou quebra de especificação detectados.${RESET}"
  exit 0
else
  echo -e "${YELLOW}Total de alertas:${RESET} $DRIFT_COUNT drift(s) de código vs doc, $BROKEN_REFS referência(s) quebrada(s)."
  if [[ "$STRICT_MODE" == true || $BROKEN_REFS -gt 0 ]]; then
    exit 1
  fi
  exit 0
fi
