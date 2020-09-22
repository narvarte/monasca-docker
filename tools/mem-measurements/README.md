# Script mem-measurements.sh v1.0.0

## Introduction

This document describes the use of script `mem-measurements.sh v1.0.0`.  
Please replace variables written in _italic_ with concrete values.

**Background**:

The goal of this script is tracking the memory consumption through the execution of a set of memory debug commands.

## Parameters

The script can be called with one optional parameter _output-dir_.  
If the script willl be called without parameter, the default value "/opt/mem-measurements" will be used.  
_output-dir_ will be created, if it doesn't exist.
  
## Description  

The script calls the following commands:

- cat /proc/meminfo
- free -h
- vmstat
- ps axo pmem,vsize,rss,pid,euser,cmd | sort -nr | head -n 1000

On each execution the script creates a dat file with the outputs of commands above:

<pre>
<code>
<i>output-dir</i>/data/data_YYYY-MM-DD_hh-mm-ss.dat
</code>
</pre>

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

1. Save the script `mem-measurements.sh` in a directory _install-dir_, e.g. `/opt/mem-measurements/`
2. Change the attributes to `500`
```
# chmod 500 mem-measurements.sh
```

3. Add the record in crontab:

<pre>
<code>
# crontab -e
20 * * * * <i>install-dir</i>/mem-measurements.sh 2>&1 | logger
</code>
</pre>

4. The directory _output-dir_/data/ will keep one week of data.
