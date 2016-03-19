### Overview

Pulls the json data for each blog post of the given tumblr url from
the tumblr API. Each post is put in a its own directory like so:

```
[tumblr_url]/[year]/[month]-[day]/[postid]
```

Inside that directory, there will be a file called json, which
contains the json data. Each post gets its own directory so that other
files associated with the post (like images, etc.) can also be
retrieved.

### authinfo.txt

For tumblrarchive to connect to tumblr's API, it needs to have some
login info. authinfo.txt is the place to store this data. Only the
first 4 lines of this file are used, and they should be in the order
expected by [PyTumblr](https://github.com/tumblr/pytumblr):

```
<consumer_key>
<consumer_secret>
<oauth_token>
<oauth_secret>
```

If you do not have these strings, the fastest way to get them is to
visit https://api.tumblr.com/console/

### Running

Once you have authinfo.txt setup, you can run tumblrarchive with the
name of the tumblr you want to archive:

```
python tumblrarchive.py [tumblr_url]
```

This will take some time, so please be patient with it.
