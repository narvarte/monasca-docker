# CMM Health check script

Main aim of this script is fast and on the spot checking of health of running
Cloud Monitoring Manager components. It's checking for most common problems
so it's not 100% foolproof but could provide operator with potential ideas
where some problems could started or where problems could arise in the close
future.

## Running script

Script is compatible with both Python 2 and Python 3.

```bash
python3 cmm-check-health.py
```

or

```bash
python2 cmm-check-health.py
```

## Checks provided by the script

* Checking Docker events for number of restarts of every service in the last
  24 hours (report warning when more than 10 restarts happen).
* Checking for number of restarts because "out of memory" errors (report on
  every such event).
* All services with the ability to check they status with some kind of request
  to them this request is done from inside they containers.
* Checking output from previous requests for containing specific text (like
  if proper database exists or status is "green").
* For MySQL:
  * Is anyone connected to the database?
  * Is MySQL database using all available connections?
* Check lags in Kafka topics.
