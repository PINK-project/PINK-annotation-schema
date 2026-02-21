#!/bin/sh

THISDIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-$0}";)" &> /dev/null && pwd;)"
ROOTDIR="$(dirname -- "$(dirname -- "$THISDIR")")"


ontograph \
    --root=Model \
    --leaves=StatisticalModel,DataBasedModel,PhysicsBasedModel \
    --format=svg \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-top.svg"

ontograph \
    --root=PhysicsBasedModel \
    --format=svg \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-PhysicsBasedModel.svg"

ontograph \
    --root=StatisticalModel \
    --format=svg \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-StatisticalModel.svg"

ontograph \
    --root=DataBasedModel \
    --leaves=NaturalLanguageProcessing,MachineLearning \
    --format=svg \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-DataBasedModel.svg"

ontograph \
    --root=NaturalLanguageProcessing \
    --format=svg \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-NaturalLanguageProcessing.svg"

ontograph \
    --root=MachineLearning \
    --leaves=DeepLearning,SupervisedLearning \
    --format=svg \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-MachineLearning.svg"

ontograph \
    --root=DeepLearning \
    --format=svg \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-DeepLearning.svg"

ontograph \
    --root=SupervisedLearning \
    --format=svg \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-SupervisedLearning.svg"
