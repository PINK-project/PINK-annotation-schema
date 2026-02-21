#!/bin/sh

THISDIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-$0}";)" &> /dev/null && pwd;)"
ROOTDIR="$(dirname -- "$(dirname -- "$THISDIR")")"


ontograph \
    --root=Model \
    --leaves=StatisticalModel,DataBasedModel,PhysicsBasedModel \
    --format=png \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-top.png"

ontograph \
    --root=PhysicsBasedModel \
    --format=png \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-PhysicsBasedModel.png"

ontograph \
    --root=StatisticalModel \
    --format=png \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-StatisticalModel.png"

ontograph \
    --root=DataBasedModel \
    --leaves=NaturalLanguageProcessing,MachineLearning \
    --format=png \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-DataBasedModel.png"

ontograph \
    --root=NaturalLanguageProcessing \
    --format=png \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-NaturalLanguageProcessing.png"

ontograph \
    --root=MachineLearning \
    --leaves=DeepLearning,SupervisedLearning \
    --format=png \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-MachineLearning.png"

ontograph \
    --root=DeepLearning \
    --format=png \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-DeepLearning.png"

ontograph \
    --root=SupervisedLearning \
    --format=png \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-SupervisedLearning.png"
