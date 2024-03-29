#!/bin/bash

if [[ "$1" == "" ]]; then
    exec $0 --help
fi

if [[ "$1" == "--help" ]]; then
    echo "$0 --list-tests"
    echo "$0 <testname>"
    echo "$0 --all"
    echo ""
    echo "set environment variable IMAGE to the container image to check, or leave empty for current codebase."
    exit 9
fi

cd "$(dirname "$0")"

if [[ "$1" == "--list-tests" ]]; then
    find * -maxdepth 0 -type d
    exit 0
fi


if [[ "$1" == "--all" ]]; then
    $0 --list-tests | xargs -i $0 {}
    exit 0
fi

IMAGE=${IMAGE-$(docker build -q ..)}
HOSTNAME=$(command ip route get 1 | sed -n 's/^.*src \([0-9.]*\) .*$/\1/p')

docker run -v $PWD/$1:/src:ro $IMAGE -P > $1_output.html

docker rm -f httpd url-to-png || true
docker run -d --name httpd -p 1300:3000 -v $PWD:/home/static/www:ro lipanski/docker-static-website
docker run -d --name url-to-png -p 1303:3000 jasonraimondi/url-to-png


while IFS= read -r -d '' filename
do
    REF_FILENAME=screenshot_ref_${filename}.png
    DUT_FILENAME=screenshot_dut_${filename}.png
    wget "http://localhost:1303?url=http://${HOSTNAME}:1300/www/$1/${filename}&width=600&height=2000" -O ${REF_FILENAME}
    wget "http://localhost:1303?url=http://${HOSTNAME}:1300/www/$1_output.html%3Fpath=${filename}&width=600&height=2000" -O ${DUT_FILENAME}
    if ! [[ -s $REF_FILENAME  ]]; then
        echo "Unable to create $REF_FILENAME" >> /dev/stderr
        exit 5
    fi
    if ! [[ -s $DUT_FILENAME  ]]; then
        echo "Unable to create $REF_FILENAME" >> /dev/stderr
        exit 5
    fi
    if ! [[ $(md5sum < $REF_FILENAME ) == $(md5sum < $DUT_FILENAME) ]]; then
        echo "FAIL: Screenshot mismatch for URL ${filename}. " >> /dev/stderr
        exit 4
    fi
    
done < <(cd $1 && find * -type f -name '*.html' -print0)

