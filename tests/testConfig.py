"""
Tests to check the loading, writing, and usage of UML.settings, along
with the undlying structures being used.

"""

import tempfile
import copy
import os
import ConfigParser

from nose.tools import raises

import UML
from UML.exceptions import ArgumentException

def safetyWrapper(toWrap):
	"""Decorator which ensures the safety of the the UML.settings and
	the configuraiton file during the unit tests"""
	def wrapped(*args):
		backupFile = tempfile.TemporaryFile()
		configurationFile = open(os.path.join(UML.UMLPath, 'configuration.ini'), 'r')
		backupFile.write(configurationFile.read())
		configurationFile.close()
		
		backupChanges = copy.copy(UML.settings.changes)
		backupAvailable = copy.copy(UML.interfaces.available)

		try:
			toWrap(*args)
		finally:
			backupFile.seek(0)
			configurationFile = open(os.path.join(UML.UMLPath, 'configuration.ini'), 'w')
			configurationFile.write(backupFile.read())
			configurationFile.close()

			UML.settings = UML.configuration.loadSettings()
			UML.settings.changes = backupChanges
			UML.interfaces.available = backupAvailable

	wrapped.func_name = toWrap.func_name
	wrapped.__doc__ = toWrap.__doc__

	return wrapped 


def fileEqualObjOutput(fp, obj):
	resultFile = tempfile.TemporaryFile()
	obj.write(resultFile)

	fp.seek(0)
	resultFile.seek(0)

	origRet = fp.read()
	objRet = resultFile.read()

	assert origRet == objRet

def makeDefaultTemplate():
	lines = [None] * 11
	# Note: the formatting and ordering must be the same as how the
	# ConfigParser outputs them normally
	lines[0] = "#Now, defaults:\n"
	lines[1] = "[DEFAULT]\n"
	lines[2] = "superkey = 44\n"
	lines[3] = "\n"
	lines[4] = "#section comment\n"
	lines[5] = "[SectionName]\n"
	lines[6] = "#option comment\n"
	lines[7] = "option1 = 5\n"
	lines[8] = "#between 1 and 3 originally\n"
	lines[9] = "option3 = 3\n"
	lines[10] = "\n"  # ConfigParser always writes two newlines at the end

	return lines


def testSCPCP_simple():
	""" Test that the ConfigParser subclass works with some simple data """
	fp = tempfile.TemporaryFile()
	template = makeDefaultTemplate()
	for line in template:
		fp.write(line)
	fp.seek(0)

	obj = UML.configuration.SortedCommentPreservingConfigParser()
	obj.readfp(fp)

	fileEqualObjOutput(fp, obj)

def testSCPCP_newOption():
	""" Test that comments are bound correctly after adding a new option """
	template = makeDefaultTemplate()

	fp = tempfile.TemporaryFile()
	for line in template:
		fp.write(line)
	fp.seek(0)

	obj = UML.configuration.SortedCommentPreservingConfigParser()
	obj.readfp(fp)

	obj.set("SectionName", "option2", '1')

	wanted = tempfile.TemporaryFile()
	template = makeDefaultTemplate()
	template.insert(8, "option2 = 1\n")
	for line in template:
		wanted.write(line)
	wanted.seek(0)

	fileEqualObjOutput(wanted, obj)


def testSCPCP_multilineComments():
	""" Test that multiline comments are preserved """
	template = makeDefaultTemplate()
	template.insert(5, "#SectionComment line 2\n")
	template.insert(6, "; Another comment, after an empty line\n")

	fp = tempfile.TemporaryFile()
	for line in template:
		fp.write(line)
	fp.seek(0)

	obj = UML.configuration.SortedCommentPreservingConfigParser()
	obj.readfp(fp)

	fp.seek(0)
	fileEqualObjOutput(fp, obj)

def testSCPCP_whitespaceIgnored():
	""" Test that white space between comment lines is ignored """
	templateWanted = makeDefaultTemplate()
	templateSpaced = makeDefaultTemplate()

	templateWanted.insert(5, "#SectionComment line 2\n")
	templateWanted.insert(6, "; Another comment, after an empty line\n")

	templateSpaced.insert(5, "#SectionComment line 2\n")
	templateSpaced.insert(6, "\n")
	templateSpaced.insert(7, "; Another comment, after an empty line\n")

	fpWanted = tempfile.TemporaryFile()
	for line in templateWanted:
		fpWanted.write(line)
	fpWanted.seek(0)

	fpSpaced = tempfile.TemporaryFile()
	for line in templateSpaced:
		fpSpaced.write(line)
	fpSpaced.seek(0)

	obj = UML.configuration.SortedCommentPreservingConfigParser()
	obj.readfp(fpSpaced)
	fpSpaced.seek(0)

	# should be equal
	fileEqualObjOutput(fpWanted, obj)

	# should raise Assertion error
	try:
		fileEqualObjOutput(fpSpaced, obj)
	except AssertionError:
		pass


def test_settings_GetSet():
	""" Test UML.settings getters and setters """
	#orig changes
	origChangeSet = copy.deepcopy(UML.settings.changes)

	# for available interfaces
	for interface in UML.interfaces.available:
		name = interface.getCanonicalName()
		for option in interface.optionNames:
			# get values of options
			origValue = UML.settings.get(name, option)

			temp = "TEMPVALUE:" + name + option
			# change those values via UML.settings - 
			UML.settings.set(name, option, temp)
			# check the change is reflected by all getters
			assert interface.getOption(option) == temp
			assert UML.settings.get(name, option) == temp

			# change it back
			interface.setOption(option, origValue)
			# check again
			assert UML.settings.get(name, option) == origValue

	# confirm that changes is the same
	assert UML.settings.changes == origChangeSet

@safetyWrapper
def test_settings_GetSectionOnly():
	""" Test UML.settings.get when only specifying a section """
	UML.settings.set("TestSec1", "op1", '1')
	UML.settings.set("TestSec1", "op2", '2')
	
	allSec1 = UML.settings.get("TestSec1", None)
	assert allSec1["op1"] == '1'
	assert allSec1['op2'] == '2'



#@safetyWrapper
#def test_settings_getFormatting():
#	""" Test the format flags  """
#	UML.settings.set("FormatTest", "numOp", 1)
#	asInt = UML.settings.get("FormatTest", "numOp", asFormat='int')
#	asFloat = UML.settings.get("FormatTest", "numOp", asFormat='float')

#	assert asInt == 1
#	assert asFloat == 1.0


@safetyWrapper
def test_settings_saving():
	""" Test UML.settings will save its in memory changes """
	# make some change via UML.settings. save it,
	UML.settings.set("bogusSectionName", "bogus.Option.Name", '1')
	UML.settings.saveChanges()

	# reload it with the starup function, make sure settings saved.
	UML.settings = UML.configuration.loadSettings()
	assert UML.settings.get("bogusSectionName", 'bogus.Option.Name') == '1'

@safetyWrapper
def test_settings_savingSection():
	""" Test UML.settings.saveChanges when specifying a section """
	UML.settings.set("TestSec1", "op1", '1')
	UML.settings.set("TestSec1", "op2", '2')
	UML.settings.set("TestSec2", "op1", '1')
	UML.settings.saveChanges("TestSec1")

	# assert that other changes are still in effect
	assert len(UML.settings.changes) == 1
	assert UML.settings.get("TestSec2", "op1") == '1'

	# reload it with the starup function, make sure settings saved.
	temp = UML.configuration.loadSettings()
	assert temp.get('TestSec1', "op1") == '1'
	assert temp.get('TestSec1', "op2") == '2'
	# confirm that the change outside the section was not saved
	try:
		val = temp.get('TestSec2', "op1")
		assert False
	except ConfigParser.NoSectionError:
		pass

@safetyWrapper
def test_settings_savingOption():
	""" Test UML.settings.saveChanges when specifying a section and option """
	UML.settings.set("TestSec1", "op1", '1')
	UML.settings.set("TestSec1", "op2", '2')
	UML.settings.set("TestSec2", "op1", '1')
	UML.settings.saveChanges("TestSec1", "op2")

	# assert that other changes are still in effect
	assert len(UML.settings.changes) == 2
	assert UML.settings.get("TestSec2", "op1") == '1'
	assert UML.settings.get("TestSec1", "op1") == '1'

	# reload it with the starup function, make that option was saved.
	temp = UML.configuration.loadSettings()
	assert temp.get('TestSec1', "op2") == '2'
	# confirm that the other changes were not saved
	try:
		val = temp.get('TestSec2', "op1")
		assert False
	except ConfigParser.NoSectionError:
		pass
	try:
		val = temp.get('TestSec1', "op1") == '1'
		assert False
	except ConfigParser.NoOptionError:
		pass


@safetyWrapper
def test_settings_syncingNewInterface():
	""" Test UML.configuration.syncWithInterfaces correctly modifies file """
	tempInterface = OptionNamedLookalike("Test", ['Temp0', 'Temp1'])
	UML.interfaces.available.append(tempInterface)
	ignoreInterface = OptionNamedLookalike("ig", [])
	UML.interfaces.available.append(ignoreInterface)

	# run sync
	UML.configuration.syncWithInterfaces(UML.settings)

	# reload settings - to make sure the syncing was recorded
	UML.settings = UML.configuration.loadSettings()

	# make sure there is no section associated with the optionless
	# interface
	assert not UML.settings.cp.has_section('ig') 

	# make sure new section and name was correctly added
	# '' is default value when adding options from interfaces
	assert UML.settings.get('Test', 'Temp0') == ''
	assert UML.settings.get('Test', 'Temp1') == ''

@safetyWrapper
def test_settings_syncingSafety():
	""" Test that syncing preserves values already in the config file """
	tempInterface1 = OptionNamedLookalike("Test", ['Temp0', 'Temp1'])
	UML.interfaces.available.append(tempInterface1)

	# run sync, then reload
	UML.configuration.syncWithInterfaces(UML.settings)
	UML.settings = UML.configuration.loadSettings()

	UML.settings.set('Test', 'Temp0', '0')
	UML.settings.set('Test', 'Temp1', '1')
	UML.settings.saveChanges()

	# now set up another trigger for syncing
	tempInterface2 = OptionNamedLookalike("TestOther", ['Temp0'])
	UML.interfaces.available.append(tempInterface2)

	# run sync, then reload
	UML.configuration.syncWithInterfaces(UML.settings)
	UML.settings = UML.configuration.loadSettings()
	
	assert UML.settings.get("Test", 'Temp0') == '0'
	assert UML.settings.get("Test", 'Temp1') == '1'

@safetyWrapper
def test_settings_syncingChanges():
	""" Test that syncing interfaces properly saves current changes """
	tempInterface1 = OptionNamedLookalike("Test", ['Temp0', 'Temp1'])
	tempInterface2 = OptionNamedLookalike("TestOther", ['Temp0'])
	UML.interfaces.available.append(tempInterface1)
	UML.interfaces.available.append(tempInterface2)

	# run sync, then reload
	UML.configuration.syncWithInterfaces(UML.settings)
	UML.settings = UML.configuration.loadSettings()

	UML.settings.set('Test', 'Temp0', '0')
	UML.settings.set('Test', 'Temp1', '1')
	UML.settings.set('TestOther', 'Temp0', 'unchanged')

	assert UML.settings.get('Test', 'Temp0') == '0'
	
	# change Test option names and resync
	tempInterface1.optionNames[1] = 'NotTemp1'
	UML.configuration.syncWithInterfaces(UML.settings)

	# check values of both changed and unchanged names
	assert UML.settings.get('Test', 'Temp0') == '0'
	try:
		UML.settings.get('Test', 'Temp1') 
	except ConfigParser.NoOptionError:
		pass
	assert UML.settings.get('Test', 'NotTemp1') == ''

	# check that the temp value for testOther is unaffeected
	assert UML.settings.get('TestOther', 'Temp0') == 'unchanged'


@raises(ArgumentException)
def test_settings_allowedNames():
	""" Test that you can only set allowed names in interface sections """

	assert UML.settings.changes == {}
	UML.settings.set('Custom', 'Hello', "Goodbye")
	UML.settings.changes = {}




###############
### Helpers ###
###############


class OptionNamedLookalike(object):
	def __init__(self, name, optNames):
		self.name = name
		self.optionNames = optNames
		
	def getCanonicalName(self):
		return self.name