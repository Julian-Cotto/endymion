#!/usr/bin/env bash
set -euo pipefail

: "${ACR_LOGIN_SERVER:?ACR_LOGIN_SERVER is required}"
: "${IMAGE_NAME:=portal-registry}"
: "${IMAGE_TAG:?IMAGE_TAG is required}"

docker build -t "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}" .
docker push "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}"
