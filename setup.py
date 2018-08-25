import os
import setuptools
import subprocess

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description = read('README.md')

version = None
try:
    version = subprocess.check_output('git describe --tags', shell=True, universal_newlines=True)
except:
    pass
version = os.environ.get('TRAVIS_TAG', version)
if not version:
    version = 'dev'
version = version.strip()

setuptools.setup(name='dynamo-store',
      version=version,
      description='dynamo-store is designed to make multi-sharded data storage in DynamoDB seamless',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='https://github.com/GusBricker/dynamo-store',
      author='Chris Lapa',
      author_email='chris@lapa.com.au',
      license='GPLv2',
      python_requires='>=3',
      packages=setuptools.find_packages(),
      install_requires=['jsonpath-ng', 'boto3', 'pycrypto', 'jsonmodels'],
      keywords="dynamo, store, JSON, shard, encryption, dynamodb, aws",
      classifiers=[
          "Development Status :: 4 - Beta",
          "Intended Audience :: Developers",
          "Intended Audience :: Science/Research",
          "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
          "Programming Language :: Python",
          "Topic :: Software Development :: Libraries :: Python Modules"
      ],
      zip_safe=True,
      test_suite="tests"
)
