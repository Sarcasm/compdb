#!/bin/bash

set -o errexit

: "${USER?Please set USER}"
: "${GROUP?Please set GROUP to the user group using $(id -gn)}"
: "${UID?Please set UID}"
: "${GID?Please set GID}"

groupadd --gid "$GID" "$GROUP"
useradd --create-home --shell /bin/bash --gid "$GROUP" --uid "$UID" "$USER"

export HOME="/home/$USER"
cd "$HOME"
exec chpst -u "$USER" "$@"

