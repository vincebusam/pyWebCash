# pyWebCash

## Summary

This is a web-based personal finance management program.  The goal is a
system that can:

 * Import _all_ data from institutions, including all transaction attributes
   and check images.
 * Import transactions more reliabily than the market leaders.
 * Import/edit data from anywhere via API.
 * Allow for more advanced (arbitrary) queries and summaries of transactions.
 * More easily separate business and personal transactions.
 * Bettar automate categorizing and filing transactions.
 * Encrypted database - file is useless if it falls into the wrong hands.
 * Scraping can be run automatically or interactively based on if you want to
   store your password in the database.

 ---

## Architecture

The back-end is written in python, exposing an API over HTTP.  There is an
html/javascript front-end for viewing and editing transactions.  Loading
transactions is done client-side (interactively or scripted) by python with
selenium.

The database is an AES-encrypted cPickle file.  It's encrypted with the
user's password, so don't lose it!  Check images, and HTTP session files
(which contain the database password) are stored encrypted as well.  This
requires the database to be entirely re-loaded for each HTTP request, but
I've found it easily fast enough for unloaded servers to handle.

 ---

## Installation

### Requiremets

 * python (tested with 2.6 and 2.7)
 * selenium (for the scraper)
 * Crypto, PIL and numpy on the back-end
 * prctl is optional, and enhances security.
 * You can find these with pip, easy_install, apt, yum, etc...
 * __You'll probably be writing your own scraper until more bank support is  contributed__

### Backend

Setup the web/ directory to be web viewable.
`Alias /myfinances/ /usr/local/myfinance/web`
Make sure .py files are run as cgi scripts.  The provided .htaccess will do
this if permissions allow.  Update config.py (on backend and scraper) to
point to this url.

Edit/create the database, image, session directories specified in config.py,
make them writable by the http user (www-data?)
If you don't use https, edit api.py to remove the secure cookies setting.

Create a cron file to clean dead session files:  
`*/5 * * * * root find /usr/local/finance/session/ -type f -mmin +20 -exec rm \{} \;`

### Scraper (client)

I've tested this on a Mac, should also work on Linux.  By default it uses
Chrome, so you'll need to install the chrome webdriver binary or change the
code to use your browser of choice.

 ---

## Usage

Create a new user from the web interface (do not forget that password,
without it, your data is lost).  Add all your applicable accounts
(password is optional if you run the scraper interactively).

Run ./gettransactions.py in the client directory.  Enter your login username
and password, and it will get a list of accounts to check.  If you don't set
the account's password in the account settings, it will interactively ask
before checking that account.