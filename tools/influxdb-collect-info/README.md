# Introduction

This document describes the use of script influxdb-collect-info.sh

**Background**:  

In certain situations, memory consumption of Influxdb could suddenly grow.
At some point of time, normal CMM operation isn’t possible any longer.

This script will collect information related to Influxdb when its memory consumption becomes too high.

# Script influxdb-collect-info.sh

## Description

The script checks RAM usage of influxdb service (running as docker container).  
If "RAM usage" > maxRam% of avail RAM, this information will be collected:

- Influxdb container inspect info
- Influxdb container stats info
- Process info from inside Influxdb container
- Shards from Influxdb
- Retention policies from Influxdb
- List of empty wal files 
- Network information of Influxdb (netstat)
- Dump memory information of Influxdb process
- The values of the metrics defined in the script

## Default parameters

```
# Default DEBUG option: 1=DEBUG output, 0=no DEBUG output (Can be set in CLI)
DEBUG=0

# Uncomment for verbose logging in bash
#set -x

# Default max ram perc. threshold. Integer 0-100 (Can be set in CLI)
maxRam=40

# Set the output directory
outputDataDir="/opt/cmm-server/cmm-influx-data"

# Set the monasca containers directory
monascaContainersDir="/opt/cmm-server/monasca-containers"

# Default amount of past days for collecting metrics.
# Integer 1-40 (Can be set in CLI)
amountDays=40

# Set the metrics list
declare -a metricNames=("container.io.read_bytes"
                        "container.io.read_bytes_sec"
                        "container.io.write_bytes"
                        "container.io.write_bytes_sec"
                        "container.mem.cache"
                        "container.mem.rss"
                        "container.mem.swap"
                        "container.mem.used_perc"
                       )
```
## Excecution
The script should be executed by the **root** user and the attributes should change to `+x`
```
# chmod +x influxdb-collect-info.sh
```
Most of the parameters can be set by CLI.
```
# ./influxdb-collect-info.sh --help
2020-02-25T11:57:10+01:00 INFO: v1.0.3 ===========================================================================
2020-02-25T11:57:10+01:00 INFO: =                           Influxdb Collect Info                                =
2020-02-25T11:57:10+01:00 INFO: ==================================================================================
2020-02-25T11:57:10+01:00 INFO: 
Usage as root:  ./influxdb-collect-info.sh [-h|--help] [-m=<maxram>|--maxram=<maxram>]
                                           [-a=<amountdays>|--amountdays=<amountdays>]
                                           [-f|--force] [-d|--debug]

  -h|--help                                   Display this help message

  -m=<max ram>|--maxram=<max ram>             Set the max ram perc. threshold.
                                              Integer 0-100
                                              Ex. --maxram=50

  -a=<amount days>|--amountdays=<amount days> Set the amount of past days for collecting
                                              metrics from Influx db.
                                              Integer 1-40
                                              Ex. --amountdays=10

  -f|--force                                  Force to collect the info

  -d|--debug                                  Increase output verbosity

```

Execution dafault parameters.
```
# ./influxdb-collect-info.sh
2020-02-24T16:35:31+01:00 INFO: v1.0.3 ===========================================================================
2020-02-24T16:35:31+01:00 INFO: =                           Influxdb Collect Info                                =
2020-02-24T16:35:31+01:00 INFO: ==================================================================================
2020-02-24T16:35:34+01:00 INFO: RAM used by influxdb service 0% is lower than max. value 40%: no action required
```

Execution forcing to collect the data, collecting 2 days of metrics and using Debug as log level.
```
./influxdb-collect-info.sh --force --amountdays=2 --debug
2020-02-24T16:39:11+01:00 INFO: v1.0.3 ===========================================================================
2020-02-24T16:39:11+01:00 INFO: =                           Influxdb Collect Info                                =
2020-02-24T16:39:11+01:00 INFO: ==================================================================================
2020-02-24T16:39:11+01:00 DEBUG: Option --maxram            40
2020-02-24T16:39:11+01:00 DEBUG: Option --amountdays        2
2020-02-24T16:39:11+01:00 DEBUG: Option --force             1
2020-02-24T16:39:11+01:00 DEBUG: Option --debug             1
2020-02-24T16:39:11+01:00 DEBUG: Param outputDataDir        /opt/cmm-server/cmm-influx-data
2020-02-24T16:39:11+01:00 DEBUG: Param monascaContainersDir /opt/cmm-server/monasca-containers
2020-02-24T16:39:14+01:00 DEBUG: Result from docker stats: memory consumption: 0.23% -> 0.23 -> 0
2020-02-24T16:39:14+01:00 DEBUG: memPercentTrunc is a valid percentage value
2020-02-24T16:39:14+01:00 DEBUG: RAM usage of service Influxdb: 0%
2020-02-24T16:39:14+01:00 INFO: Getting inspect info from Influxdb container...
2020-02-24T16:39:14+01:00 DEBUG: Executing: docker inspect <Influxdb-ID>
2020-02-24T16:39:14+01:00 INFO: Getting stats info from Influxdb container...
2020-02-24T16:39:14+01:00 DEBUG: Executing: docker stats <Influxdb-ID> --no-stream
2020-02-24T16:39:16+01:00 INFO: Getting process info from Influxdb container
2020-02-24T16:39:16+01:00 DEBUG: Executing inside of the Influxdb container: ps aux
2020-02-24T16:39:16+01:00 INFO: Getting shards from Influxdb...
2020-02-24T16:39:16+01:00 DEBUG: Executing inside of the Influxdb container: influx -execute 'SHOW SHARDS' -database=mon
2020-02-24T16:39:17+01:00 INFO: Getting retention policies from Influxdb...
2020-02-24T16:39:17+01:00 DEBUG: Executing inside of the Influxdb container: influx -execute 'SHOW RETENTION POLICIES' -database=mon
2020-02-24T16:39:17+01:00 INFO: Getting the list of empty wal files...
2020-02-24T16:39:17+01:00 DEBUG: find /<monasca-containers-dir>/influxdb/wal -size 0 -type f -print | wc -l
2020-02-24T16:39:17+01:00 DEBUG: find /<monasca-containers-dir>/influxdb/wal -size 0 -type f -print
2020-02-24T16:39:17+01:00 INFO: Getting Influxdb network information...
2020-02-24T16:39:17+01:00 DEBUG: Executing inside of the Influxdb container: netstat -r
2020-02-24T16:39:18+01:00 DEBUG: Executing inside of the Influxdb container: netstat -aeWp
2020-02-24T16:39:18+01:00 INFO: Getting Influxdb memory information...
2020-02-24T16:39:18+01:00 DEBUG: Executing inside of the Influxdb container: cat /proc/1/status
2020-02-24T16:39:19+01:00 DEBUG: Executing inside of the Influxdb container: cat /proc/1/maps
2020-02-24T16:39:19+01:00 DEBUG: Executing inside of the Influxdb container: cat /proc/1/smaps
2020-02-24T16:39:19+01:00 INFO: Getting the metric values: container.io.read_bytes from Influxdb container...
2020-02-24T16:39:19+01:00 DEBUG: Getting metric container.io.read_bytes from 2 days ago to 1 days ago
2020-02-24T16:39:20+01:00 DEBUG: Getting metric container.io.read_bytes from 1 days ago to 0 days ago
2020-02-24T16:39:20+01:00 INFO: Getting the metric values: container.io.read_bytes_sec from Influxdb container...
2020-02-24T16:39:20+01:00 DEBUG: Getting metric container.io.read_bytes_sec from 2 days ago to 1 days ago
2020-02-24T16:39:20+01:00 DEBUG: Getting metric container.io.read_bytes_sec from 1 days ago to 0 days ago
2020-02-24T16:39:21+01:00 INFO: Getting the metric values: container.io.write_bytes from Influxdb container...
2020-02-24T16:39:21+01:00 DEBUG: Getting metric container.io.write_bytes from 2 days ago to 1 days ago
2020-02-24T16:39:21+01:00 DEBUG: Getting metric container.io.write_bytes from 1 days ago to 0 days ago
2020-02-24T16:39:22+01:00 INFO: Getting the metric values: container.io.write_bytes_sec from Influxdb container...
2020-02-24T16:39:22+01:00 DEBUG: Getting metric container.io.write_bytes_sec from 2 days ago to 1 days ago
2020-02-24T16:39:22+01:00 DEBUG: Getting metric container.io.write_bytes_sec from 1 days ago to 0 days ago
2020-02-24T16:39:23+01:00 INFO: Getting the metric values: container.mem.cache from Influxdb container...
2020-02-24T16:39:23+01:00 DEBUG: Getting metric container.mem.cache from 2 days ago to 1 days ago
2020-02-24T16:39:23+01:00 DEBUG: Getting metric container.mem.cache from 1 days ago to 0 days ago
2020-02-24T16:39:23+01:00 INFO: Getting the metric values: container.mem.rss from Influxdb container...
2020-02-24T16:39:23+01:00 DEBUG: Getting metric container.mem.rss from 2 days ago to 1 days ago
2020-02-24T16:39:24+01:00 DEBUG: Getting metric container.mem.rss from 1 days ago to 0 days ago
2020-02-24T16:39:24+01:00 INFO: Getting the metric values: container.mem.swap from Influxdb container...
2020-02-24T16:39:24+01:00 DEBUG: Getting metric container.mem.swap from 2 days ago to 1 days ago
2020-02-24T16:39:24+01:00 DEBUG: Getting metric container.mem.swap from 1 days ago to 0 days ago
2020-02-24T16:39:25+01:00 INFO: Getting the metric values: container.mem.used_perc from Influxdb container...
2020-02-24T16:39:25+01:00 DEBUG: Getting metric container.mem.used_perc from 2 days ago to 1 days ago
2020-02-24T16:39:25+01:00 DEBUG: Getting metric container.mem.used_perc from 1 days ago to 0 days ago
2020-02-24T16:39:26+01:00 INFO: Compressing gathered data to /opt/cmm-server/cmm-influx-data_2020-02-24_163926.tar.gz
2020-02-24T16:39:26+01:00 INFO: Keeping the 3 newest cmm-influx-data_YYYY-mm-dd_HHMMSS.tar.gz files
2020-02-24T16:39:26+01:00 DEBUG: Removing old cmm-influx-data_YYYY-mm-dd_HHMMSS.tar.gz file(s):
/opt/cmm-server/cmm-influx-data/../cmm-influx-data_2020-02-24_152855.tar.gz
```
## Output
The output is a tar.gz file save in the `outputDataDir`.
The script will leave in `outputDataDir` the 3 newest cmm-influx-data_YYYY-mm-dd_HHMMSS.tar.gz files.
```
2020-02-24T17:17:21+01:00 INFO: Compressing gathered data to /opt/cmm-server/cmm-influx-data_2020-02-24_171721.tar.gz
```

## Cron Job

In order tu execute `influxdb-collect-info.sh` as a cron job, check that the script version is >= v1.0.1

In this example the script `influxdb-collect-info.sh` will be executed everyday dat at 4:00 am.
The output will be redirect to the syslog. `/var/log/messages` in case of RHEL.
The compressed data will be saved in the `outputDataDir`

1. Save the influxdb-collect-info.sh in `/opt/cmm-server/`
2. The attributes should be changed to `+x`
```
# chmod +x influxdb-collect-info.sh
```

3. Add the record in crontab:

```
# crontab -e
0 4 * * * /opt/cmm-server/influxdb-collect-info.sh 2>&1 | logger
```
