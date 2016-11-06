#!/bin/sh

eval $(gpg-agent --daemon)

./yalptool.py -c sundtek-rebuild-stable-vdr-0.5.conf
./yalptool.py -c sundtek-rebuild-stable-yavdr-0.5.conf
./yalptool.py -c sundtek-rebuild-testing-vdr-0.5.conf
./yalptool.py -c sundtek-rebuild-testing-yavdr-0.5.conf

./yalptool.py -c sundtek-rebuild-stable-vdr-0.6.conf
./yalptool.py -c sundtek-rebuild-stable-yavdr-0.6.conf
./yalptool.py -c sundtek-rebuild-testing-vdr-0.6.conf
./yalptool.py -c sundtek-rebuild-testing-yavdr-0.6.conf

./yalptool.py -c sundtek-rebuild-unstable-vdr.conf
./yalptool.py -c sundtek-rebuild-unstable-yavdr.conf

