import praw
import requests
import datetime
from .config import api_keys

class RedditClient:
    """
    Handles fetching data from Reddit using PRAW for recent posts
    and Pushshift for historical posts.
    """
    def __init__(self):
        self.reddit = praw.Reddit(
            client_id=api_keys.get("reddit_client_id"),
            client_secret=api_keys.get("reddit_client_secret"),
            user_agent=api_keys.get("reddit_user_agent"),
        )
        self.pushshift_url = "https://api.pushshift.io/reddit/search/submission/"

    def get_new_posts(self, subreddit_name: str, limit: int = 100, after: str = None):
        """
        Fetches new posts from a subreddit using PRAW, allowing for pagination.
        Returns a tuple of (posts, last_post_fullname).
        """
        subreddit = self.reddit.subreddit(subreddit_name)
        params = {}
        if after:
            params['after'] = after
            
        posts = list(subreddit.new(limit=limit, params=params))
        
        last_post_fullname = posts[-1].fullname if posts else None
        
        return posts, last_post_fullname

    def get_historical_posts(self, subreddit_name: str, keywords: list, start_date: str, end_date: str, limit: int = 100):
        """
        Fetches historical posts from a subreddit using Pushshift.
        Date format: YYYY-MM-DD
        """
        start_timestamp = int(datetime.datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        end_timestamp = int(datetime.datetime.strptime(end_date, "%Y-%m-%d").timestamp())
        query = "|".join(keywords)

        params = {
            "subreddit": subreddit_name,
            "q": query,
            "after": start_timestamp,
            "before": end_timestamp,
            "size": limit,
            "sort": "desc",
            "sort_type": "score"
        }
        response = requests.get(self.pushshift_url, params=params)
        response.raise_for_status()
        return response.json().get("data", [])

    def get_comments(self, post_id: str, limit: int = 20):
        """
        Fetches top comments for a given post ID using PRAW.
        """
        submission = self.reddit.submission(id=post_id)
        submission.comment_sort = "top"
        submission.comments.replace_more(limit=0)
        return submission.comments[:limit]