import requests
import time
from twitter import *

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

    def latest_rss_to_tweet(self, feed_name, feed_entry):
        '''
        Converts the latest RSS entry in a feed
        to a tweetable message of 140 characters
        containing a shortened (is.gd) URL.
        '''

        entry = feed_entry
        short_url = self.shorten_url(entry['link'])
        msg = '[{}] {} {}'.format(feed_name, entry['title'], short_url)

        if len(msg) > 140:
            excess_chars = len(msg) - 140
            stripped_title = '[{}] {}{}'.format(
                feed_name,
                entry['title'][
                    :-excess_chars-3],
                '...')  # remove 3 more chars to add dots
            final_msg = '{} {}'.format(stripped_title, short_url)
        else:
            final_msg = msg

        return final_msg

    def tweet_latest_update(self, feed_name, feed_entry):
        '''
        Tweets the latest update, logs when doing so.
        '''

        latest_update = self.latest_rss_to_tweet(feed_name, feed_entry)
        return self.twitter_api.statuses.update(status=latest_update)

