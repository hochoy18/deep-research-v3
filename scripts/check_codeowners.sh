#!/usr/bin/env bash
# =============================================================================
# scripts/check_codeowners.sh — US-5 团队代码归属验证
# =============================================================================
# Parse .github/CODEOWNERS, print a path → owner table, and validate:
#   1. The wildcard fallback rule '*' is the LAST non-comment line (GitHub
#      CODEOWNERS semantics: "last matching pattern wins").
#   2. All 4 M1 Co-Owners (Dev.cai.1-4) appear at least once.
#   3. TL.cai appears as fallback owner.
#   4. No duplicate path patterns.
#
# Compatibility:
#   - bash 3.2+ (macOS default) — uses no associative arrays
#   - bash 4+ / zsh also fine
#
# Usage:
#   scripts/check_codeowners.sh [repo-root]
#
# Exit codes:
#   0 — all checks pass
#   1 — fallback rule absent / not last
#   2 — required owner missing
#   3 — duplicate path pattern
#
# Owner: Dev.cai.4  [Phase 7 US-5 — T097 + T101]
# =============================================================================

set -eu

ROOT="${1:-.}"
CODEOWNERS="${ROOT}/.github/CODEOWNERS"

# ---- preflight -------------------------------------------------------------
if [[ ! -f "$CODEOWNERS" ]]; then
  echo "ERROR: CODEOWNERS not found at $CODEOWNERS" >&2
  exit 1
fi

# ---- 1. parse & print path → owner table ----------------------------------
echo "============================================================"
echo "  CODEOWNERS path → owner table  (.github/CODEOWNERS)"
echo "============================================================"
printf "  %-48s %s\n" "PATTERN" "OWNERS"
printf "  %-48s %s\n" "-------" "------"

# Hold non-comment rules in two parallel arrays (no associative arrays).
declare -a patterns=()
declare -a rules=()
duplicate_found=0
duplicate_msg=""

while IFS= read -r line; do
  # Strip trailing comment + leading/trailing whitespace.
  stripped="${line%%#*}"
  stripped="$(printf '%s' "$stripped" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  if [[ -z "$stripped" ]]; then
    continue
  fi
  pattern="${stripped%% *}"
  rest="${stripped#* }"
  printf "  %-48s %s\n" "$pattern" "$rest"

  # Duplicate detection — linear scan, fine for the ~30 rules we have.
  for existing in "${patterns[@]:-}"; do
    if [[ "$existing" == "$pattern" ]]; then
      duplicate_found=1
      duplicate_msg="$duplicate_msg$pattern "
      break
    fi
  done
  patterns+=("$pattern")
  rules+=("$stripped")
done < "$CODEOWNERS"

if [[ "$duplicate_found" -eq 1 ]]; then
  echo ""
  echo "  FAIL: duplicate path patterns: $duplicate_msg" >&2
  exit 3
fi

# ---- 2. fallback rule check ------------------------------------------------
echo ""
echo "============================================================"
echo "  Fallback rule check  (must be last non-comment line: '*')"
echo "============================================================"
last_idx=$(( ${#rules[@]} - 1 ))
last_rule="${rules[$last_idx]}"
last_pattern="${last_rule%% *}"
if [[ "$last_pattern" == "*" ]]; then
  echo "  PASS  fallback '*' rule is the last entry"
  echo "        -> ${last_rule}"
else
  echo "  FAIL  fallback '*' rule is NOT the last entry" >&2
  echo "        last pattern: ${last_pattern}" >&2
  echo "        expected:    *" >&2
  exit 1
fi

# ---- 3. owner coverage check ----------------------------------------------
echo ""
echo "============================================================"
echo "  Owner coverage check  (5 expected accounts)"
echo "============================================================"
required_owners="Dev.cai.1 Dev.cai.2 Dev.cai.3 Dev.cai.4 TL.cai"
missing=0
for owner in $required_owners; do
  # Count @owner followed by space or EOL — bare "@Dev.cai.1x" must not match.
  count=$(grep -cE "@${owner}([[:space:]]|$)" "$CODEOWNERS" 2>/dev/null || true)
  count="${count:-0}"
  if [[ "$count" -gt 0 ]]; then
    printf "  PASS  @%-12s appears %d time(s)\n" "$owner" "$count"
  else
    printf "  FAIL  @%-12s MISSING\n" "$owner" >&2
    missing=1
  fi
done

if [[ "$missing" -eq 1 ]]; then
  echo ""
  echo "FAIL: required owner missing from CODEOWNERS" >&2
  exit 2
fi

# ---- 4. summary ------------------------------------------------------------
echo ""
echo "============================================================"
echo "  Summary"
echo "============================================================"
total=${#patterns[@]}
wildcards=0
for p in "${patterns[@]}"; do
  if [[ "$p" == "*" ]]; then
    wildcards=$((wildcards + 1))
  fi
done
echo "  Total non-comment rules:   ${total}"
echo "  Wildcard rules:            ${wildcards}"
echo "  Status:                    PASS"