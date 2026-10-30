# Shared by the Mac commands: finds the FM24 user folder and the Steam game folder.
# Set FM_USER_DATA or FM_GAME to use other locations.

fail() { print -u2 "\n$1"; exit 1 }

fm=${FM_USER_DATA:-"$HOME/Library/Application Support/Sports Interactive/Football Manager 2024"}
game=${FM_GAME:-}

if [[ -z $game ]]; then
  steam="$HOME/Library/Application Support/Steam"
  # Every Steam library is listed in libraryfolders.vdf as: "path"  "<folder>"
  for lib in "$steam" ${(f)"$(sed -nE 's/.*"path"[[:space:]]+"(.*)".*/\1/p' "$steam/steamapps/libraryfolders.vdf" 2>/dev/null)"}; do
    if [[ -d "$lib/steamapps/common/Football Manager 2024/data" ]]; then
      game="$lib/steamapps/common/Football Manager 2024"
      break
    fi
  done
fi
