"""
Script loading some data, spliting it, and writing the results to seperate files

"""

from allowImports import boilerplate
boilerplate()


if __name__ == "__main__":

	from UML import data

	# string manipulation to get and make paths
	pathOrig = "example_data/adult_income_classification_tiny.csv"
	pathOut = "example_data/adult_income_classification_tiny_numerical.csv"

	# we specify that we want a DenseMatrixData object returned, and with just the path it will
	# decide automaticallly the format of the file that is being loaded
	processed = data("RowListData", pathOrig)

	# this feature is a precalculated similarity rating. Lets not make it too easy....
	processed.extractFeatures('fnlwgt')

	#convert assorted features from strings to binary category columns
	processed.featureToBinaryCategoryFeatures('sex')
	processed.featureToBinaryCategoryFeatures('marital-status')
	processed.featureToBinaryCategoryFeatures('occupation')
	processed.featureToBinaryCategoryFeatures('relationship')
	processed.featureToBinaryCategoryFeatures('race')
	processed.featureToBinaryCategoryFeatures('native-country')
	
	# convert 'income' column (the classification label) to a single numerical column
	processed.featureToIntegerCategories('income')

	#scrub the rest of the string valued data -- the ones we converted are the non-redundent ones
	processed.dropStringValuedFeatures()

	# output the split and normalized sets for later usage
	processed.writeFile('csv', pathOut, includeFeatureNames=True)
