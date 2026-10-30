#!/bin/zsh
# Copies the ReSeason files into FM24 and checks the whole setup. Safe to run again.
set -eu
cd "${0:A:h}"
source mac/common.zsh

editor="$fm/editor data"
italy="sortitoutsi.net FM24 Data Update - Italy (2026 Start).fmf"
helper="$game/data/database/db/2430/edt/permanent"

[[ -d $fm ]] || fail "Can't find $fm
Start FM24 once so it creates that folder, then run this again."

mods=(data/*.fmf(N))
(( $#mods )) || fail "The ReSeason modules are missing from the data folder.
Download ReSeason from the Releases page, not with the green Code button."

mkdir -p "$editor"
cp -f $mods "$editor/"
print "Copied $#mods ReSeason modules into editor data."

# The ReSeason Italy module replaces this file; loading both breaks the Italian leagues.
if [[ -f "$editor/$italy" ]]; then
  mv -f "$editor/$italy" "$editor/$italy.disabled"
  print "Disabled the sortitoutsi Italy file (ReSeason replaces it)."
fi

if [[ -n $game && -d $helper ]]; then
  cp -f data/FM24_History_Ahron_Retention.ddt "$helper/"
  print "Copied the retention helper into the game folder."
else
  print "Skipped the retention helper: FM24 game folder not found."
  print "If FM24 isn't in Steam, run: FM_GAME='/path/to/Football Manager 2024' ./Install.command"
fi

print "\nChecking editor data against the tested setup..."
typeset -A known
problems=0
while IFS= read -r line; do
  sum=${line%%  *} name=${line#*  }
  known[$name]=1
  if [[ ! -f "$editor/$name" ]]; then
    print "  missing:   $name"; (( ++problems ))
  elif [[ $(shasum -a 256 "$editor/$name") != "$sum "* ]]; then
    print "  different: $name"; (( ++problems ))
  fi
done < data/checksums.txt

extra=()
for f in "$editor"/*.fmf(N:t); do (( ${+known[$f]} )) || extra+=$f; done

if (( problems )); then
  print "\n$problems of ${#known} files are missing or not the tested version."
  print "Get the sortitoutsi 2026 start update (see README). A newer update should work, but it hasn't been tested."
else
  print "\nAll ${#known} files match the tested setup."
fi
if (( $#extra )); then
  print "\nOther editor data files found. Untick them when you create the career:"
  print -l "  "$^extra
fi
print "\nDone. Next: open New Career.command to start your 2026/27 career."
