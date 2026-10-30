#!/bin/sh
# Builds dist/ReSeason-<version>.zip from the current commit plus the six modules in data/.
# Usage: ./release.sh 1.0.0
set -eu
cd "$(dirname "$0")"
name="ReSeason-$1"

rm -rf "dist/$name" "dist/$name.zip"
mkdir -p "dist/$name"
git archive HEAD | tar -x -C "dist/$name"
cp data/ReSeason*.fmf "dist/$name/data/"
(cd "dist/$name/data" && grep '  ReSeason' checksums.txt | shasum -a 256 -c --quiet)
(cd dist && zip -qry "$name.zip" "$name")
shasum -a 256 "dist/$name.zip"
