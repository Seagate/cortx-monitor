#!/bin/bash

set -e

default_name="Seagate SSPL RAS"
default_email="eos.ras@seagate.com"
default_comment="EES RAS SSPL developer RPM signing key"

if [ "$#" -eq 0 ]; then
    key_name="${default_name}"
    key_email="${default_email}"
    key_comment="${default_comment}"
elif [ "$#" -eq 3 ]; then
    key_name="$1"
    key_email="$2"
    key_comment="$3"
else
    1>&2 echo "Error: Unexpected number of arguments: $#"
    1>&2 echo "Usage:"
    1>&2 echo "${0}"
    1>&2 echo "OR"
    1>&2 echo "${0} <key-name> <key-email> <key-comment>"
    exit 1
fi

./jenkins/make_gpg_key "${key_name}" "${key_email}" "${key_comment}"

