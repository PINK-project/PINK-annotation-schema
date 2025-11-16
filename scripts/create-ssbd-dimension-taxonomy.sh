#!/bin/sh

rootdir=$(git rev-parse --show-toplevel)

datadoc \
    --prefix "pink=https://w3id.org/pink#" \
    --prefix "owl=http://www.w3.org/2002/07/owl#" \
    add \
    --dump=$rootdir/ssbd_dimensions.ttl \
    $rootdir/sources/ssbd_dimension_taxonomy.csv
