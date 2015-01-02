from setuptools import setup

with open('README.rst') as file:
        README = file.read()

setup(
    name = 'py-feedr',
    packages = ['feedr'],
    scripts = ['bin/feedr'],
    install_requires = ['requests'],
    version = '0.1b1',
    description = 'A Python Python parser to tweet the latest updates from multiple RSS feeds.',
    long_description = README,
    author = 'iceTwy',
    author_email = 'icetwy@icetwy.re',
    license = 'WTFPLv2',
    url = 'https://github.com/iceTwy/py-feedr',
    keywords = ['Twitter', 'tweet', 'RSS', 'feed'],
    classifiers = [
        'Programming Language :: Python :: 3',
        'Topic :: Internet'
    ]
)
