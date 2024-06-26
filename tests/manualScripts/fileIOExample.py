
##########################################################################
# Copyright 2024 Sparkwave LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##########################################################################

"""
Demonstrates loading, intelligently spliting, and then writing data to
seperate files. Uses a portion of the UCI ML repository census income
dataset (aka Adult).
"""

import sys
import os.path

import nimble
from nimble import match

if __name__ == "__main__":

    # string manipulation to get and make paths
    projectRoot = os.path.dirname(nimble.nimblePath)
    projectData = "https://storage.googleapis.com/nimble/datasets/"
    inFileName = "adult_income_classification_tiny.csv"
    nameSplit = inFileName.rsplit('.')

    # if a directory is given, we will output the split data to that location.
    if len(sys.argv) > 1:
        outDir = sys.argv[1]
    else:
        outDir = os.path.join(projectRoot, "datasets")

    pathOrig = os.path.join(projectData, inFileName)
    pathTrain = os.path.join(outDir, nameSplit[0] + "TRAIN" + ".csv")
    pathTest = os.path.join(outDir, nameSplit[0] + "TEST" + ".csv")

    # we specify that we want a Matrix object returned, and that we want the first row to
    # taken as the featureNames. Given the .csv extension on the path it will infer the
    # format of the file to be loaded, though that could be explicitly specified if desired.
    full = nimble.data(pathOrig, featureNames=True)

    # scrub the set of any string valued data
    full.features.delete(match.anyNonNumeric)

    # demonstrate splitting the data in train and test sets out of place. By default,
    # the distribution of points between the two returned objects is random.
    testFraction = .15
    (trainOutPlace, testOutPlace) = full.trainAndTestSets(testFraction)

    # demonstrate splitting the data into train and test sets in place
    total = len(full.points)
    num = int(round(testFraction * total))
    testInPlace = full.points.extract(start=0, end=total-1, number=num, randomize=True)
    trainInPlace = full

    # the two methods yield comparable results
    assert len(testInPlace.points) == num
    assert len(trainInPlace.points) == total - num
    assert len(testInPlace.points) == len(testOutPlace.points)
    assert len(trainInPlace.points) == len(trainOutPlace.points)

    # output the split and normalized sets for later usage
    trainInPlace.save(pathTrain, fileFormat='csv', includeNames=True)
    testInPlace.save(pathTest, fileFormat='csv', includeNames=True)
