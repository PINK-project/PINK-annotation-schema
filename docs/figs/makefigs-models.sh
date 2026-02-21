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
    --leaves=NaturalLanguageProcessingModel,MachineLearningModel \
    --format=png \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-DataBasedModel.png"

ontograph \
    --root=NaturalLanguageProcessingModel \
    --format=png \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-NaturalLanguageProcessingModel.png"

ontograph \
    --root=MachineLearningModel \
    --leaves=DeepLearningModel,SupervisedLearningModel \
    --format=png \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-MachineLearningModel.png"

ontograph \
    --root=DeepLearningModel \
    --format=png \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-DeepLearningModel.png"

ontograph \
    --root=SupervisedLearningModel \
    --format=png \
    "$ROOTDIR/models.ttl" \
    "$THISDIR/models-SupervisedLearningModel.png"
