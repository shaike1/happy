#!/bin/bash
# This script runs inside the container and executes netstat on the host network namespace

# Use nsenter to run netstat on host (PID 1 is init, we access host network namespace)
nsenter -t 1 -n netstat -tn 2>/dev/null | grep ESTABLISHED | grep ":3000" | awk "{print \$4,\$5}" | while read local remote; do
    echo "$local|$remote"
done
