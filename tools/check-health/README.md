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

### Command line arguments

You can use the following arguments to script:

| Short | Long           | Default | Description                                         |
| ----- | -------------- | ------- | --------------------------------------------------- |
| -m    | --metrics      | False   | Check metrics pipeline                              |
| -l    | --logs         | False   | Check logs pipeline                                 |
| -k    | --kafka-lag    | 20000   | Report warning when Kafka lag jump over this value  |
| -r    | --max-restarts | -1      | After this number of service restarts issue warning |
| -f    | --folder       | CMM dir | Folder with `.env` and docker-compose config files  |
| -h    | --help         |         | Show help                                           |

If you start script without `--metrics` and `--logs` arguments both pipelines
will be checked.

```bash
python3 cmm-check-health.py -k=100 -m
```

Max restarts check is disabled by default because of too many false positives.
If you want to run it to check  if number of restarts from the start of all
services is bigger than 20 use following command:

```bash
python3 cmm-check-health.py -r=20
```

## Checks provided by the script

* All services with the ability to check they status with some kind of request
  to them this request is done from inside they containers.
* Checking output from previous requests for containing specific text (like
  if proper database exists or status is "green").
* For MySQL:
  * Is anyone connected to the database?
  * Is MySQL database using all available connections?
* Check lags in Kafka topics.
* Checking Docker for number of restarts of every service from the time they
  was created (report warning when more than 10 restarts happen).
* Checking if any service was restarted because "out of memory" error.

### Services without health checks

Following services does not have health checks and are not tested
if they are working properly:

* Monasca Agent Forwarder
* Monasca Agent Collector
* Monasca Persister
* Monasca Thresh
* Monasca Notification
* Monasca Log Metrics
* Monasca Log Persister
* Monasca Log Transformer
* Monasca Log Agent
* Monasca Log Spout

They are still tested for too many restarts if `-r` is used.


## Checking number of service restarts

It's impossible to check exact number of restarts of services in the last
24 hours. Theoretically `docker events` provide this functionality but it's
limited to last 256 events. In CMM case that have a lot of containers running
at the same time on one machine it's useless because it showing only last
4 minutes of events.

If you still want to check Docker events use the following command:

```bash
docker events --filter event=die --filter event=oom --since=24h --until=1s
```
