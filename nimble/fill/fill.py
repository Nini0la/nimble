"""
Variety of functions to replace values in data with other values
"""
import functools

import numpy

import nimble
from nimble.match import convertMatchToFunction
from nimble.match import anyValues
from nimble.exceptions import InvalidArgumentValue

def booleanElementMatch(vector, match):
    if not isinstance(match, nimble.data.Base):
        match = convertMatchToFunction(match)
        return vector.matchingElements(match, useLog=False)
    return match

def constant(vector, match, constantValue):
    """
    Fill matched values with a constant value

    Parameters
    ----------
    vector : nimble point or feature
        A nimble Base object containing one point or feature.
    match : value or function
        * value - The value which should be filled if it occurs in the
          data.
        * function - Input a value and return True if that value should
          be filled. Nimble offers common use-case functions in its
          match module.
    constantValue : value
        The value which will replace any matching values.

    Returns
    -------
    list
        The vector values with the ``constantValue`` replacing the
        ``match`` values.

    See Also
    --------
    nimble.match

    Examples
    --------
    Match a value.

    >>> raw = [1, 'na', 3, 'na', 5]
    >>> data = nimble.createData('Matrix', raw)
    >>> constant(data, 'na', 0)
    Matrix(
        [[1.000 0.000 3.000 0.000 5.000]]
        )

    Match using a function from nimble's match module.

    >>> from nimble import match
    >>> raw = [1, 0, 3, 0, 5]
    >>> data = nimble.createData('Matrix', raw)
    >>> constant(data, match.zero, 99)
    Matrix(
        [[1.000 99.000 3.000 99.000 5.000]]
        )
    """
    toFill = booleanElementMatch(vector, match)

    def filler(vec):
        return [constantValue if fill else val
                for val, fill in zip(vec, toFill)]

    if len(vector.points) == 1:
        return vector.points.calculate(filler, useLog=False)
    return vector.features.calculate(filler, useLog=False)

def mean(vector, match):
    """
    Fill matched values with the mean.

    The calculation of the mean will ignore any matched values, but all
    unmatched values must be numeric. If all the values are a match the
    mean cannot be calculated.

    Parameters
    ----------
    vector : nimble point or feature
        A nimble Base object containing one point or feature.
    match : value or function
        * value - The value which should be filled if it occurs in the
          data.
        * function - Input a value and return True if that value should
          be filled. Nimble offers common use-case functions in its
          match module.

    Returns
    -------
    list
        The vector values with the mean replacing the ``match`` values.

    See Also
    --------
    median, mode, nimble.match

    Examples
    --------
    Match a value.

    >>> raw = [1, 'na', 3, 'na', 5]
    >>> data = nimble.createData('Matrix', raw)
    >>> mean(data, 'na')
    Matrix(
        [[1.000 3.000 3.000 3.000 5.000]]
        )

    Match using a function from nimble's match module.

    >>> from nimble import match
    >>> raw = [6, 0, 2, 0, 4]
    >>> data = nimble.createData('Matrix', raw)
    >>> mean(data, match.zero)
    Matrix(
        [[6.000 4.000 2.000 4.000 4.000]]
        )
    """
    return statsBackend(vector, match, 'mean', nimble.calculate.mean)

def median(vector, match):
    """
    Fill matched values with the median.

    The calculation of the median will ignore any matched values, but
    all unmatched values must be numeric. If all the values are a match
    the median cannot be calculated.

    Parameters
    ----------
    vector : nimble point or feature
        A nimble Base object containing one point or feature.
    match : value or function
        * value - The value which should be filled if it occurs in the
          data.
        * function - Input a value and return True if that value should
          be filled. Nimble offers common use-case functions in its
          match module.

    Returns
    -------
    list
        The vector values with the median replacing the ``match``
        values.

    See Also
    --------
    mean, mode, nimble.match

    Examples
    --------
    Match a value.

    >>> raw = [1, 'na', 3, 'na', 5]
    >>> data = nimble.createData('Matrix', raw)
    >>> median(data, 'na')
    Matrix(
        [[1.000 3.000 3.000 3.000 5.000]]
        )

    Match using a function from nimble's match module.

    >>> from nimble import match
    >>> raw = [6, 0, 2, 0, 4]
    >>> data = nimble.createData('Matrix', raw)
    >>> median(data, match.zero)
    Matrix(
        [[6.000 4.000 2.000 4.000 4.000]]
        )
    """
    return statsBackend(vector, match, 'median', nimble.calculate.median)

def mode(vector, match):
    """
    Fill matched values with the mode.

    The calculation of the mode will ignore any matched values. If all
    the values are a match the mean cannot be calculated.

    Parameters
    ----------
    vector : nimble point or feature
        A nimble Base object containing one point or feature.
    match : value or function
        * value - The value which should be filled if it occurs in the
          data.
        * function - Input a value and return True if that value should
          be filled. Nimble offers common use-case functions in its
          match module.

    Returns
    -------
    list
        The vector values with the mode replacing the ``match`` values.

    See Also
    --------
    mean, median, nimble.match

    Examples
    --------
    Match a value.

    >>> raw = [1, 'na', 1, 'na', 5]
    >>> data = nimble.createData('Matrix', raw)
    >>> mode(data, 'na')
    Matrix(
        [[1.000 1.000 1.000 1.000 5.000]]
        )

    Match using a function from nimble's match module.

    >>> from nimble import match
    >>> raw = [6, 6, 2, 0, 0]
    >>> data = nimble.createData('Matrix', raw)
    >>> mode(data, match.zero)
    Matrix(
        [[6.000 6.000 2.000 6.000 6.000]]
        )
    """
    return statsBackend(vector, match, 'mode', nimble.calculate.mode)

def forwardFill(vector, match):
    """
    Fill matched values with the previous unmatched value.

    Each matching value will be filled with the first non-matching value
    occurring prior to the matched value. An exception will be raised if
    the first value is a match, since there is not a valid value to
    reference.

    Parameters
    ----------
    vector : nimble point or feature
       A nimble Base object containing one point or feature.
    match : value or function
        * value - The value which should be filled if it occurs in the
          data.
        * function - Input a value and return True if that value should
          be filled. Nimble offers common use-case functions in its
          match module.

    Returns
    -------
    list
        The vector values with the forward filled values replacing the
        ``match`` values.

    See Also
    --------
    backwardFill, nimble.match

    Examples
    --------
    Match a value.

    >>> raw = [1, 'na', 3, 'na', 5]
    >>> data = nimble.createData('Matrix', raw)
    >>> forwardFill(data, 'na')
    Matrix(
        [[1.000 1.000 3.000 3.000 5.000]]
        )

    Match using a function from nimble's match module.

    >>> from nimble import match
    >>> raw = [6, 0, 2, 0, 4]
    >>> data = nimble.createData('Matrix', raw)
    >>> forwardFill(data, match.zero)
    Matrix(
        [[6.000 6.000 2.000 2.000 4.000]]
        )
    """
    toFill = booleanElementMatch(vector, match)
    if toFill[0]:
        msg = directionError('forward fill', vector, 'first')
        raise InvalidArgumentValue(msg)

    def filler(vec):
        ret = []
        for val, fill in zip(vec, toFill):
            if fill:
                ret.append(ret[-1])
            else:
                ret.append(val)
        return ret

    if len(vector.points) == 1:
        return vector.points.calculate(filler, useLog=False)
    return vector.features.calculate(filler, useLog=False)

def backwardFill(vector, match):
    """
    Fill matched values with the next unmatched value.

    Each matching value will be filled with the first non-matching value
    occurring after to the matched value. An exception will be raised if
    the last value is a match, since there is not a valid value to
    reference.

    Parameters
    ----------
    vector : nimble point or feature
        A nimble Base object containing one point or feature.
    match : value or function
        * value - The value which should be filled if it occurs in the
          data.
        * function - Input a value and return True if that value should
          be filled. Nimble offers common use-case functions in its
          match module.

    Returns
    -------
    list
        The vector values with the backward filled values replacing the
        ``match`` values.

    See Also
    --------
    forwardFill, nimble.match

    Examples
    --------
    Match a value.

    >>> raw = [1, 'na', 3, 'na', 5]
    >>> data = nimble.createData('Matrix', raw)
    >>> backwardFill(data, 'na')
    Matrix(
        [[1.000 3.000 3.000 5.000 5.000]]
        )

    Match using a function from nimble's match module.

    >>> from nimble import match
    >>> raw = [6, 0, 2, 0, 4]
    >>> data = nimble.createData('Matrix', raw)
    >>> backwardFill(data, match.zero)
    Matrix(
        [[6.000 2.000 2.000 4.000 4.000]]
        )
    """
    toFill = booleanElementMatch(vector, match)
    if toFill[-1]:
        msg = directionError('backward fill', vector, 'last')
        raise InvalidArgumentValue(msg)

    def filler(vec):
        ret = numpy.empty_like(vector, dtype=numpy.object_)
        numValues = len(vec)
        for i, (val, fill) in enumerate(zip(reversed(vector),
                                            reversed(toFill))):
            idx = numValues - i - 1
            if fill:
                ret[idx] = ret[idx + 1]
            else:
                ret[idx] = val
        return ret

    if len(vector.points) == 1:
        return vector.points.calculate(filler, useLog=False)
    return vector.features.calculate(filler, useLog=False)

def interpolate(vector, match, **kwarguments):
    """
    Fill matched values with the interpolated value

    The fill value is determined by the piecewise linear interpolant
    returned by numpy.interp. By default, the unmatched values will be
    used as the discrete data points, but additional arguments for
    numpy.interp can be passed as keyword arguments.

    Parameters
    ----------
    vector : nimble point or feature
        A nimble Base object containing one point or feature.
    match : value or function
        * value - The value which should be filled if it occurs in the
          data.
        * function - Input a value and return True if that value should
          be filled. Nimble offers common use-case functions in its
          match module.
    kwarguments
        Collection of extra key:value argument pairs to pass to
        numpy.interp.

    Returns
    -------
    list
        The vector values with the interpolated values replacing the
        ``match`` values.

    See Also
    --------
    nimble.match, numpy.interp

    Examples
    --------
    Match a value.

    >>> raw = [1, 'na', 3, 'na', 5]
    >>> data = nimble.createData('Matrix', raw)
    >>> interpolate(data, 'na')
    Matrix(
        [[1.000 2.000 3.000 4.000 5.000]]
        )

    Match using a function from nimble's match module.

    >>> from nimble import match
    >>> raw = [6, 0, 4, 0, 2]
    >>> data = nimble.createData('Matrix', raw)
    >>> interpolate(data, match.zero)
    Matrix(
        [[6.000 5.000 4.000 3.000 2.000]]
        )
    """
    toFill = booleanElementMatch(vector, match)
    if 'x' in kwarguments:
        msg = "'x' is a disallowed keyword argument because it is "
        msg += "determined by the data in the vector."
        raise TypeError(msg)
    matchedLoc = []
    unmatchedLoc = []
    unmatchedVals = []
    for i, (val, fill) in enumerate(zip(vector, toFill)):
        if fill:
            matchedLoc.append(i)
        else:
            unmatchedLoc.append(i)
            unmatchedVals.append(val)

    kwarguments['x'] = matchedLoc
    if 'xp' not in kwarguments:
        kwarguments['xp'] = unmatchedLoc
    if 'fp' not in kwarguments:
        kwarguments['fp'] = unmatchedVals

    tmpV = numpy.interp(**kwarguments)

    def filler(vec):
        ret = []
        j = 0
        for i, val in enumerate(vec):
            if i in matchedLoc:
                ret.append(tmpV[j])
                j += 1
            else:
                ret.append(val)
        return ret

    if len(vector.points) == 1:
        return vector.points.calculate(filler, useLog=False)
    return vector.features.calculate(filler, useLog=False)

def kNeighborsRegressor(point, match, data, **kwarguments):
    """
    Fill matched values with value from skl.kNeighborsRegressor

    The k nearest neighbors are determined by analyzing all points with
    the same unmatched features as the point with missing data. The
    values for the matched feature at those k points are averaged to
    fill the matched value. By default, k=5. This and other parameters
    for skl.kNeighborsRegressor can be adjusted using keyword arguments.

    Parameters
    ----------
    point : nimble point or feature
        A nimble Base object containing the data.
    match : value or function
        * value - The value which should be filled if it occurs in the
          data.
        * function - Input a value and return True if that value should
          be filled. Nimble offers common use-case functions in its
          match module.
    data : nimble Base object
        The object containing the data for the neighbors.
    kwarguments
        Collection of extra key:value argument pairs to pass to
        skl.kNeighborsRegressor.

    Returns
    -------
    list
        The point values with the kNeighborsRegressor values replacing
        the ``match`` values.

    See Also
    --------
    nimble.match

    Examples
    --------
    >>> rawPt = [[1, 1, 'na']]
    >>> rawData = [[1, 1, 1],
    ...            [1, 1, 3],
    ...            [1, 1, 'na'],
    ...            [2, 2, 2],
    ...            ['na', 2, 2]]
    >>> point = nimble.createData('Matrix', rawPt)
    >>> data = nimble.createData('Matrix', rawData)
    >>> kNeighborsRegressor(point, 'na', data, n_neighbors=3)
    Matrix(
        [[1.000 1.000 2.000]]
        )
    """
    return kNeighborsBackend("skl.KNeighborsRegressor", point, match, data,
                             **kwarguments)

def kNeighborsClassifier(point, match, data, **kwarguments):
    """
    Fill matched values with value from skl.kNeighborsClassifier

    The k nearest neighbors are determined by analyzing all points with
    the same unmatched features as the point with missing data. The
    values for the matched feature at those k points are averaged to
    fill the matched value. By default, k=5. This and other parameters
    for skl.kNeighborsClassifier can be adjusted using ``arguments``.

    Parameters
    ----------
    point : nimble point or feature
        A nimble Base object containing the data.
    match : value or function
        * value - The value which should be filled if it occurs in the
          data.
        * function - Input a value and return True if that value should
          be filled. Nimble offers common use-case functions in its
          match module.
    data : nimble Base object
        The object containing the data for the neighbors.
    kwarguments
        Collection of extra key:value argument pairs to pass to
        skl.kNeighborsClassifier.

    Returns
    -------
    list
        The point values with the kNeighborsClassifier values replacing
        the ``match`` values.

    See Also
    --------
    nimble.match

    Examples
    --------
    >>> rawPt = [[1, 1, 'na']]
    >>> rawData = [[1, 1, 1],
    ...            [1, 1, 1],
    ...            [1, 1, 'na'],
    ...            [2, 2, 2],
    ...            ['na', 2, 2]]
    >>> point = nimble.createData('Matrix', rawPt)
    >>> data = nimble.createData('Matrix', rawData)
    >>> kNeighborsClassifier(point, 'na', data, n_neighbors=3)
    Matrix(
        [[1.000 1.000 1.000]]
        )
    """
    return kNeighborsBackend("skl.KNeighborsClassifier", point, match, data,
                             **kwarguments)

############
# Backends #
############

def kNeighborsBackend(method, point, match, data, **kwarguments):
    """
    Backend for filling using skl kNeighbors functions.
    """
    match = convertMatchToFunction(match)
    numPts = len(point.points)
    numFts = len(point.features)
    if not numPts == 1:
        func = 'kNeighbors' + method.split('Neighbors')[1]
        msg = '{func} can only fill point-shaped objects (1 x n), but this '
        msg += 'object had shape ({pts} x {fts})'
        msg = msg.format(func=func, pts=numPts, fts=numFts)
        raise InvalidArgumentValue(msg)

    if anyValues(match)(point):
        notMatching = []
        matching = []
        for idx, val in enumerate(point):
            if match(val):
                matching.append(idx)
            else:
                notMatching.append(idx)
        if len(matching) == numFts:
            msg = 'Unable to determine the nearest neighbors because all '
            msg += 'elements in the point matched'
            raise InvalidArgumentValue(msg)

        predictData = point[notMatching]
        tmpDict = {}
        for fID in matching:
            # training data includes not matching features and this feature
            notMatching.append(fID)
            trainingData = data[:, notMatching]
            # training data includes only points that have valid data at
            # each feature this will also remove the point we are
            # evaluating from the training data
            trainingData.points.delete(anyValues(match), useLog=False)
            pred = nimble.trainAndApply(method, trainingData, -1, predictData,
                                        useLog=False, **kwarguments)
            pred = pred[0]
            tmpDict[fID] = pred
            # remove this feature so next prediction will not include it
            del notMatching[-1]

        def filled(value, i, j):
            try:
                return tmpDict[j]
            except KeyError:
                return value

        return point.calculateOnElements(filled, useLog=False)

    else:
        return point

def statsBackend(vector, match, funcString, statisticsFunction):
    """
    Backend for filling with a statistics function from nimble.calculate.
    """
    toFill = booleanElementMatch(vector, match)

    def toStat(vec):
        return [val for val, fill in zip(vector, toFill) if not fill]

    if len(vector.points) == 1:
        unmatched = vector.points.calculate(toStat, useLog=False)
    else:
        unmatched = vector.features.calculate(toStat, useLog=False)

    if len(unmatched) == len(vector):
        return vector
    if not unmatched:
        msg = statsExceptionNoMatches(funcString, vector)
        raise InvalidArgumentValue(msg)

    stat = statisticsFunction(unmatched)
    if stat is None:
        msg = statsExceptionInvalidInput(funcString, vector)
        raise InvalidArgumentValue(msg)

    return constant(vector, match, stat)

###########
# Helpers #
###########

def getAxis(vector):
    """
    Helper function to determine if the vector is a point or feature.
    """
    return 'point' if vector.points == 1 else 'feature'

def getNameAndIndex(axis, vector):
    """
    Helper function to find the name and index of the vector.
    """
    name = None
    index = 0
    if axis == 'point':
        if vector._pointNamesCreated():
            name = vector.points.getName(0)
        if isinstance(vector, nimble.data.BaseView):
            index = vector._pStart
    else:
        if vector._featureNamesCreated():
            name = vector.features.getName(0)
        if isinstance(vector, nimble.data.BaseView):
            index = vector._fStart

    return name, index

def getLocationMsg(name, index):
    """
    Helper function to format the error message with either a name or index.
    """
    if name is not None:
        location = "'{0}'".format(name)
    else:
        location = "at index '{0}'".format(index)

    return location

def errorMsgFormatter(msg, vector, **kwargs):
    """
    Generic function to format error messages.
    """
    axis = getAxis(vector)
    name, index = getNameAndIndex(axis, vector)
    location = getLocationMsg(name, index)

    return msg.format(axis=axis, location=location, **kwargs)

def statsExceptionNoMatches(funcString, vector):
    """
    Generic message when the statisitcs function recieves no values.
    """
    msg = "Cannot calculate {funcString}. The {funcString} is calculated "
    msg += "using only unmatched values. All values for the {axis} {location} "
    msg += "returned a match."

    return errorMsgFormatter(msg, vector, **{'funcString':funcString})

def statsExceptionInvalidInput(funcString, vector):
    """
    Generic message when statistics functions are given invalid data.
    """
    msg = "Cannot calculate {funcString}. The {axis} {location} "
    msg += "contains non-numeric values or is all NaN values"

    return errorMsgFormatter(msg, vector, **{'funcString':funcString})

def directionError(funcString, vector, target):
    """
    Generic message for directional fill with a matched inital value.
    """
    msg = "Unable to provide a {funcString} value for the {axis} {location} "
    msg += "because the {target} value is a match"

    return errorMsgFormatter(msg, vector, **{'funcString':funcString,
                                             'target':target})
