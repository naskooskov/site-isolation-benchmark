#!/usr/bin/python

import argparse
import json
import re
import sys
import time

from urlparse import urlparse

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

# Note: The data is saved in filename derived from the host portion of the URL.
# Therefore each URL should come from a different site to avoid clobbering the
# output or the filename generation should be changed.
urls_list = [
  # Baseline with no out-of-process iframes.
  'https://web.evilbit.io/empty.html',
  # Baseline with single out-of-process iframe which is empty.
  'http://csreis.github.io/tests/cross-site-iframe-minimal.html',
  # Games, #1
  'https://www.twitch.tv',
  # Games, #50
  'https://www.wowprogress.com/',
  # Sports, #1
  'http://www.espn.com/',
  # Sports, #49
  'https://www.eurosport.com/',
  # Shopping, #1
  'https://www.amazon.com/',
  # Shopping, #50
  'https://www.legacy.com/',
  # News, #1
  'https://www.reddit.com/',
  # News, #50
  'https://www.economist.com/',
  # Home, #1
  'https://www.yelp.com/',
  # Home, #50
  'https://seatguru.com/',
  # Top URL, no out-of-process iframes.
  'https://google.com'
]

# Chrome and ChromeDriver location
if 'win32' in sys.platform:
  chrome_driver_path = 'chromedriver.exe'
  chrome_binary_path = 'chrome-win64-clang\\chrome.exe'
else:
  chrome_driver_path = './chromedriver_linux64/chromedriver'
  chrome_binary_path = './chrome-linux64/chrome'

# The user profile directory to be reused across all starts of Chrome
chrome_user_data_path = './user-profile/'

# Number of iterations to load each URL in the benchmark
benchmark_iterations = 5

# A helper sleep function which prints countdown in seconds to the console.
def sleep(msg, seconds):
  for i in range(seconds, 0, -1):
    sys.stdout.write("\r")
    sys.stdout.write("%s: %s " % (msg, str(i)))
    sys.stdout.flush()
    time.sleep(1)
  print "\r%s - complete" % (msg)

# A helper to construct an Options object to use with ChromeDriver
def get_chrome_options():
  global args

  options = Options()

  # Set the location of the binary and the user profile to use.
  options.binary_location = chrome_binary_path
  options.add_argument('--user-data-dir=%s' % (chrome_user_data_path))

  # This is necessary if one wants to get a Chrome instance with no extensions
  # loaded at all.
  options.add_experimental_option('useAutomationExtension', False)

  # Set these command line switches to get memory metrics from chrome://histograms.
  options.add_argument('--force-enable-metrics-reporting')
  options.add_experimental_option('excludeSwitches', ['metrics-recording-only'])

  # Use a large window to ensure sufficient DOM elements are loaded, even if pages
  # use lazy loading for offscreen elements.
  options.add_argument("window-size=1300,1200")

  # If WebPageReplay Go is used, the following command line parameters are
  # necessary to instruct Chrome to use it as the proxy through which to load
  # all resources.
  if not args.live_sites:
    options.add_argument('--host-resolver-rules=MAP *:80 127.0.0.1:8080,MAP *:443 127.0.0.1:8081,EXCLUDE localhost')
    options.add_argument('--ignore-certificate-errors-spki-list=PhrPvGIaAMmd29hj8BCZOq096yj7uMpRNHpn5PDxI6I=')

  return options

# A helper which navigates Chrome to the histograms page and captures it for
# later analysis.
def collect_data(driver, file_name):
  driver.get('chrome://histograms')
  content = driver.page_source
  with open(file_name + ".html", "w") as html_file:
    html_file.write(content)

  # This is not strictly necessary, but saving a version of the file without
  # some of the HTML formatting makes it easier to just grep from the command
  # line.
  content = re.sub("<br />", "\n", content)
  content = re.sub("<hr />", "-----", content)
  content = re.sub("<pre>", "", content)
  content = re.sub("</pre>", "", content)
  with open(file_name + ".txt", "w") as text_file:
    text_file.write(content)

# This method creates a new instance of Chrome, loads the URL specified and
# captures the UMA histograms. It is used to run multiple iterations in
# the specified isolation mode.
def benchmark_url(url, disable_isolation):
  driver = None
  options = get_chrome_options()
  if disable_isolation:
    options.add_argument("--disable-site-isolation-trials")
  else:
    options.add_argument("--site-per-process")

  for i in range(0, benchmark_iterations):
    print "Starting Chrome"
    driver = webdriver.Chrome(chrome_options=options, executable_path=chrome_driver_path)
    print "Starting Chrome - complete"

    # Waiting here is useful to allow for all initialization tasks to have a
    # chance to complete and browser activity to be ideally at a minimum.
    # The interval can be adjusted based on the hardware this runs on to be
    # either quicker or slower.
    sleep("Waiting to settle down", 7)

    print "Load[%s]: %s" % (i, url)
    driver.get(url)
    print "Load[%s]: %s - complete!" % (i, url)

    # The initial generation of histograms, which includes metrics from the
    # periodic metrics updater such as memory metrics, runs at about 60 seconds
    # after the browser has started. Wait for at least that long and maybe a
    # bit extra to ensure the metrics we care about are generated prior to
    # capturing it.
    sleep("Waiting for histograms", 70)

    print "Collect data[%s]: %s" % (i, url)
    if disable_isolation:
      file_name = "histograms-%s-%s-noisolation" % (urlparse(url)[1], i+1)
    else:
      file_name = "histograms-%s-%s" % (urlparse(url)[1], i+1)
    collect_data(driver, file_name)
    print "Collect data[%s]: %s - complete!" % (i, url)
    driver.quit()
    
# A helper method that iterates through all the URLs in the benchmark and
# loads them sequentially without measuring anything, so all URLs have a
# chance to be cached in the HTTP disk cache. This ensures better uniformity
# between benchmark runs.
def cache_urls():
  global args
  driver = webdriver.Chrome(chrome_options=get_chrome_options(), executable_path=chrome_driver_path)
  for url in urls_list:
    driver.get(url)
    sleep("Waiting for page (%s) to fully load" % (url), int(args.caching_wait_time))

  driver.quit()

if __name__== "__main__":
  global args
  parser = argparse.ArgumentParser()
  parser.add_argument('--no-prime-cache', default=False, action='store_true')
  parser.add_argument('--caching-wait-time', default=10)
  parser.add_argument('--live-sites', default=False, action='store_true')
  args = parser.parse_args()

  if args.no_prime_cache:
    print "Priming HTTP cache"
    cache_urls()
    print "Priming HTTP cache - complete"

  for url in urls_list:
    print "benchmark: %s" % (url)
    benchmark_url(url, False)
    benchmark_url(url, True)
