#!/bin/sh

./yalptool.py -c sundtek-rebuild-stable-vdr.conf
./yalptool.py -c sundtek-rebuild-stable-yavdr.conf
./yalptool.py -c sundtek-rebuild-testing-vdr.conf
./yalptool.py -c sundtek-rebuild-testing-yavdr.conf
./yalptool.py -c sundtek-rebuild-unstable-vdr.conf
./yalptool.py -c sundtek-rebuild-unstable-yavdr.conf

