from allowImports import boilerplate
boilerplate()

def readMapFile(filePath):
    """
    Read in a file mapping id to attribute, formatted as such:
    id=attribute, with one entry per line
    """
    mapFile = open(filePath, 'r')

    idAttrMap = {}

    for line in mapFile:
        line = line.strip('\n')
        lineList = line.split('=', 1)
        idAttrMap[lineList[0].lower()] = lineList[1].lower()

    return idAttrMap

if __name__ == "__main__":
    from UML.read.convert_to_base import convertToCooBaseData

    rawTextDirPath = '/home/ross/LaddersData/rawData'
    #rawTextDirPath = 'UML/datasets/rawDataSmall/rawHtml'
    urlMapPath = '/home/ross/LaddersData/rawData/urlMapAll.txt'
    companyNamePath = '/home/ross/LaddersData/rawData/companyNameMapAll.txt'
    approvalMapPath = '/home/ross/LaddersData/rawData/approvalMapAll.txt'
    entryTimeMapPath = '/home/ross/LaddersData/rawData/entryDateAll.txt'

    urlMap = readMapFile(urlMapPath)
    companyNameMap = readMapFile(companyNamePath)
    approvalMap = readMapFile(approvalMapPath)
    entryDateMap = readMapFile(entryTimeMapPath)
    #convert string labels ('A', 'R') to ints
    for docId, approvalClass in approvalMap.iteritems():
        if approvalClass.lower() == 'a':
            approvalMap[docId] = '1'
        elif approvalClass.lower() == 'r':
            approvalMap[docId] = '2'
        else:
            continue

    attributeMaps = {'url':urlMap, 'companyName':companyNameMap}

    dataObj = convertToCooBaseData(rawTextDirPath, dirMappingMode='multiTyped', attributeMaps=attributeMaps, docIdClassLabelMaps={'approval':approvalMap, 'entryDate':entryDateMap}, requiredClassLabelTypes=set(['approval', 'entryDate']), minTermFrequency=3, featureRepresentation='tfidf')

    dataObj.writeFile('/home/ross/library/LaddersData/umlApprovalEntryDateAll.mtx', includeFeatureNames=True)
    # numPointsToExtract = int(round(dataObj.pointCount * 0.2))
    # testData = dataObj.extractPoints(number=numPointsToExtract, randomize=True)
    # trainData = dataObj

    # #remove the document id's, which are in the first column of the data object
    # trainData.extractFeatures(toExtract=['documentId'])
    # testData.extractFeatures(toExtract=['documentId'])

    # #extract known class labels
    # trainY = trainData.extractFeatures(toExtract=['approval'])
    # testY = testData.extractFeatures(toExtract=['approval'])

    # trainX = trainData
    # testX = testData

    # trainYList = []
    # testYList = []
    
    # nonzeroTrainEntries = trainY.copy(asType="python list")
    # for i in range(len(nonzeroTrainEntries)):
    #     label = nonzeroTrainEntries[i][0]
    #     trainYList.append([int(label)])

    # nonzeroTestEntries = testY.copy(asType="python list")
    # for i in range(len(nonzeroTestEntries)):
    #     label = nonzeroTestEntries[i][0]
    #     testYList.append([int(label)])

    # trainY = createData('Matrix', trainYList)
    # testY = createData('Matrix', testYList)

    # toRun = 'runAndTest("shogun.MulticlassLibLinear", trainX, trainY, testX, testY, {"C":<0.1|0.6|0.75|0.9|1.5|5.0>}, [fractionTrueNegativeTop90], scoreMode="allScores", negativeLabel="2", sendToLog=False)'
    # runs = functionCombinations(toRun)
    # extraParams = {'runAndTest':runAndTest, 'fractionTrueNegativeTop90':fractionTrueNegativeTop90}
    # results = {}
    # run, results = crossValidateReturnBest(trainX, trainY, runs, mode='min', numFolds=5, extraParams=extraParams, sendToLog=True)

    # # for run in runs:
    # run = run.replace('sendToLog=False', 'sendToLog=True')
    # dataHash={"trainX": trainX, 
    #           "testX":testX, 
    #           "trainY":trainY, 
    #           "testY":testY, 
    #           'runAndTest':runAndTest, 
    #           'fractionTrueNegativeTop90':fractionTrueNegativeTop90}
    # #   print "Run call: "+repr(run)
    # print "Best run call: " + str(run)
    # print "Best Run confirmation: "+repr(executeCode(run, dataHash))
