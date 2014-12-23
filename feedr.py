#!/usr/bin/env python

from configparser import SafeConfigParser
import feedparser
import hashlib
import json
import requests
import sqlite3
import time
from twitter import *


class DatabaseManager(object):

    '''
    This class is used to manage a single RSS feed's table in the database.
    It writes new updates to the table, and checks if the latest update from
    the RSS feed already exists in the table (and has thus already been posted).
    '''

    def __init__(self, sqlite_db, feed_dbtable):
        '''
        Checks if it feed's table exists in the DB, creates it if not.
            * Feed table structure: (sha256_hash text, date text, name text,
                                     url text)
        '''

        self.sqlite_db = sqlite_db
        self.feed_dbtable = feed_dbtable

        conn = sqlite3.connect(self.sqlite_db)
        c = conn.cursor()
        c.execute(
            'SELECT name FROM sqlite_master WHERE type="table" AND name=?',
            (self.feed_dbtable,))
        if c.fetchall() == []:  # table doesn't exist
            # ! WARNING : Vulnerable to SQLi with forged table name
            # Ugly workaround for binding a table name
            c.execute(
                'CREATE table {}(sha256_hash text, date text, title text, url text)'. format(
                    self.feed_dbtable))
        conn.commit()
        conn.close()

    def create_latest_rss_entry(self, update):
        '''
        Receives an entry from TweetUpdate's latest_rss_entry_to_db method,
        then creates an entry in the feed's assigned table in the SQLite3
        database for the update, with the following structure:
            (sha256_hash text, date text, title text, url text)
        '''

        conn = sqlite3.connect(self.sqlite_db)
        c = conn.cursor()

        table = self.feed_dbtable
        # ! WARNING : Vulnerable to SQLi with forged table name
        # Ugly workaround for binding a table name
        c.execute('INSERT INTO {} VALUES (?, ?, ?, ?)'.format(table), update)
        conn.commit()
        conn.close()

    def check_for_existing_update(self, hashval):
        '''
        Checks if an update already exists in the database, i.e. if the hash
        generated from the latest update with TweetUpdate's rss_latest_sha256
        method already exists in the feed's table of the SQLite3 DB.
        This method is used by TweetUpdate's monitor_new_update method, so it
        returns a boolean
        '''

        conn = sqlite3.connect(self.sqlite_db)
        c = conn.cursor()

        table = self.feed_dbtable
        # ! WARNING : Vulnerable to SQLi with forged table name
        # Ugly workaround for binding a table name
        c.execute('SELECT * from {} WHERE sha256_hash=?'.format(table), hashval)

        if c.fetchone():  # unique update hash present in table, update exists
            conn.commit()
            conn.close()
            return True
        else:
            conn.commit()
            conn.close()
            return False


class MonitorFeedUpdate(object):

    '''
    This class is used to monitor the RSS feed for a new update.
    It interacts with the DatabaseManager and TweetUpdate classes, to check if
    the update has already been posted or if it must be posted and logged in
    the database.
    '''

    def __init__(self, feed_name, feed_url,
                 sqlite_db, feed_dbtable,
                 oauth_key, oauth_secret, consumer_key, consumer_secret):
        '''
        * Parses the RSS feed with feedparser.
        * Initializes a DatabaseManager object.
        * Initializes a TweetUpdate object.
        '''

        # RSS feed
        self.feed_name = feed_name
        self.feed = feedparser.parse(feed_url)

        # DatabaseManager object
        self.dbmanager = DatabaseManager(sqlite_db, feed_dbtable)

        # TweetUpdate object
        self.tweetupdate = TweetUpdate(oauth_key, oauth_secret, consumer_key,
                                       consumer_secret)

    def monitor(self):
        '''
        Monitors the RSS feed for a new update.
        This simply calls the DatabaseManager object's check_for_existing_update
        method; if its return value is false, then TweetUpdate's
        tweet_latest_update method is called.
        '''

        unchecked_hash = (self.rss_latest_sha256(),)
        check = self.dbmanager.check_for_existing_update(unchecked_hash)

        if check:
            # FIXME: Use logging module
            localtime_log = time.strftime("%d %b %Y - %H:%M:%S", time.gmtime())
            print(
                '[{}] - {} -  No new update found.'.format(self.feed_name,
                                                           localtime_log))
        else:
            self.dbmanager.create_latest_rss_entry(
                self.latest_rss_entry_to_db())
            return self.tweetupdate.tweet_latest_update()

    def rss_latest_sha256(self):
        '''
        Creates an unique SHA-256 hash from the latest RSS feed element using
        the publication date, the title and the URL of the element.

        Returns the hex digest of the SHA-256 hash.
        '''
        entry = self.feed.entries[0]
        genhash = hashlib.sha256()
        genhash.update((entry['published'] + entry['title']
                        + entry['link']).encode('utf-8'))
        return genhash.hexdigest()

    def latest_rss_entry_to_db(self):
        '''
        Creates an entry in a SQLite3 database for an update, with the
        following structure:
            (sha256_hash text, date text, title text, url text)
        '''
        entry = self.feed.entries[0]
        update = (self.rss_latest_sha256(), entry['published'], entry['title'],
                  entry['link'])

        return update


class TweetUpdate(object):

    '''
    This class is used to tweet the latest update from a RSS feed, once that
    update has been handled by the MonitorFeedUpdate object.
    '''

    def __init__(self, oauth_key, oauth_secret, consumer_key, consumer_secret):
        '''
        Initializes a Twitter object from the twitter module, using the given
        API credentials.
        '''

        # Twitter object
        self.twitter_api = Twitter(auth=OAuth(oauth_key, oauth_secret,
                                              consumer_key, consumer_secret))

    def shorten_url(self, url):
        '''
        Shortens an URL using is.gd.
        Returns the shortened URL.
        '''
        api_url = "http://is.gd/create.php"
        parameters = {'format': 'json', 'url': url}
        request = requests.get(api_url, params=parameters,
                               headers={'Accept': 'application/json'})
        return request.json()['shorturl']

    def latest_rss_to_tweet(self):
        '''
        Converts the latest RSS entry in a feed
        to a tweetable message of 140 characters
        containing a shortened (is.gd) URL.
        '''

        entry = self.feed.entries[0]
        short_url = self.shorten_url(entry['link'])
        msg = '[{}] {} {}'.format(self.feed_name, entry['title'], short_url)

        if len(msg) > 140:
            excess_chars = len(msg) - 140
            stripped_title = '[{}] {}{}'.format(
                self.feed_name,
                entry['title'][
                    :-excess_chars-3],
                '...')  # remove 3 more chars to add dots
            final_msg = '{} {}'.format(stripped_title, short_url)
        else:
            final_msg = msg

        return final_msg

    def tweet_latest_update(self):
        '''
        Tweets the latest update, logs when doing so.
        '''
        latest_update = self.latest_rss_to_tweet()

        localtime_log = time.strftime("%d %b %Y - %H:%M:%S", time.gmtime())
        print(
            '{0} - {1} - New update posted: {2}\n'
            '{0} - {1} - Update title: {3}\n'
            '{0} - {1} - Published: {4}\n'.format(
                self.feed_name, localtime_log,
                self.rss_latest_sha256()[:10],
                self.feed.entries[0]['title'],
                self.feed.entries[0]['published']))

        return self.twitter_api.statuses.update(status=latest_update)

if __name__ == "__main__":

    configparser = SafeConfigParser()
    cfg = configparser.read('feedr.ini')
    if not cfg:
        raise ValueError('Could not find configuration file feedr.ini')

    feedlist_location = configparser['feeds']['feedlist']
    with open(feedlist_location) as f:
        feedlist = json.load(f)
    oauth_key = configparser['twitter']['oauth_key']
    oauth_secret = configparser['twitter']['oauth_secret']
    consumer_key = configparser['twitter']['consumer_key']
    consumer_secret = configparser['twitter']['consumer_secret']
    sqlite_db = configparser['sqlite']['db_path']

    for feed in feedlist.keys():
        MonitorFeedUpdate(
            feedlist[feed]['name'],
            feedlist[feed]['url'],
            sqlite_db,
            feedlist[feed]['db_table']
            oauth_key,
            oauth_secret,
            consumer_key,
            consumer_secret).monitor()

