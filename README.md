The benchmark.py script can be used to run a simple benchmark in Chromium-based browsers. The goal of the script is to collect metrics in a consistent and repeatable way. It is not meant to be representative of real browsing workloads from actual users. This should mainly be used as an example for how to automate the browser for measuring performance for a set of test URLs.

The benchmark script runs two phases:
* Populating cache - this visits each URL in succession in the same tab to ensure the HTTP disk cache is properly primed. It waits for a period of time after each load. This can be used to capture the traffic and replay later if the benchmark is not going to be used against live sites.
* Benchmarking - loads each page in a new instance of Chrome and captures data from chrome://histograms.


### Prerequisites
* Python 2.7.* and [Selenium](https://www.seleniumhq.org/) (pip install selenium)
* [Web Page Replay Go](https://github.com/catapult-project/catapult/blob/master/web_page_replay_go/README.md), which depends on [Go runtime](https://golang.org/dl/)
* Having a Chrome/Chromium browser and [ChromeDriver](chromedriver.chromium.org/) binary [corresponding to the browser build](http://chromedriver.chromium.org/downloads/version-selection).

### Recording traffic
* In terminal 1 run WPR in recording mode:

  go run src/wpr.go record --http_port=8080 --https_port=8081 capture.wpr

* In terminal 2 run the benchmark.py script:

  python benchmark.py

The script will visit each site and stay for an interval after that on the same page waiting for additional resources to be fetched. Once it has gone through the populating cache phase, the script can be stopped.

### Running the benchmark
* In terminal 1 run WPR in replay mode:

  go run src/wpr.go replay --http_port=8080 --https_port=8081 capture.wpr

* In terminal 2 run the benchmark.py script:
  
  python benchmark.py
