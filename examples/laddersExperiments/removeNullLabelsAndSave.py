"""
Script to load a data set, determine which rows have null class labels (if label==0), 
remove those rows, and save the data set.  May not work on very large, sparse sets: converts
data to dense version to hasten removal of arbitrary rows.
"""

from allowImports import boilerplate
boilerplate()

if __name__ == "__main__":

    from UML import create

    pathIn = "/media/library_/LaddersData/umlApproval50KTfIdfRoundedNoHeaders.mtx"
    sparseVersion = create('coo', pathIn, fileType='mtx')
    
    print "Finished loading data"
    print "trainX shape: " + str(trainX.data.shape)
    print "trainY shape: " + str(trainY.data.shape)

    # sparse types aren't playing nice with the error metrics currently, so convert
    trainY = trainY.toDenseMatrixData()
    testY = testY.toDenseMatrixData()

    trainYList = []
    nullPointIndicesTrain = []
    for i in range(len(trainY.data)):
        label = trainY.data[i][0]
        if int(label) != 0:
            trainYList.append([int(label)])
        else:
            trainYList.append([int('1')])

        

    testYList = []
    nullPointIndicesTest = []
    for i in range(len(testY.data)):
        label = testY.data[i][0]
        if int(label) != 0:
            testYList.append([int(label)])
        else:
            testYList.append([int('1')])

    trainY = create('dense', trainYList)
    testY = create('dense', testYList)

    print "Finished converting labels to ints"