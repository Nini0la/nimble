"""
Similarity calculations.
"""

import numpy as np

import nimble
from nimble.exceptions import InvalidArgumentType, InvalidArgumentValue
from nimble.calculate.loss import _validatePredictedAsLabels
from nimble.calculate.loss import fractionIncorrect
from nimble.calculate.loss import varianceFractionRemaining
from nimble.core.data._dataHelpers import createDataNoValidation

def cosineSimilarity(knownValues, predictedValues):
    """
    Calculate the cosine similarity between known and predicted values.
    """
    _validatePredictedAsLabels(predictedValues)
    if not isinstance(knownValues, nimble.core.data.Base):
        msg = "knownValues must be derived class of nimble.core.data.Base"
        raise InvalidArgumentType(msg)

    known = knownValues.copy(to="numpy array").flatten()
    predicted = predictedValues.copy(to="numpy array").flatten()

    numerator = (np.dot(known, predicted))
    denominator = (np.linalg.norm(known) * np.linalg.norm(predicted))

    return numerator / denominator


cosineSimilarity.optimal = 'max'


def correlation(X, X_T=None):
    """
    Calculate the Pearson correlation coefficients between points in X.
    If X_T is not provided, a copy of X will be made in this function.
    """
    # pylint: disable=invalid-name
    if X_T is None:
        X_T = X.T
    stdVector = X.points.statistics('populationstd')
    stdVector_T = stdVector.T

    cov = covariance(X, X_T, False)
    stdMatrix = stdVector.matrixMultiply(stdVector_T)
    ret = cov / stdMatrix

    return ret


def covariance(X, X_T=None, sample=True):
    """
    Calculate the covariance between points in X. If X_T is not
    provided, a copy of X will be made in this function.
    """
    # pylint: disable=invalid-name
    if X_T is None:
        X_T = X.T
    pointMeansVector = X.points.statistics('mean')
    fill = lambda x: [x[0]] * len(X.features)
    pointMeans = pointMeansVector.points.calculate(fill, useLog=False)
    pointMeans_T = pointMeans.T

    XminusEofX = X - pointMeans
    X_TminusEofX_T = X_T - pointMeans_T

    # doing sample covariance calculation
    if sample:
        divisor = len(X.features) - 1
    # doing population covariance calculation
    else:
        divisor = len(X.features)

    ret = (XminusEofX.matrixMultiply(X_TminusEofX_T)) / divisor
    return ret


def fractionCorrect(knownValues, predictedValues):
    """
    Calculate how many values in predictedValues are equal to the
    values in the corresponding positions in knownValues. The return
    will be a float between 0 and 1 inclusive.
    """
    return 1 - fractionIncorrect(knownValues, predictedValues)


fractionCorrect.optimal = 'max'


def rSquared(knownValues, predictedValues):
    """
    Calculate the r-squared (or coefficient of determination) of the
    predictedValues given the knownValues. This will be equal to 1 -
    nimble.calculate.varianceFractionRemaining() of the same inputs.

    """
    return 1.0 - varianceFractionRemaining(knownValues, predictedValues)


rSquared.optimal = 'max'


def confusionMatrix(knownValues, predictedValues, labels=None,
                    convertCountsToFractions=False):
    """
    Generate a confusion matrix for known and predicted label values.

    The confusion matrix contains the counts of observations that
    occurred for each known/predicted pair. Features represent the
    known classes and points represent the predicted classes.
    Optionally, these can be output as fractions instead of counts.

    Parameters
    ----------
    knownValues : nimble Base object
        The ground truth labels collected for some data.
    predictedValues : nimble Base object
        The labels predicted for the same data.
    labels : dict, list
        As a dictionary, a mapping of from the value in ``knownLabels``
        to a more specific label. A list may also be used provided the
        values in ``knownLabels`` represent an index to each value in
        the list. The labels will be used to create the featureNames and
        pointNames with the prefixes `known_` and `predicted_`,
        respectively.  If labels is None, the prefixes will be applied
        directly to the unique values found in ``knownLabels``.
    convertCountsToFractions : bool
        If False, the default, elements are counts. If True, the counts
        are converted to fractions by dividing by the total number of
        observations.

    Returns
    -------
    Base
        A confusion matrix nimble object matching the type of
        ``knownValues``.

    Notes
    -----
    Metrics for binary classification based on a confusion matrix,
    like truePositive, recall, precision, etc., can also be found in
    the nimble.calculate module.

    Examples
    --------
    Confusion matrix with and without alternate labels.

    >>> known = [[0], [1], [2],
    ...          [0], [1], [2],
    ...          [0], [1], [2],
    ...          [0], [1], [2]]
    >>> pred = [[0], [1], [2],
    ...         [0], [1], [2],
    ...         [0], [1], [2],
    ...         [1], [0], [2]]
    >>> knownObj = nimble.data('Matrix', known)
    >>> predObj = nimble.data('Matrix', pred)
    >>> cm = confusionMatrix(knownObj, predObj)
    >>> cm
    <Matrix 3pt x 3ft
                   known_0 known_1 known_2
                 ┌────────────────────────
     predicted_0 │    3       1       0
     predicted_1 │    1       3       0
     predicted_2 │    0       0       4
     >
    >>> labels = {0: 'cat', 1: 'dog', 2: 'fish'}
    >>> cm = confusionMatrix(knownObj, predObj, labels=labels)
    >>> cm
    <Matrix 3pt x 3ft
                      known_cat known_dog known_fish
                    ┌───────────────────────────────
      predicted_cat │     3         1         0
      predicted_dog │     1         3         0
     predicted_fish │     0         0         4
     >

    Label objects can have string values and here we output fractions.

    >>> known = [['cat'], ['dog'], ['fish'],
    ...          ['cat'], ['dog'], ['fish'],
    ...          ['cat'], ['dog'], ['fish'],
    ...          ['cat'], ['dog'], ['fish']]
    >>> pred = [['cat'], ['dog'], ['fish'],
    ...         ['cat'], ['dog'], ['fish'],
    ...         ['cat'], ['dog'], ['fish'],
    ...         ['dog'], ['cat'], ['fish']]
    >>> knownObj = nimble.data('Matrix', known)
    >>> predObj = nimble.data('Matrix', pred)
    >>> cm = confusionMatrix(knownObj, predObj,
    ...                      convertCountsToFractions=True)
    >>> cm
    <Matrix 3pt x 3ft
                      known_cat known_dog known_fish
                    ┌───────────────────────────────
      predicted_cat │   0.250     0.083     0.000
      predicted_dog │   0.083     0.250     0.000
     predicted_fish │   0.000     0.000     0.333
     >
    """
    if not (isinstance(knownValues, nimble.core.data.Base)
            and isinstance(predictedValues, nimble.core.data.Base)):
        msg = 'knownValues and predictedValues must be nimble data objects'
        raise InvalidArgumentType(msg)
    if not knownValues.shape[1] == predictedValues.shape[1] == 1:
        msg = 'knownValues and predictedValues must each be a single feature'
        raise InvalidArgumentValue(msg)
    if knownValues.shape[0] != predictedValues.shape[0]:
        msg = 'knownValues and predictedValues must have the same number of '
        msg += 'points'
        raise InvalidArgumentValue(msg)
    if not isinstance(labels, (type(None), dict, list)):
        msg = 'labels must be a dictionary mapping values from knownValues to '
        msg += 'a label or a list if the unique values in knownValues are in '
        msg += 'the range 0 to len(labels)'
        raise InvalidArgumentType(msg)

    if isinstance(labels, dict):
        confusionMtx, knownLabels = _confusionMatrixWithLabelsDict(
            knownValues, predictedValues, labels)
    elif labels is not None:
        confusionMtx, knownLabels = _confusionMatrixWithLabelsList(
            knownValues, predictedValues, labels)
    else:
        confusionMtx, knownLabels = _confusionMatrixNoLabels(
            knownValues, predictedValues)

    if convertCountsToFractions:
        confusionMtx = confusionMtx.astype(float) / len(knownValues.points)

    asType = knownValues.getTypeString()
    fNames = ['known_' + str(label) for label in knownLabels]
    pNames = ['predicted_' + str(label) for label in knownLabels]

    return createDataNoValidation(asType, confusionMtx, pNames, fNames,
                                  reuseData=True)

###########
# Helpers #
###########

_intMapCache = {} # increase efficiency by caching
def _mapInt(val):
    if val in _intMapCache:
        return _intMapCache[val]

    try:
        if val % 1 == 0:
            _intMapCache[val] = int(val)
            return int(val)
        return val
    except TypeError:
        return val

def _validateIndex(idx, numLabels, sourceArg):
    errorType = None
    if not isinstance(idx, int):
        errorType = InvalidArgumentValue
    elif not 0 <= idx < numLabels:
        errorType = IndexError
    if errorType is not None:
        msg = '{arg} contains an invalid value: {val}. All values must be '
        msg += 'equal to integers 0 through {lastIdx} (inclusive) indicating '
        msg += 'an index value for the labels argument'
        msg = msg.format(arg=sourceArg, val=idx, lastIdx=numLabels-1)
        raise errorType(msg)

def _confusionMatrixWithLabelsList(knownValues, predictedValues, labels):
    numLabels = len(labels)
    toFill = np.zeros((numLabels, numLabels), dtype=int)
    validLabels = set() # to prevent repeated validation of same label
    for kVal, pVal in zip(knownValues, predictedValues):
        kVal = _mapInt(kVal)
        if kVal not in validLabels:
            _validateIndex(kVal, numLabels, 'knownValues')
            validLabels.add(kVal)
        pVal = _mapInt(pVal)
        if pVal not in validLabels:
            _validateIndex(pVal, numLabels, 'predictedValues')
            validLabels.add(pVal)
        toFill[pVal, kVal] += 1

    return toFill, labels

def _validateKey(key, labels, sourceArg):
    if key not in labels:
        msg = '{key} was found in {arg} but is not a key in labels'
        raise KeyError(msg.format(key=key, arg=sourceArg))

def _confusionMatrixWithLabelsDict(knownValues, predictedValues, labels):
    sortedLabels = sorted(labels)
    numLabels = len(labels)
    toFill = np.zeros((numLabels, numLabels), dtype=int)
    labelsIdx = {}
    for kVal, pVal in zip(knownValues, predictedValues):
        # trigger KeyError if label not present
        if kVal not in labelsIdx:
            _validateKey(kVal, labels, 'knownValues')
            labelsIdx[kVal] = sortedLabels.index(kVal)
        if pVal not in labelsIdx:
            _validateKey(pVal, labels, 'predictedValues')
            labelsIdx[pVal] = sortedLabels.index(pVal)
        toFill[labelsIdx[pVal], labelsIdx[kVal]] += 1

    knownLabels = [labels[key] for key in sortedLabels]

    return toFill, knownLabels

def _confusionMatrixNoLabels(knownValues, predictedValues):
    knownLabels = set()
    confusionDict = {}
    # get labels and positions first then we will sort before creating matrix
    for kVal, pVal in zip(knownValues, predictedValues):
        knownLabels.add(kVal)
        if (kVal, pVal) in confusionDict:
            confusionDict[(kVal, pVal)] += 1
        else:
            confusionDict[(kVal, pVal)] = 1

    knownLabels = sorted(list(map(_mapInt, knownLabels)))
    labelsIdx = {}
    length = len(knownLabels)
    toFill = np.zeros((length, length), dtype=int)

    for (kVal, pVal), count in confusionDict.items():
        if kVal not in labelsIdx:
            labelsIdx[kVal] = knownLabels.index(kVal)
        if pVal not in labelsIdx:
            labelsIdx[pVal] = knownLabels.index(pVal)
        toFill[labelsIdx[pVal], labelsIdx[kVal]] = count

    return toFill, knownLabels
