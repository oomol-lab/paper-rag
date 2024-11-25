#!/bin/bash
set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

cd browser
pnpm i
pnpm build
cd ../

APP_NAME=PaperRAG
DIST=./dist/${APP_NAME}

rm -rf ./dist
mkdir -p ${DIST}

cp requirements.txt ${DIST}/requirements.txt
cp main.py ${DIST}/main.py
cp config.yaml ${DIST}/config.yaml
cp -r browser.lib ${DIST}/browser.lib
cp -r index_package ${DIST}/index_package
cp -r sqlite3_pool ${DIST}/sqlite3_pool
cp -r server ${DIST}/server
cp -r build/start.bat ${DIST}/start.bat

mkdir -p ${DIST}/data

cd $SCRIPT_DIR/../dist
zip -r ./${APP_NAME}-win-amd64.zip ${APP_NAME}