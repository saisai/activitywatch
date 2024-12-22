#!/bin/bash

modules=$(pip3 list --format=legacy | grep 'aa-' | grep -o '^aa-[^ ]*')

for module in $modules; do
    pip3 uninstall -y $module
done

