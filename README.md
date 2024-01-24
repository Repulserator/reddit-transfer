# reddit-transfer

## My Contributions (Forked Repository)

- **Ensured that saved posts are saved in the same order**
   - This is the only reason i delved into this script, I just couldnt overlook it
- **Added New functionality to list posts, unsave posts and seperately subscribe**
   - Reddit as protection against bots bars you to follow other users for 3,7 and 21 days (You can follow a few after 3 days of account creation, most after 7 and all after 21 is what i understood, it could also be related to Karma)
   - Which is why i created another function just to subscribe, so you dont have to sync just everything. The other functions are if you also need to mess around
- **Remove MFA**
   - Considerably sped up my workflow

I would like to thank natan lao for this wonderful script, really saved me a world of trouble and i am truly grateful for it. I am also impressed by how clean the UI and performance of the script is.

**Thank you**

<center>
======================================================================================================
</center>

## README (Original)

Synchronizes account data (saved submission, saved comments, friends,
subscriptions, settings) between two reddit accounts. This synchronization is
one-way but also destructive; this means, for example, that if a submission is
saved in the destination account but not in the source account, the submission
will be unsaved in the destination account.

It's called "reddit transfer" instead of "reddit sync" because there's already a
cool app called Sync for Reddit that you should try because it's really cool.

Copying preferences works for all preferences accessible via the API. Some
preferences (e.g., those related to profiles) can't be controlled by the API.
(Or maybe they can, I'm not really concerned with those settings so I haven't
investigated it thoroughly.)

The script can handle accounts with two-factor authentication, too. Either way,
you need application keys. For each account:

1. Open the [Third-Party Authorizations page](https://www.reddit.com/prefs/apps)
   when logged in to your Reddit account.

2. Click the `create an app...` button. Choose type `script`, any name, and any
   redirect URL.

3. Provide the provided client ID (in bold under the name you chose) and secret
   to `python reddit_transfer.py login $USERNAME`.

## Usage

Running Python 3.9:

    pip install -r requirements.txt
    python reddit_transfer.py login $OLD_USERNAME
    python reddit_transfer.py login $NEW_USERNAME
    python reddit_transfer.py transfer $OLD_USERNAME $NEW_USERNAME


`Similar usage for other functions like "unsave" and "subscribe"`

## Caveats

MFA authentication may be broken. You can authenticate successfully if MFA is
disabled.\

Check config.ini directly if you have an issue with passwords and scripts

