#!/bin/bash
# Bruk: bash ~/ki-push-rom.sh 2.3.0
set -e
V=$1
[ -z "$V" ] && { echo "Bruk: ki-push-rom.sh 2.3.0"; exit 1; }
REPO=~/Documents/HomeAssistant/ki-rom
U=${V//./_}                      # 2.3.0 -> 2_3_0

cd ~/Downloads
ZIP=""
for k in "ki-rom-$V.zip" "ki-rom-$U.zip"; do
  [ -f "$k" ] && ZIP="$k" && break
done
[ -z "$ZIP" ] && { echo "Fant ingen ki-rom-$V.zip eller ki-rom-$U.zip i ~/Downloads"; exit 1; }

rm -rf "ki-rom-$V" && unzip -oq "$ZIP" -d "ki-rom-$V"

KILDE="ki-rom-$V"
[ -d "$KILDE/ki-rom" ] && KILDE="$KILDE/ki-rom"
[ -d "$KILDE/custom_components" ] || { echo "Fant ingen custom_components i pakka"; exit 1; }

[ -d "$REPO/.git" ] || git clone -q https://github.com/SebastianKristo/ki-rom.git "$REPO"
cp -r "$KILDE/." "$REPO/"
cd "$REPO"
perl -pi -e "s/\"version\": \"[^\"]*\"/\"version\": \"$V\"/" custom_components/ki_rom/manifest.json
git add .
git commit -m "KI Rom v$V" || true
git push origin main
git tag -f "v$V" && git push -f origin "v$V"

NOTAT=""
[ -f RELEASE.md ] && NOTAT="--notes-file RELEASE.md"
if gh release view "v$V" >/dev/null 2>&1; then
  gh release edit "v$V" $NOTAT && echo "Ferdig. Release v$V oppdatert."
else
  gh release create "v$V" --title "v$V" $NOTAT && echo "Ferdig. Release v$V opprettet."
fi
