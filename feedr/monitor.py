import difflib
import feedparser
import hashlib
import time

from feedr.dbmanager import DatabaseManager
from feedr.tweetupdate import TweetUpdate


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
        self.latest_entry = self.feed.entries[0]  # for convenience

        # DatabaseManager object
        self.dbmanager = DatabaseManager(sqlite_db, feed_dbtable)

        # TweetUpdate object
        self.tweetupdate = TweetUpdate(oauth_key, oauth_secret, consumer_key,
                                       consumer_secret)

    def monitor(self):
        '''
        Monitors the RSS feed for a new update.
        This calls the DatabaseManager object's check_for_existing_update
        method.
         * New update: checks if it is a duplicate with is_duplicate_update,
           removes the last tweet and DB entry if it is. In all cases, the
           tweet_latest_update method is called. Logs.
         * No new update: does nothing, logs.
        '''

        unchecked_hash = (self.rss_latest_sha256(),)
        check = self.dbmanager.check_for_existing_update(unchecked_hash)
        localtime_log = time.strftime("%d %b %Y - %H:%M:%S", time.gmtime())

        if check:
            # FIXME: Use logging module
            print(
                '[{}] - {} -  No new update found.'.format(self.feed_name,
                                                           localtime_log))
        else:
            # See https://github.com/iceTwy/py-feedr/issues/4
            if self.is_duplicate_update():
                self.tweetupdate.delete_last_tweet()
                entry_table_hash = self.dbmanager.get_last_table_entry[1]
                self.dbmanager.del_last_table_entry()
                print(
                    '[{0}] - {1} - Duplicate update in the feed.\n'
                    '[{0}] - {1} - Deleted entry {} from the table, and its associated tweet\n'.
                    format(self.feed_name, localtime_log, entry_table_hash))
            self.dbmanager.create_latest_rss_entry(
                self.latest_rss_entry_to_db())
            self.tweetupdate.tweet_latest_update(self.feed_name,
                                                 self.latest_entry)
            print('[{0}] - {1} - New update posted: {2}\n'
                  '[{0}] - {1} - Update title: {3}\n'
                  '[{0}] - {1} - Published: {4}\n'.format(
                      self.feed_name, localtime_log,
                      self.rss_latest_sha256()[:10],
                      self.latest_entry['title'],
                      self.latest_entry['published']))

    def is_duplicate_update(self):
        '''
        Checks if an update is a duplicate of the previous one in the feed
        by using fuzzy-string matching on the title or checking if the old
        update's title is contained in the new one.
        '''

        cur_title = self.latest_entry['title']
        last_table_entry = self.dbmanager.get_last_table_entry()
        if not last_table_entry: # empty table
            return False
        else:
            prev_title = last_table_entry[3]

        if prev_title in cur_title:
            return True
        delta = difflib.SequenceMatcher(None, cur_title, prev_title)
        if delta.ratio() >= 0.75:
            return True

        return False

    def rss_latest_sha256(self):
        '''
        Creates an unique SHA-256 hash from the latest RSS feed element using
        the publication date, the title and the URL of the element.

        Returns the hex digest of the SHA-256 hash.
        '''
        entry = self.latest_entry
        genhash = hashlib.sha256()
        genhash.update((entry['published'] + entry['title']
                        + entry['link']).encode('utf-8'))
        return genhash.hexdigest()

    def latest_rss_entry_to_db(self):
        '''
        Formats the latest RSS feed element to a valid table entry in the
        database using the following structure:
            (sha256_hash text, date text, title text, url text)
        '''
        entry = self.latest_entry
        update = (self.rss_latest_sha256(), entry['published'], entry['title'],
                  entry['link'])

        return update

