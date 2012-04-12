# pyWebCash

## Summary

pyWebCash is a web-based personal finance management program.

### Features

 * Import _all_ data from institutions, including all transaction attributes
   and check images, autosplitting if necessary.
 * Import transactions more reliabily than the market leaders.
 * Import/edit data from anywhere via API.
 * Advanced (arbitrary) queries and summaries of transactions.
 * Easily separate business and personal transactions.
 * Automated categorizing and filing transactions.
 * Scan email for receipts
 * Encrypted database - file is useless if it falls into the wrong hands.
 * Scraping can be run automatically or interactively based on willingness to
   store password in the database.

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

### Download

Get it at [GitHub](https://github.com/vincebusam/pyWebCash)

### Requiremets

 * python (tested with 2.6 and 2.7)
 * selenium (for the scraper)
 * Crypto, PIL and numpy on the back-end
 * prctl is optional, and enhances security.
 * Can be found with pip, easy_install, apt, yum, etc...
 * [Highcharts](http://www.highcharts.com/) (free for non-commercial use only) for graphs
 * __There is currently a very limited number of bank scrapers.  Most banks
   are not supported__ (Contributions are welcome!)

### Backend

Setup the web/ directory to be web viewable.
`Alias /myfinances/ /my/installdir/web`
Make sure .py files are run as cgi scripts.  The provided .htaccess will do
this if permissions allow.  Update config.py (on backend and scraper) to
point to this url.

Edit/create the database, image, session directories specified in config.py,
make them writable by the http user (www-data?)
If not using SSL, edit api.py to remove the secure cookies setting.

Create a cron file to clean dead session files and reminde you to re-scrape:

    */5 * * * * root find /my/installdir/session/ -type f -mmin +20 -exec rm \{} \;
    0 6 * * * www-data /my/srcdir/db/emailreminder.py

### Scraper (client)

This has been tested on a Mac, but should also work on Linux.  By default it
uses Chrome, which requires the chrome webdriver binary in the path.  It
can be easily edited to use other browsers.

I couldn't find a better way to re-enable SSL certificate warnings in Chrome
beyond binary patching chromedriver:

`sed -i -e 's/ignore-certificate-errors/nogood-certificate-errors/' /usr/local/bin/chromedriver`

 ---

## Usage

Create a new user from the web interface (do not forget that password,
without it, all data is lost).  Add all applicable accounts
(password is optional if the scraper is run interactively).

Run ./gettransactions.py in the client directory.  Enter login username and
password, and it will get a list of accounts to check.  If the account's
password was not set in the account settings, it will interactively ask
for it before checking that account.
