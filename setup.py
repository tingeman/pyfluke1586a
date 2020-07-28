'''
Created on Mar 24, 2012

@author: tin@byg.dtu.dk

Run from command line:

python setup.py sdist
python setup.py bdist_wininst

This will generate a distribution zip file and a windows executable installer
Can be installed by running from the unzipped temporary directory:

python setup.py install

Or from development directory, in development mode - will reflect changes made
in the original development directory instantly automatically.

python setup.py develop
'''

from setuptools import find_packages
from numpy.distutils.core import setup

                 
if __name__ == "__main__":
    
    raise NotImplementedError("""
    This software is currently a script. It should not be 
    installed as a packages, but run from the command line 
    or python interpreter.""")

    setup(
    name = "pyfluke1524",
    version = "2019.09",
    description = "Package to collect temperature data with Fluke 1524 thermometer.",
    author = "Thomas Ingeman-Nielsen",
    author_email = "tin@byg.dtu.dk",
    url = "http://???/",
    keywords = ["temperature","Fluke"],
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Fortran",
        "Development Status :: 3 - Alpha",
        "Operating System :: Microsoft :: Windows",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering",      
        ],
    packages=find_packages(),
    include_package_data = True,
    package_data = {
    # If any package contains *.txt files, include them:
    '': ['*.txt','*.FOR','*.for','*.pyf','*.pyd','*.par'] },
    ext_modules = [],
    long_description = """\
pyfluke1524
----------------

Package to communicate with Fluke1524 thermometer.
It can:
- Check PC time off set with internet time server
- Check thermometer time off set with PC time
- Synchronize thermometer time with PC time
- Download autolog data from instrument

Intended use is to ensure thermometer time is synchronized with PC time
before collection of reference temperature data with Fluke1524.
If the thermometer/logger system under calibration is also synchronized, 
it is simple to calculate temperature offset.

Other features not yet implemented:
- Delete autolog memory
- Initiate autolog measurements (must be done manually from instrument)
- Stop autolog measurements (must be done manually from instrument)
""")
