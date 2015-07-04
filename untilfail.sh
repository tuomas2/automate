#!/bin/bash
while true; do
    rm unittests.log*
    if py.test tests/ $@; then
        echo ok
    else
        exit 0 
    fi
done
