#!/bin/bash
for module in "aa-server" "aa-watcher-afk" "aa-watcher-x11"; do
    ln -s $(pwd)/$module/misc/${module}.service ~/.config/systemd/user/${module}.service
done
