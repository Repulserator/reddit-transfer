#!/usr/bin/env python3.9
"""
Transfer reddit subscriptions, saved submissions/comments, friends,
and preferences from one account to another.
"""
import argparse
import collections
import configparser
import functools
import getpass
import logging
import pprint
import sys
from typing import Mapping, Optional, Set, Sequence
from tqdm import tqdm
import pandas as pd
import praw

log = logging.getLogger('reddit-transfer')
logging.basicConfig(level=logging.INFO)
user_agent = "la.natan.reddit-transfer:v0.0.2"


# Create a custom logger
custom_logger = logging.getLogger("custom_logger")
custom_logger.setLevel(logging.DEBUG)

# Create a file handler to write log messages to a file
file_handler = logging.FileHandler("custom_log_file.log")
file_handler.setLevel(logging.DEBUG)


# Add the file handler to the logger
custom_logger.addHandler(file_handler)

# Custom log function
def custom_log(message):
    custom_logger.debug(message)



def prompt(question: str,
           suggestion: Optional[str] = None,
           optional: bool = False) -> Optional[str]:
    suggest = f' [{suggestion}]' if suggestion else ''
    option = ' (optional)' if optional else ''
    answer = input(f'{question}{suggest}{option}: ')
    if answer:
        return answer
    elif suggestion:
        return suggestion
    elif optional:
        return None
    else:
        raise ValueError(f'{question} is required')


class Config:

    def __init__(self, username: str, config_file: str = 'praw.ini'):
        # praw.Reddit exposes a config management interface but we can't use
        # it without authenticating
        self.username = username
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

    def write(self):
        with open(self.config_file, 'w') as fp:
            self.config.write(fp)
        log.info('Credentials saved to %r', self.config_file)

    def read(self) -> Mapping:
        return self.config[self.username]

    def login(self):
        """
        Interactive; prompt for login details and store in praw.ini.
        """
        client_id = self.config.get(self.username, 'client_id', fallback=None)
        client_secret = self.config.get(self.username, 'client_secret', fallback=None)
        self.config[self.username] = {
            'username': self.username,
            'client_id': prompt('Client ID', client_id),
            'client_secret': prompt('Client secret', client_secret)
        }
        self.write()


class User:

    def __init__(self, username: str):
        self.username = username
        password = self.prompt_password()
        self.config = Config(username)
        try:
            self.reddit = praw.Reddit(username,
                                      password=password,
                                      user_agent=user_agent,
                                      **self.config.read())
        except configparser.NoSectionError:
            raise RuntimeError(f'Did you run `{sys.argv[0]} login {username}?')

    def prompt_password(self) -> str:
        password = getpass.getpass(f'Password for /u/{self.username}: ')
        return password

    @functools.cached_property
    def subscriptions(self) -> Set[str]:
        log.info('Fetching subreddits for /u/%s', self.username)
        return {sub.display_name for sub in self.reddit.user.subreddits(limit=None)}

    @functools.cached_property
    def friends(self) -> Set[str]:
        log.info('Fetching friends for /u/%s', self.username)
        return {friend.name for friend in self.reddit.user.friends()}


    #Maintains order of posts
    @functools.cached_property
    def saved(self) -> Set[str]:
        log.info('Fetching saved comments/submissions for /u/%s', self.username)
        sd = []
        for item in self.reddit.user.me().saved(limit=None):
            sd.append(item)

        #Debug if incorrect order
        # with open('savedlog2.txt', 'w') as f:
        #     for item in self.reddit.user.me().saved(limit=None):
        #         sd.append(item)
        #         f.write(f'{item}\n')

        sd.reverse()
        return sd

def sync_data(src_user: str, dst_user: str) -> None:
    src = User(src_user)
    dst = User(dst_user)


    diff = lambda l1,l2: [x for x in l1 if x not in l2]

    # TODO: Leaky abstraction
    if src.config.read()['client_id'] == dst.config.read()['client_id']:
        raise ValueError('You must generate one set of keys per account')

    # Since these are bulk operations, we could just unsubscribe from all
    # then resubscribe as needed but I've found that there's some lag between
    # subscribing to a subreddit and the Reddit API recognizing that we've
    # subscribed to a subreddit

    # While the above statements are true, i think anyone in a similar situation as me has created a new account
    # and as per latest rules it has a time limit before you can follow users, so i disabled it

    # for sub in dst.subscriptions - src.subscriptions:
    #     log.info('Unsubscribe from /r/%s', sub)
    #     dst.reddit.subreddit(sub).unsubscribe()


    for sub in src.subscriptions - dst.subscriptions:
        log.info('Subscribe to /r/%s', sub)
        try:
            dst.reddit.subreddit(sub).subscribe()
        except:
            #Add to log these into a sperate category and into a file
            log.info('Failed r/%s', sub)
            pass


    for friend in dst.friends - src.friends:
        log.info('Friend /u/%s', friend)
        dst.reddit.redditor(friend).unfriend()

    for friend in src.friends - dst.friends:
        log.info('Unfriend /u/%s', friend)
        dst.reddit.redditor(friend).friend()

    for thing in dst.saved - setsrc.saved:
        # TODO: Leaky abstraction
        log.info('Unsave %r', thing)
        if isinstance(thing, praw.models.Submission):
            dst.reddit.submission(thing.id).unsave()
        elif isinstance(thing, praw.models.Comment):
            dst.reddit.comment(thing.id).unsave()
        else:
            raise RuntimeError('unexpected object type')

    #Enable if you want to manage saved by time (Use this to remake both lists)
    #latest_saved_posts = sorted(list(user.saved)[:10], key=lambda x: x.created_utc, reverse=True)


    #Now i am not sure if this will work this way, but i guess we will find out
    for thing in tqdm(diff(src.saved,dst.saved)):
        log.info('Save %r', thing)
        if isinstance(thing, praw.models.Submission):
            dst.reddit.submission(thing.id).save()
        elif isinstance(thing, praw.models.Comment):
            dst.reddit.comment(thing.id).save()
        else:
            raise RuntimeError('unexpected object type')



    #Print to check the last few posts and if the order was maintained
    #-----------------------------------------------------------------#
    srcsaved = list(src.saved)
    dstsaved = list(dst.saved)
    max_length = max(len(srcsaved), len(dstsaved))
    srcsaved += [None] * (max_length - len(srcsaved))
    dstsaved += [None] * (max_length - len(dstsaved))
    df = pd.DataFrame({'rep': srcsaved[-16:], 'anon': dstsaved[-16:]})
    pd.set_option('display.max_rows', 20)
    pd.set_option('display.max_columns', None)
    print(df)
    #-----------------------------------------------------------------#


    log.info(f"Copy preferences from {dst_user}")
    dst.reddit.user.preferences.update(**src.reddit.user.preferences())
    pprint.pprint(src.reddit.user.preferences())
    pprint.pprint(dst.reddit.user.preferences())


#Personal Unpolished function to check stuff and print it into a csv
def list_saved_posts(username: str) -> None:

    user = User(username)
    srcsaved = list(user.saved)

    latest_saved_posts = sorted(list(user.saved)[:10], key=lambda x: x.created_utc, reverse=True)
    saved_data = []

    #List latest 20 saved and also saves it in a csv
    for post in srcsaved[-20:]:
        post_data = {}

        # Define the fields you want to include
        fields = ['id', 'title', 'created_utc', 'saved', 'over_18']

        for field in fields:
            try:
                post_data[field] = getattr(post, field, None)
            except Exception as e:
                # Handle any other exceptions if needed
                log.warning('Error: %s. Handling missing attribute %s for post with ID %s.', e, field, post.id)
                post_data[field] = None

        saved_data.append(post_data)

    # Create a DataFrame from the list of dictionaries
    df = pd.DataFrame(saved_data)
    df.to_csv('saved_posts.csv', index=False)
    log.info('DataFrame of saved posts for /u/%s:\n%s', username, df)


# IF the order is messed up and you want to unsave everything and start over

def unsaved(username: str) -> None:
    
    user = User(username)
    #saved_posts = [str(item) for item in user.saved][:20]
    srcsaved = list(user.saved)[-20:]

    
    input("\nTo confirm this will wipe your saved for " + username)
    z = input("\nAre you sure you want to proceed? (Type proceed)\n")

    if z.lower() == "proceed":
        
        #Unsave all, If you messed up something
        #-----------------------------------------------------------------#
        for thing in srcsaved:
            # TODO: Leaky abstraction
            log.info('Unsave %r', thing)
            if isinstance(thing, praw.models.Submission):
                user.reddit.submission(thing.id).unsave()
            elif isinstance(thing, praw.models.Comment):
                user.reddit.comment(thing.id).unsave()
            else:
                raise RuntimeError('unexpected object type')
        #-----------------------------------------------------------------#

    else:
        print("cheers")
        exit(1)
    

#As mentioned before, if you made a new account, this is the only thing thats going to take time.

def subscribe(src_user: str, dst_user: str) -> None:
    src = User(src_user)
    dst = User(dst_user)

    # TODO: Leaky abstraction
    if src.config.read()['client_id'] == dst.config.read()['client_id']:
        raise ValueError('You must generate one set of keys per account')
    

    for sub in src.subscriptions - dst.subscriptions:
        log.info('Subscribe to /r/%s', sub)
        try:
            dst.reddit.subreddit(sub).subscribe()
        except:
            #Add to log these into a sperate category and into a file
            log.info('Failed r/%s', sub)
            custom_log(sub)
            pass


def main(argv: Sequence[str]):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(help='Specify action', dest='action')
    subparsers.required = True

    login_parser = subparsers.add_parser('login')
    login_parser.add_argument('username')

    transfer_parser = subparsers.add_parser('transfer')
    transfer_parser.add_argument('src_user', help='User to copy data from')
    transfer_parser.add_argument('dst_user', help='User to copy data to')

    list_parser = subparsers.add_parser('list')
    list_parser.add_argument('username', help='List saved posts # .py list $username')

    list_parser = subparsers.add_parser('unsave')
    list_parser.add_argument('username', help='Unsave all posts # .py unsave $username')

    subscribe_parser = subparsers.add_parser('subscribe')
    subscribe_parser.add_argument('src_user', help='User to copy data from')
    subscribe_parser.add_argument('dst_user', help='User to copy data to')



    args = parser.parse_args(argv)

    if args.action == 'login':
        Config(args.username).login()
    elif args.action == 'transfer':
        sync_data(args.src_user, args.dst_user)
    elif args.action == 'list':
        list_saved_posts(args.username)
    elif args.action == 'unsave':
        unsaved(args.username)
    elif args.action == 'subscribe':
        subscribe(args.src_user, args.dst_user)

    else:
        exit(1)


if __name__ == '__main__':
    main(sys.argv[1:])
