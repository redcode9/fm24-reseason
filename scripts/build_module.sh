#!/bin/sh
# Developer rebuild only; never replaces the pinned release binary.
set -eu
cd "$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
mkdir -p build
target=build/libfm24_awards_init_rebuilt.dylib
if [ -e "$target" ]; then
    echo "Build output exists; preserve or move it before rebuilding." >&2
    exit 1
fi
clang -arch arm64 -mmacosx-version-min=12.0 -Wall -Wextra -Werror -O2 \
    -dynamiclib -fvisibility=hidden \
    -Wl,-install_name,@rpath/libfm24_awards_init_rebuilt.dylib \
    toolkit/source/awards_init.c toolkit/source/conversion_arm64.S -o "$target"
codesign --force --sign - "$target"
echo "Built $target. This rebuild has not been qualified as a release binary."
