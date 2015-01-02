Introduction
============

feedr is a non-asynchronous, WTFPLv2-licensed Python parser to tweet the latest updates from multiple RSS feeds.

More information can be found at `its git repository`.

.. _`its git repository`: https://github.com/iceTwy/py-feedr

Registration
============

feedr uses the Twitter API to tweet and retrieve information about tweets.

You need to sign up for a `Twitter account`_, then to get your `API credentials`_.

.. _`Twitter account`: https://twitter.com/signup
.. _`API credentials`: https://apps.twitter.com


Installation
============

Simply use `pip` to install py-feedr::

        $ pip install py-feedr

imgur-scraper provides the `feedr` binary.

Usage
=====

feedr can be used with the following arguments::

        usage: feedr [-h] config

        positional arguments:
          config      path to the feedr configuration file

        optional arguments:
          -h, --help  show this help message and exit
