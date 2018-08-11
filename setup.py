import os
from setuptools import setup

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description = (
    read('README.md')
    + '\n' +
    'Download\n'
    '********\n'
    )

setup(name='dynamo-store',
      version=os.environ.get('TRAVIS_TAG', 'dev').strip(),
      description='dynamo-store is a Python library designed to make multi-sharded data structure storage in DynamoDB seamless.',
      long_description=long_description,
      url='http://github.com/GusBricker/dynamo-store',
      author='Chris Lapa',
      author_email='chris@lapa.com.au',
      license='GPLv2',
      packages=['dynamo_store'],
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
