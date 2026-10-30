#!/bin/sh
# Rebuilds the engine module from source into build/. mac/reseason.dylib is the build tested in game.
set -eu
cd "$(dirname "$0")/.."
mkdir -p build
clang -arch arm64 -mmacosx-version-min=12.0 -Wall -Wextra -Werror -O2 -dynamiclib -fvisibility=hidden \
  mac/awards_init.c mac/conversion_arm64.S -o build/reseason.dylib
codesign --force --sign - build/reseason.dylib
echo build/reseason.dylib
