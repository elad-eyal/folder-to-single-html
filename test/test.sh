#!/bin/bash

if [[ "$1" == "" ]]; then
    exec $0 --help
fi

if [[ "$1" == "--help" ]]; then
    echo "$0 --list-tests"
    echo "$0 --list-tests-json"
    echo "$0 <testname>"
    echo "$0 --all"
    echo ""
    echo "set environment variable IMAGE to the container image to check, or leave empty for current codebase."
    exit 9
fi

if [[ "$1" == "--all" ]]; then
    $0 --list-tests | xargs -i $0 {}
    exit 0
fi

if [[ "$1" == "--list-tests-json" ]]; then
    test/test.sh --list-tests | jq -R -s -c 'split("\n")[:-1]'
    exit 0
fi

cd "$(dirname "$0")"

if [[ "$1" == "--list-tests" ]]; then
    cd src
    find * -maxdepth 0 -type d
    exit 0
fi

IMAGE=${IMAGE-$(docker build -q ..)}
HOSTNAME=$(command ip route get 1 | sed -n 's/^.*src \([0-9.]*\) .*$/\1/p')

mkdir -p artifacts/$1
rm -fr artifacts/$1
mkdir -p artifacts/$1
docker run -v $PWD/src/$1:/in:ro $IMAGE -P > artifacts/$1/$1_output.html

docker rm -f httpd || true
docker run -d --name httpd -p 1300:3000 -v $PWD:/home/static/www:ro lipanski/docker-static-website
trap 'docker rm -f httpd || true' EXIT


while IFS= read -r -d '' filename
do
    REF_FILENAME=artifacts/$1/${filename}_ref
    DUT_FILENAME=artifacts/$1/${filename}_dut
    docker run -v ${PWD}:/usr/src/app/out --rm nevermendel/chrome-headless-screenshots "http://${HOSTNAME}:1300/www/src/$1/${filename}" --filename ${REF_FILENAME} --delay 3000
    docker run -v ${PWD}:/usr/src/app/out --rm nevermendel/chrome-headless-screenshots "http://${HOSTNAME}:1300/www/artifacts/$1/$1_output.html?path=${filename}" --filename ${DUT_FILENAME} --delay 3000
    if ! [[ -s $REF_FILENAME.png  ]]; then
        echo "Unable to create $REF_FILENAME" >> /dev/stderr
        exit 5
    fi
    if ! [[ -s $DUT_FILENAME.png  ]]; then
        echo "Unable to create $REF_FILENAME" >> /dev/stderr
        exit 5
    fi
    if ! [[ $(md5sum < $REF_FILENAME.png ) == $(md5sum < $DUT_FILENAME.png ) ]]; then
        echo "FAIL: Screenshot mismatch for URL ${filename}. " >> /dev/stderr
        exit 4
    fi
    
done < <(cd src/$1 && find * -type f -name '*.html' -print0)

