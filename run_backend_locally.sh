#!/bin/sh

set -e

cd "`dirname "$0"`"

for var in UMLS_EMAIL UMLS_USERNAME UMLS_PASSWORD; do
    if test -z "`eval echo \\$$var`"; then
        echo "Environment variable $var is not set." >&2
        exit 1
    fi
done

if ! test -d .ve; then
    virtualenv -p python3 .ve
fi

METAMAP_CLIENT_JAR="`pwd`/metamap_client.jar"
JOB_OUTPUT_DIR="`pwd`/job_output"
export METAMAP_CLIENT_JAR JOB_OUTPUT_DIR

if ! test -f "$METAMAP_CLIENT_JAR"; then
    echo "$METAMAP_CLIENT_JAR does not exist" >&2
    echo 'Please run setup.sh' >&2
    exit 2
fi

mkdir -p "$JOB_OUTPUT_DIR"

. ./.ve/bin/activate
python backend/backend.py
