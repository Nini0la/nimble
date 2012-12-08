"""
Class extending SparseBaseData, defining an object to hold and manipulate a scipy csc_matrix.

"""

from scipy.sparse import csc_matrix
from scipy.io import mmread
from scipy.io import mmwrite
import numpy

from base_data import *
from dense_matrix_data import DenseMatrixData
from sparse_data import *
from ..utility.custom_exceptions import ArgumentException



class CscSparseData(SparseData):


	def __init__(self, data=None, labels=None):
		self.data = csc_matrix(data)
		super(CscSparseData, self).__init__(self.data,labels)


	def _extractColumns_implementation(self,toExtract):
		"""
		

		"""

		converted = self.data.todense()
		ret = converted[:,toExtract]
		converted = numpy.delete(converted,toExtract,1)
		self.data = csc_matrix(converted)


		return CscSparseData(ret)


	
	def _transpose_implementation(self):
		"""

		"""

		print self.data
		self.data = self.data.transpose()
		print self.data



	def _convertToDenseMatrixData_implementation(self):
		""" Returns a DenseMatrixData object with the same data and labels as this object """
		return DenseMatrixData(self.data.todense(), self.labels)




def loadMM(inPath):
	"""
	Returns a CscSparseData object containing the data at the Market Matrix file specified by inPath.
	Uses the build in scipy function io.mmread().

	"""
	return CscSparseData(mmread(inPath))
	



def writeToMM(toWrite, outPath, includeLabels=False):
	"""

	"""
	if includeLabels:
		labelString = "#"
		for i in xrange(toWrite.numColumns()):
			labelString += toWrite.labelsInverse[i]
			if not i == toWrite.numColumns() - 1:
				labelString += ','
		
		mmwrite(target=outPath, a=toWrite.data, comment=labelString)		
	else:
		mmwrite(target=outPath, a=toWrite.data)








