#!/bin/sh
# Once for each person, at their first login: a Projects folder with the
# cheat sheet in it, and git set to name new branches main.
set -eu
mkdir -p "$HOME/Projects"
if [ ! -e "$HOME/Projects/README.md" ]; then
	cp /usr/share/foundry/cheatsheet.md "$HOME/Projects/README.md"
fi
git config --global init.defaultBranch main
