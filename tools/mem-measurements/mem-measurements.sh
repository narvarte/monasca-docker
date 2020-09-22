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
 
# Set default value for output directory
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
 
######### handle input params ##############
if [ $# -gt 1 ]; then
   echo "ERROR: illegal number of parameters, expected format: $0 <output directory>"
   exit 1;
elif [ $# -eq 1 ]; then
   outputDataDir=$1
fi

# Creating output data dir
mkdir -p $outputDataDir/data
 
if [ $? -ne 0 ]; then
   echo "$0: ERROR: output directory $outputDataDir/data could not be created"
   exit 1
fi

echo "$0: collecting information in directory $outputDataDir"

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
