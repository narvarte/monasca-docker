#!/bin/bash
 
# (C) Copyright 2020 Fujitsu Enabling Software Technology GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
 
###########################
# mem-measurements v1.0.0 #
###########################
 
# Uncomment for verbose logging in bash
#set -x
 
# Set the output directory
outputDataDir="/opt/mem-measurements"
 
# Default amount of max files to keep.
# With a cron job running each hour: 24h x 7d = 168
maxAmountFiles=168
 
# Commands to be executed
declare -a metricNames=(
                        "cat /proc/meminfo"
                        "free -h"
                        "vmstat"
                        "ps axo pmem,vsize,rss,pid,euser,cmd | sort -nr | head -n 1000"
                       )
 
##############################
# Don't edit below this line #
##############################
 
# Creating output data dir
mkdir -p $outputDataDir/data
 
# Collecting memory status data
for metricName in "${metricNames[@]}"; do
    {
     echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
     echo "+ COMMAND: $metricName"
     echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
     eval "$metricName"
     echo -e "\n"
    } &>> tmpdata.dat
done
 
mv tmpdata.dat $outputDataDir/data/"data_$(date +%Y-%m-%d_%H-%M-%S).dat"
 
# Removing old data files
((maxAmountFiles++))
# shellcheck disable=SC2012
ls $outputDataDir/data/data_*.dat -t | tail -n +"$maxAmountFiles" | xargs -I {} rm {}
