#!/bin/bash
# shellcheck disable=SC2128

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

#####################################
# purge-zookeeper-txnlogs.sh v1.0.3 #
#####################################

# Default DEBUG option: 1=DEBUG output, 0=no DEBUG output
DEBUG=0

# Default data directory in ZooKeeper container
zk_data_dir="/data/version-2"

# Default datalog directory in ZooKeeper container
zk_datalog_dir="/datalog/version-2"

# Default amount of txnlog/snapshot to leave in the container
max_old_files=5

#####################################
# Don't edit below this line        #
#####################################

# Exit the script if any statement returns error
set -eo pipefail

log() { echo -e "$(date --iso-8601=seconds)" "$1"; }
error() { log "ERROR: $1"; }
warn() { log "WARN : $1"; }
inf() { log "INFO : $1"; }
debg() { if [ $DEBUG == 1 ]; then
           log "DEBUG: $1";
         fi
       }

inf "v1.0.3 =========================================================================================="
inf "=                                  Purge-ZooKeeper-TxnLogs                                      ="
inf "================================================================================================="
inf ""

# check that max_old_files >= 4
if [ "$max_old_files" -ge 4 ];
  then
      debg "Correct value for parameter max_old_files=$max_old_files";
  else
      error "Invalid value for the parameter max_old_files=$max_old_files Use integer greater or equal than 4"
    exit 1;
fi

inf "Cleaning ZooKeeper container..."
declare -a zookeeper_dirs=("$zk_data_dir"
                           "$zk_datalog_dir")

for zookeeper_dir in "${zookeeper_dirs[@]}"; do

  inf "  Searching for old txnlogs/snapshots at $zookeeper_dir"

  dir_exists=$(docker exec "$(docker ps | grep zookeeper | awk '{print $1}')" \
    sh -c "test -d $zookeeper_dir && echo 'TRUE'")
  if [ "$dir_exists" == "TRUE" ]; then
    debg "    Directory was found $zookeeper_dir"
  else
    error "    Directory was not found $zookeeper_dir"
    break
  fi

  (( zk_cont_max=max_old_files+1 ))
  mapfile -t zookeeper_files < <(docker exec "$(docker ps | grep zookeeper | awk '{print $1}')" \
    ls -t "$zookeeper_dir" | tail -n +"$zk_cont_max")

  if [ ${#zookeeper_files[@]} -eq 0 ]; then
    inf "    No old txnlogs/snapshots were found"
  fi

  for zook_file in "${zookeeper_files[@]}"; do
    inf "    Removing $zookeeper_dir/$zook_file"
    docker exec "$(docker ps | grep zookeeper | awk '{print $1}')" rm -f "$zookeeper_dir"/"$zook_file"
  done
done
inf ""

inf "Cleaning Thresh container..."
mapfile -t zookeeper_dirs < <(docker exec "$(docker ps | grep thresh | awk '{print $1}')" \
  sh -c "find /tmp -type d -name 'version-2' -print0 | xargs -r0 stat -c %y\ %n | sort -r" | awk '{ print $3 }')

if [ -z "$zookeeper_dirs" ]; then
  error "  ZooKeeper's txnlogs/snapshots directory was not found"
  exit 1
fi

found_current_zk_dir=0
for zookeeper_dir in "${zookeeper_dirs[@]}"; do
  if [ $found_current_zk_dir -eq 0  ]; then
    inf "  Found current txnlogs/snapshots directory $zookeeper_dir"
    found_current_zk_dir=1
    continue
  fi
  inf "  Removing unused txnlogs/snapshots directory $zookeeper_dir"
  docker exec "$(docker ps | grep thresh | awk '{print $1}')" rm -rf "$zookeeper_dir"
done

inf "  Searching for old txnlogs/snapshots at ${zookeeper_dirs[0]}"
(( th_cont_max=max_old_files*2+1 ))
mapfile -t zookeeper_files < <(docker exec "$(docker ps | grep thresh | awk '{print $1}')" \
  ls -t "${zookeeper_dirs[0]}" | tail -n +"$th_cont_max")

if [ ${#zookeeper_files[@]} -eq 0 ]; then
  inf "    No old txnlogs/snapshots were found"
fi

for zook_file in "${zookeeper_files[@]}"; do
  inf "    Removing ${zookeeper_dirs[0]}/$zook_file"
  docker exec "$(docker ps | grep thresh | awk '{print $1}')" rm -f "${zookeeper_dirs[0]}"/"$zook_file"
done
