# Script mem-measurements.sh v1.0.0

## Introduction

This document describes the use of script `mem-measurements.sh v1.0.0`

**Background**:

The goal of this script is tracking the memory consumption through the execution of a set of memory debug commands.

## Description

The script calls the following commands:

- cat /proc/meminfo
- free -h
- vmstat
- ps axo pmem,vsize,rss,pid,euser,cmd | sort -nr | head -n 1000

On each execution the script creates a dat file with the outputs of commands above:

```
/opt/mem-measurements/data/data_YYYY-MM-DD_hh-mm-ss.dat
```

By default the script keeps 168 dat files, which means one week of data if the script is executed once every hour.

## Excecution

The script should be executed by the **root** user and the attributes should be changed to `500`
```
# chmod 500 mem-measurements.sh
# ./mem-measurements.sh
```

## Cron Job

In order to set `mem-measurements.sh` as a cron job follow these instructions as the **root** user:

In this example the script `mem-measurements.sh` will be executed once every hour at minute 20.

1. Save the script `mem-measurements.sh` in the directory `/opt/mem-measurements/`
2. Change the attributes to `500`
```
# chmod 500 mem-measurements.sh
```

3. Add the record in crontab:

```
# crontab -e
20 * * * * /opt/mem-measurements/mem-measurements.sh
```

4. The directory `/opt/mem-measurements/data/` will keep one week of data.
