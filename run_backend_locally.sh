#!/bin/sh

set -e

cd "`dirname "$0"`"

for var in UMLS_EMAIL UMLS_USERNAME UMLS_PASSWORD; do
    if test -z "`eval echo \\$$var`"; then
        echo "Environment variable $var is not set." >&2
        exit 1
    fi
done

test -d .ve || virtualenv -p python3 .ve
. ./.ve/bin/activate
(cd backend && pip -q install -r requirements.txt)

METAMAP_CLIENT_JAR="`pwd`/metamap_worker/metamap_worker.jar"
JOB_INPUT_DIR="`pwd`/job_input"
JOB_OUTPUT_DIR="`pwd`/job_output"
UMLS_SEMANTIC_TYPES_CSV="`pwd`/data/umls_semantic_types.csv"
export METAMAP_CLIENT_JAR JOB_INPUT_DIR JOB_OUTPUT_DIR UMLS_SEMANTIC_TYPES_CSV

if ! test -f "$METAMAP_CLIENT_JAR"; then
    echo "$METAMAP_CLIENT_JAR does not exist" >&2
    echo 'Please run setup.sh' >&2
    exit 2
fi

mkdir -p "$JOB_INPUT_DIR" "$JOB_OUTPUT_DIR"

cleanup()
{
    kill "$backend_pid" "$worker_pid" 2>/dev/null
}

trap cleanup EXIT

echo 'Starting web backend...'
gunicorn -w 4 -b :8080 backend.backend:app > backend.log 2>&1 &
backend_pid=$!


echo 'Starting metamap_worker...'
java -jar metamap_worker/metamap_worker.jar > worker.log 2>&1 &
worker_pid=$!

check_child() {
    local service=$1
    local pid=$2

    if [ -z "$pid" ]; then
        return
    fi

    if ! kill -0 $pid 2> /dev/null; then
        echo "$service unexpectedly stopped." >&2
        echo "See `pwd`/$service.log for details." >&2
        exit 3
    fi
}

while true; do
    check_child 'backend' $backend_pid
    check_child 'worker' $worker_pid

    sleep .1
done
