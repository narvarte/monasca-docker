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

## Parameters

```
# Set DEBUG option: 1=DEBUG output, 0=no DEBUG output
DEBUG=0

# Uncomment for verbose logging in bash
#set -x

# Set the max ram perc. threshold. Integer 0-100
maxRam=30

# Set the output directory
outputDataDir="/opt/cmm-server/cmm-influx-data"

# Set the monasca containers directory
monascaContainersDir="/opt/cmm-server/monasca-containers"

# Set the amount of past days for collecting metrics
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

Execution with `maxRam=30` and Influxdb consuming 1% of RAM.
```
# ./influxdb-collect-info.sh
2020-02-05T16:45:51+0100 INFO: v1.0.1 ===========================================================================
2020-02-05T16:45:51+0100 INFO: =                           Influxdb Collect Info                                =
2020-02-05T16:45:51+0100 INFO: ==================================================================================
2020-02-05T16:45:53+0100 INFO: RAM used by influxdb service 1% is lower than max. value 30%: no action required
```

Execution with `maxRam=1` and Influxdb consuming 1% of RAM.
```
# ./influxdb-collect-info.sh 
2020-02-05T16:48:13+0100 INFO: v1.0.1 ===========================================================================
2020-02-05T16:48:13+0100 INFO: =                           Influxdb Collect Info                                =
2020-02-05T16:48:13+0100 INFO: ==================================================================================
2020-02-05T16:48:15+0100 WARNING: RAM used by influxdb service 1% is equal or higher than max. value 1% !!!
2020-02-05T16:48:15+0100 INFO: Getting inspect info from Influxdb container...
2020-02-05T16:48:15+0100 INFO: Getting stats info from Influxdb container...
2020-02-05T16:48:17+0100 INFO: Getting process info from Influxdb container
2020-02-05T16:48:17+0100 INFO: Getting shards from Influxdb...
2020-02-05T16:48:17+0100 INFO: Getting retention policies from Influxdb...
2020-02-05T16:48:17+0100 INFO: Getting the list of empty wal files...
2020-02-05T16:48:17+0100 INFO: Getting Influxdb network information...
2020-02-05T16:48:18+0100 INFO: Getting Influxdb memory information...
2020-02-05T16:48:19+0100 INFO: Getting the metric values: container.io.read_bytes from Influxdb container...
2020-02-05T16:48:30+0100 INFO: Getting the metric values: container.io.read_bytes_sec from Influxdb container...
2020-02-05T16:48:42+0100 INFO: Getting the metric values: container.io.write_bytes from Influxdb container...
2020-02-05T16:48:54+0100 INFO: Getting the metric values: container.io.write_bytes_sec from Influxdb container...
2020-02-05T16:49:06+0100 INFO: Getting the metric values: container.mem.cache from Influxdb container...
2020-02-05T16:49:18+0100 INFO: Getting the metric values: container.mem.rss from Influxdb container...
2020-02-05T16:49:30+0100 INFO: Getting the metric values: container.mem.swap from Influxdb container...
2020-02-05T16:49:42+0100 INFO: Getting the metric values: container.mem.used_perc from Influxdb container...
2020-02-05T16:49:54+0100 INFO: Compressing gathered data to /opt/cmm-server/cmm-influx-data_2020-02-05_164954.tar.gz
2020-02-05T16:49:57+0100 INFO: Successfully compressed data to file /opt/cmm-server/cmm-influx-data_2020-02-05_164954.tar.gz
```
## Output
The output is a tar.gz file save in the `outputDataDir`.

```
2020-02-05T16:49:57+0100 INFO: Successfully compressed data to file /opt/cmm-server/cmm-influx-data_2020-02-05_164954.tar.gz
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
0 4 * * * /opt/cmm-server/influxdb-collect-info.sh 2>&1 | logger &
```
