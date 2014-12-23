import sqlite3

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

