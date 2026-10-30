#!/bin/zsh
# Starts FM24 with the ReSeason engine module. Only needed to create a new career.
set -eu
cd "${0:A:h}"
source mac/common.zsh

app="$game/fm.app"
tested=f0ba078c384f1095320ed4059a18fe4de4701cae5661a117417b2624d12b16e2  # Steam FM24 24.4.2

[[ $(uname -m) == arm64 ]] || fail "The engine module needs an Apple Silicon Mac. Start FM24 from Steam instead."
[[ -n $game && -d $app ]] || fail "Can't find Football Manager 2024 in your Steam library."
if [[ $(shasum -a 256 "$app/Contents/MacOS/fm") != "$tested "* ]]; then
  fail "This FM24 build isn't Steam 24.4.2, the version the engine module was made for."
fi
if pgrep -x fm >/dev/null; then
  fail "Quit Football Manager 2024 first."
fi

# Files downloaded with a browser are quarantined and macOS refuses to load them.
xattr -d com.apple.quarantine mac/reseason.dylib 2>/dev/null || true

open -n \
  --env DYLD_INSERT_LIBRARIES="$PWD/mac/reseason.dylib" \
  --env FM24_AWARDS_LOG="$HOME/Library/Logs/ReSeason.log" \
  --env FM24_AWARDS_SCHEDULE_MODE=apply \
  --env FM24_AWARDS_FIRST_CYCLE_MODE=catchup \
  --env FM24_WORLD_CUP_HISTORY_MODE=skip-completed \
  --env FM24_INTERNATIONAL_HISTORY_MODE=skip-completed \
  --env FM24_INTERNATIONAL6_HISTORY_MODE=skip-completed \
  --env SteamAppId=2252570 \
  --env SteamGameId=2252570 \
  "$app"

print "FM24 is starting with ReSeason."
print "Create your career, play one day, save and quit."
print "After that, play that save by starting FM24 from Steam as usual."
