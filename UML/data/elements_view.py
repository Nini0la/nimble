"""
Defines a subclass of the Elements object, which serves as the primary
base class for read only elements views of data objects.
"""

from __future__ import absolute_import

from UML.docHelpers import inheritDocstringsFactory
from .elements import Elements
from .dataHelpers import readOnlyException

@inheritDocstringsFactory(Elements)
class ElementsView(Elements):
    """
    Class defining read only view objects, which have the same api as a
    normal Elements object, but disallow all methods which could change
    the data.

    Parameters
    ----------
    kwds
        Included due to best practices so args may automatically be
        passed further up into the hierarchy if needed.
    """
    def transform(self, toTransform, points=None, features=None,
                  preserveZeros=False, skipNoneReturnValues=False,
                  useLog=None):
        readOnlyException("transform")

    def multiply(self, other, useLog=None):
        readOnlyException("multiply")

    def power(self, other, useLog=None):
        readOnlyException("power")