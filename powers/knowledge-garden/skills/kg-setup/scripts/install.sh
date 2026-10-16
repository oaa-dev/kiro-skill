#!/bin/sh
# Install Knowledge Garden's skills, sub-agents and steering into a Kiro workspace.
#
# Shipped as skills/kg-setup/scripts/install.sh by scripts/build-kiro-power.py, which fills in
# the version. /kg-setup runs it from the project root:
#
#     sh <kg-setup folder>/scripts/install.sh <laravel|nextjs|fullstack|generic>
#
# Sources are found relative to this script, so it works from the installed power or from a copy
# of the power's skills in ~/.kiro/skills. What it installed is recorded in .kiro/kg-manifest.txt.
# On a re-run a file is replaced only if it still matches what was installed last time; a file the
# user edited is kept and reported. A file the power no longer ships is removed on the same terms.

set -eu

VERSION="0.6.0"
STACK="${1:-}"
case "$STACK" in
  laravel | nextjs | fullstack | generic) ;;
  *)
    echo "usage: sh install.sh <laravel|nextjs|fullstack|generic>" >&2
    exit 2
    ;;
esac

SETUP_DIR=$(cd "$(dirname "$0")/.." && pwd)
SKILLS_DIR=$(dirname "$SETUP_DIR")
DEST="$(pwd)/.kiro"
MANIFEST="$DEST/kg-manifest.txt"

if [ "$SKILLS_DIR" = "$DEST/skills" ]; then
  echo "This is a workspace copy of kg-setup. Run setup from the Knowledge Garden power" >&2
  echo "(or from ~/.kiro/skills) so it installs the current version." >&2
  exit 3
fi

TAB=$(printf '\t')
NEW_MANIFEST=$(mktemp)
LIST=$(mktemp)
trap 'rm -f "$NEW_MANIFEST" "$LIST"' EXIT

added=0 updated=0 unchanged=0 removed=0 kept=""

sig() { cksum <"$1" | tr ' ' '-'; }

recorded() {
  [ -f "$MANIFEST" ] || return 0
  awk -F "$TAB" -v p="$1" '$2 == p { print $1; exit }' "$MANIFEST"
}

# $1 = source file, $2 = path under .kiro/
install_file() {
  dst="$DEST/$2"
  want=$(sig "$1")
  if [ ! -e "$dst" ]; then
    mkdir -p "$(dirname "$dst")"
    cp "$1" "$dst"
    added=$((added + 1))
  else
    have=$(sig "$dst")
    if [ "$have" = "$want" ]; then
      unchanged=$((unchanged + 1))
    elif [ "$have" = "$(recorded "$2")" ]; then
      cp "$1" "$dst"
      updated=$((updated + 1))
    else
      kept="$kept
  .kiro/$2"
      want=$(recorded "$2") # keep the last signature we shipped, so the edit stays detected
    fi
  fi
  [ -z "$want" ] || printf '%s\t%s\n' "$want" "$2" >>"$NEW_MANIFEST"
}

# Skills: every kg-* skill except kg-setup, which stays in the power so re-running setup after a
# power update installs the new version rather than the workspace's old one.
for dir in "$SKILLS_DIR"/kg-*/; do
  name=$(basename "$dir")
  [ "$name" = "kg-setup" ] && continue
  find "$dir" -type f | sort >"$LIST"
  while IFS= read -r f; do
    install_file "$f" "skills/${f#"$SKILLS_DIR"/}"
  done <"$LIST"
done

for f in "$SETUP_DIR"/references/agents/*.md; do
  install_file "$f" "agents/$(basename "$f")"
done

case "$STACK" in
  laravel) rules="laravel" ;;
  nextjs) rules="nextjs" ;;
  fullstack) rules="laravel nextjs" ;;
  generic) rules="" ;;
esac
for r in $rules; do
  install_file "$SETUP_DIR/references/steering/kg-$r.md" "steering/kg-$r.md"
done

# Files installed last time that this version no longer ships.
if [ -f "$MANIFEST" ]; then
  while IFS="$TAB" read -r old path; do
    case "$old" in "#"* | "") continue ;; esac
    awk -F "$TAB" -v p="$path" '$2 == p { found = 1 } END { exit !found }' "$NEW_MANIFEST" && continue
    [ -e "$DEST/$path" ] || continue
    if [ "$(sig "$DEST/$path")" = "$old" ]; then
      rm "$DEST/$path"
      rmdir -p "$(dirname "$DEST/$path")" 2>/dev/null || true
      removed=$((removed + 1))
    else
      kept="$kept
  .kiro/$path (no longer shipped)"
    fi
  done <"$MANIFEST"
fi

mkdir -p "$DEST"
{
  printf '# Knowledge Garden %s, installed by kg-setup. Do not edit.\n' "$VERSION"
  cat "$NEW_MANIFEST"
} >"$MANIFEST"

echo "Knowledge Garden $VERSION installed into .kiro/ (stack: $STACK)"
echo "  added $added, updated $updated, unchanged $unchanged, removed $removed"
if [ -n "$kept" ]; then
  echo "  kept, because they were edited in this project (delete and re-run setup to replace):$kept"
fi
