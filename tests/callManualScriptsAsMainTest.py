
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
Defines a single test to check the functionality of all of the
scripts contained in the examples folder.
"""

import os
import subprocess
import tempfile

def test_callAllAsMain():
    """
    Calls each script in manualScripts, confirms it completes without an exception.
    """
    # collect the filenames of the scripts we want to run
    examplesDir = os.path.join(os.getcwd(), 'tests', 'manualScripts')
    examplesFiles = os.listdir(examplesDir)
    cleaned = []
    for fileName in examplesFiles:
        if fileName.endswith('.py'):
            cleaned.append(fileName)

    results = {}
    for script in cleaned:
        scriptLoc = os.path.join(examplesDir, script)
        # Provide a dummy output directory argument. For the plotting example,
        # this will write the files into the temp dir instead of generating
        # plots on the screen.
        tempOutDir = tempfile.TemporaryDirectory()

        cmd = ("python", scriptLoc, tempOutDir.name, "False")
        spP = subprocess.PIPE

        # We want these scripts to run with the local copy of nimble, so we need
        # the current working directory (as established by runTests) to be
        # on the path variable in the subprocess. However, we also want the
        # environment to otherwise be the same (because we know it works).
        # Therefore we reuse the environment, except with a modification to
        # PYTHONPATH
        env = os.environ
        env['PYTHONPATH'] = os.getcwd()
        cp = subprocess.run(cmd, stdout=spP, stderr=spP, cwd=os.getcwd(), env=env)
        results[script] = cp
        tempOutDir.cleanup()

    print("")
    print("*** Results ***")
    print("")
    print("")
    fail = False
    sortedKeys = sorted(results.keys())
    for key in sortedKeys:
        cp = results[key]
        if cp.returncode != 0:
            fail = True
        print(key + " : " + str(cp))
        print("")
    assert not fail
