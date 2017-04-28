#!/bin/bash

set -o errexit

LOCAL_PATH=$(cd $(dirname "${BASH_SOURCE[0]}") && pwd)
COMPDB_PATH=$(cd ${LOCAL_PATH}/../../.. && pwd)
IMAGE_NAME=sarcasm/compdb-ubuntu-trusty

if [[ $# -ne 1 ]]; then
    1>&2 cat <<EOF
Usage: $0 SCRIPT

SCRIPT argument is required.
EOF
    exit 1
fi

USER_SCRIPT=$(realpath "$1")

>/dev/null docker build -q -t ${IMAGE_NAME} "${LOCAL_PATH}/ubuntu-trusty"

tempdir=$(mktemp -d --tmpdir -t compdb_docker_trusty.XXXXXXXXXX)
>/dev/null pushd "$tempdir"

cp "$USER_SCRIPT" script.sh

cat <<'EOF' > wrapper.sh
#!/bin/bash
set -o errexit
tar xaf /data/compdb.tar.gz
cd compdb
exec /data/script.sh
EOF
chmod +x wrapper.sh

# TODO: verify that removed files (in the index) are not present in the archive
>/dev/null pushd "$COMPDB_PATH"
gitref=$(git stash create)
git archive --prefix=compdb/ -o "${tempdir}/compdb.tar.gz" ${gitref:-HEAD}
>/dev/null popd

docker run \
    --interactive \
    --tty \
    --rm \
    --env USER=user \
    --env GROUP=grp \
    --env UID=$(id -u) \
    --env GID=$(id -g) \
    --volume $(pwd):/data \
    ${IMAGE_NAME} \
    /data/wrapper.sh

>/dev/null popd

rm -rf "$tempdir"
