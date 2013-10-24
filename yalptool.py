#!/usr/bin/python

import os
import shutil
import sys
from subprocess import call

cachedir = os.path.expanduser("~/.launchpadlib/cache/")
cwd = os.getcwd()

def get_subdirs(dir):
  return [name for name in os.listdir(dir) if os.path.isdir(name)]

from launchpadlib.launchpad import Launchpad
launchpad = Launchpad.login_anonymously('example', 'production', cachedir)

ubuntu = launchpad.distributions["ubuntu"]
series_name_source = "precise"
series_source = ubuntu.getSeries(name_or_version=series_name_source)
series_name_destination = "precise"
series_destination = ubuntu.getSeries(name_or_version=series_name_destination)

os.putenv("DEBEMAIL", "release@yavdr.org")
os.putenv("DEBFULLNAME", "yavdr package builder")
os.putenv("GPGKEY", "5289F541")
changelog = os.path.join("debian", "changelog")

yavdr_name = "yavdr"
yavdr = launchpad.people[yavdr_name]
ppas_yavdr = yavdr.ppas

for ppa in ppas_yavdr:
  if ppa.name == "unstable-vdr":
    sources = ppa.getPublishedSources(distro_series=series_source, status="Published")
    for s in sources:
      source_name = s.source_package_name
      if source_name == "vdr":
        print "=========="
        print "source_package_name: " + s.source_package_name
        print "source_package_version: " + s.source_package_version
        urls = s.sourceFileUrls()
        for u in urls:
          if u.endswith(".dsc"):
            dir = s.source_package_name

            old_version = s.source_package_version
            pos = old_version.rindex("-")
            if pos < 0:
              raise Exception(old_version + " is not debian version number scheme")
            pos2 = pos + 2
            while pos2 < len(old_version):
              if not old_version[pos + 1:pos2].isdigit():
                pos2 = pos2 - 1
                break
              pos2 = pos2 + 1
            count = ""
            if pos2 > pos + 1:
              count = str(int(old_version[pos + 1:pos2]) + 1)
            new_version = old_version[:pos] + "-" + count + "yavdr0"
            print "new source_package_version: " + new_version

            #os.mkdir(dir)
            os.chdir(dir)
            print "dget -xu " + u
            #os.system("dget -xu " + u)
            subdirs = get_subdirs(".")
            for subdir in subdirs:
              os.chdir(subdir)
              if os.access(changelog, os.F_OK | os.W_OK) and os.path.isfile(changelog):
                print "dch --newversion " + new_version + " -u medium --distribution " + series_name_destination +" \"automatic rebuild\""
                #os.system("dch --newversion " + new_version + " -u medium --distribution " + series_name_destination +" \"automatic rebuild\"")
                print "debuild -S -sa -k$GPGKEY"
                #os.system("debuild -S -sa -k$GPGKEY")
              os.chdir(os.path.join(cwd, dir))
              print "dput -U ppa:" + yavdr_name + "/" + ppa.name + " " + source_name + "_" + new_version + "_source.changes"
              #os.system("dput -U ppa:" + yavdr_name + "/" + ppa.name + " " + source_name + "_" + new_version + "_source.changes")
            os.chdir(cwd)
            #shutil.rmtree(dir)
