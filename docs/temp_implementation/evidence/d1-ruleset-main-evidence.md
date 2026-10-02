# Evidência de Execução — Despacho 1 (D1: Ruleset na branch `main`)

**Data/Hora:** 2026-10-01T19:51:47-03:00  
**Repositório:** `nandinhos/antigravity-clearer-engineering-harness`  
**Ruleset ID:** `24338451`  
**Enforcement:** `active`  
**Status:** Comprovado fisicamente (`OBSERVED`)

---

## 1. Prova de Ativação Autenticada (GitHub REST API)

Comando executado:
```bash
gh api repos/nandinhos/antigravity-clearer-engineering-harness/rulesets/24338451
```

Saída bruta capturada:
```json
{
  "id": 24338451,
  "name": "Protect main branch",
  "target": "branch",
  "source_type": "Repository",
  "source": "nandinhos/antigravity-clearer-engineering-harness",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "exclude": [],
      "include": [
        "~DEFAULT_BRANCH"
      ]
    }
  },
  "rules": [
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "required_reviewers": [],
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false,
        "require_extra_approval_for_unattributed_changes": true,
        "allowed_merge_methods": [
          "merge",
          "squash",
          "rebase"
        ]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          {
            "context": "Validate (ubuntu-latest - Python 3.9)"
          },
          {
            "context": "Validate (ubuntu-latest - Python 3.12)"
          },
          {
            "context": "Validate (macos-latest - Python 3.9)"
          },
          {
            "context": "Validate (macos-latest - Python 3.12)"
          }
        ]
      }
    },
    {
      "type": "non_fast_forward"
    },
    {
      "type": "deletion"
    }
  ],
  "node_id": "RRS_lACqUmVwb3NpdG9yec5QWjcWzgFzYBM",
  "created_at": "2026-10-01T19:50:45.589-03:00",
  "updated_at": "2026-10-01T19:50:45.640-03:00",
  "bypass_actors": [],
  "current_user_can_bypass": "never",
  "_links": {
    "self": {
      "href": "https://api.github.com/repos/nandinhos/antigravity-clearer-engineering-harness/rulesets/24338451"
    },
    "html": {
      "href": "https://github.com/nandinhos/antigravity-clearer-engineering-harness/rules/24338451"
    }
  }
}
```

---

## 2. Prova Negativa de Bloqueio Físico no Servidor (GH013)

Comando executado em clone limpo contra o remote do GitHub sem o hook client-side ativo:
```bash
git push origin main
```

Saída bruta capturada (Exit Code: 1):
```text
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: Review all repository rules at https://github.com/nandinhos/antigravity-clearer-engineering-harness/rules?ref=refs%2Fheads%2Fmain
remote: 
remote: - Changes must be made through a pull request.
remote: 
remote: - 4 of 4 required status checks are expected.
remote: 
To https://github.com/nandinhos/antigravity-clearer-engineering-harness.git
 ! [remote rejected] main -> main (push declined due to repository rule violations)
error: failed to push some refs to 'https://github.com/nandinhos/antigravity-clearer-engineering-harness.git'
```

Veredito: **BARREIRA REMOTA ATIVA E INTRANSPONÍVEL (CAMADA 3 COMPROVADA).**

---

## 3. Prova Autenticada de Atualização para Check Único `ci-ok` (CE3 / Handoff 096)

**Data/Hora:** 2026-10-02T05:18:15Z  
**Comando executado:**
```bash
gh api repos/nandinhos/antigravity-clearer-engineering-harness/rulesets/24338451
```

**Saída bruta capturada (Exit Code: 0):**
```json
{
  "id": 24338451,
  "name": "Protect main branch",
  "target": "branch",
  "source_type": "Repository",
  "source": "nandinhos/antigravity-clearer-engineering-harness",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "exclude": [],
      "include": [
        "~DEFAULT_BRANCH"
      ]
    }
  },
  "rules": [
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "required_reviewers": [],
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false,
        "require_extra_approval_for_unattributed_changes": true,
        "allowed_merge_methods": [
          "merge",
          "squash",
          "rebase"
        ]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          {
            "context": "CI Aggregated Status (ci-ok)"
          }
        ]
      }
    },
    {
      "type": "non_fast_forward"
    },
    {
      "type": "deletion"
    }
  ],
  "node_id": "RRS_lACqUmVwb3NpdG9yec5QWjcWzgFzYBM",
  "created_at": "2026-10-01T19:50:45.589-03:00",
  "updated_at": "2026-10-02T00:04:45.191-03:00",
  "bypass_actors": [],
  "current_user_can_bypass": "never"
}
```

Veredito: **Comprovado fisicamente que o único check obrigatório da branch `main` no servidor é `CI Aggregated Status (ci-ok)` (CE3 satisfeito).**
