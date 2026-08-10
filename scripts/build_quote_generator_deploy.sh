#!/usr/bin/env sh
set -eu

# Build the deployed Next.js image from the checked-out source while preserving
# the dependency stage across machines. The registry ref is a BuildKit cache,
# not an image used by Compose at runtime.
#
# Before the first run, authenticate the deployment host with a token that can
# read and write the GHCR package (typically `docker login ghcr.io`).

image="${QUOTE_GENERATOR_IMAGE:-quotation-generator:local}"
cache_ref="${QUOTE_GENERATOR_BUILD_CACHE:-ghcr.io/vungocnamhust/quotation-landingpage-template-quote-generator:buildcache}"
builder="${QUOTE_GENERATOR_BUILDER:-quotation-deploy}"

if ! docker buildx inspect "$builder" >/dev/null 2>&1; then
  docker buildx create --name "$builder" --driver docker-container --use
else
  docker buildx use "$builder"
fi

docker buildx inspect --bootstrap >/dev/null
docker buildx build \
  --builder "$builder" \
  --load \
  --tag "$image" \
  --file docker/quote-generator/Dockerfile \
  --cache-from "type=registry,ref=$cache_ref" \
  --cache-to "type=registry,ref=$cache_ref,mode=max,compression=zstd" \
  quote-generator
