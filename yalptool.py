#!/usr/bin/python

from_user_name = "yavdr"
from_series_name = "precise"
from_ppa_name = "unstable-vdr"

to_user_name = from_user_name
to_series_name = from_series_name
to_ppa_name = from_ppa_name

# use False for copy to different PPA
increment_version = True
# expect: <upstream-version>-<package-number><build_number_prefix><build-number>~<series>
# example: 2.0.3-3yavdr0~precise
build_number_prefix = "yavdr"
changelog_message = "automatic rebuild"

debemail = "release@yavdr.org"
debfullname = "yavdr package builder"
gpgkey = "5289F541"

# do only process packages in include_packages
include_packages = []
# and never packages in exclude_packages
exclude_packages = ["vdr"]


import os
import shutil
import sys
from signal import signal, SIGPIPE, SIG_DFL
from subprocess import call
from launchpadlib.launchpad import Launchpad


def get_subdirs(dir):
  return [name for name in os.listdir(dir) if os.path.isdir(name)]

def find_ppa(ppas, name):
  for ppa in ppas:
    if ppa.name == name:
      return ppa
  return None

  
cachedir = os.path.expanduser("~/.launchpadlib/cache/")
cwd = os.getcwd()

print "connecting to Launchpad..."
launchpad = Launchpad.login_anonymously('yalptool', 'production', cachedir)
ubuntu = launchpad.distributions["ubuntu"]
from_series = ubuntu.getSeries(name_or_version=from_series_name)
to_series = ubuntu.getSeries(name_or_version=to_series_name)

os.putenv("DEBEMAIL", debemail)
os.putenv("DEBFULLNAME", debfullname)
os.putenv("GPGKEY", gpgkey)
changelog = os.path.join("debian", "changelog")

from_user = launchpad.people[from_user_name]
if from_user is None:
  print >>sys.stderr, "can't find 'from' user " + from_user_name
  exit(1)

from_ppas = from_user.ppas
from_ppa = find_ppa(from_ppas, from_ppa_name)
if from_ppa is None:
  print >>sys.stderr, "can't find 'from' ppa " + from_ppa_name
  exit(1)

to_user = launchpad.people[to_user_name]
if to_user is None:
  print >>sys.stderr, "can't find 'to' user " + to_user_name
  exit(1)

to_ppas = to_user.ppas
to_ppa = find_ppa(to_ppas, to_ppa_name)
if to_ppa is None:
  print >>sys.stderr, "can't find 'to' ppa " + to_ppa_name
  exit(1)

sources = from_ppa.getPublishedSources(distro_series=from_series, status="Published")
for s in sources:
  source_name = s.source_package_name
  source_version = s.source_package_version
  if (     (not include_packages or source_name in include_packages)
       and (not exclude_packages or not source_name in exclude_packages)):
    print "=========="
    print "source_package_name: " + source_name
    print "source_package_version: " + source_version
    urls = s.sourceFileUrls()
    for u in urls:
      if u.endswith(".dsc"):
        dir = source_name
        if os.access(dir, os.F_OK):
          print >>sys.stderr, dir + " already exists, skipping " + source_name
          break

        new_version = source_version
        if increment_version:
          pos = source_version.rindex("-")
          if pos < 0:
            print >>sys.stderr, source_version + " has not the expected version number scheme, skipping " + source_name
            break

          pos2 = source_version.find(build_number_prefix, pos)
          if pos2 < 0:
            print >>sys.stderr, source_version + " has not the expected version number scheme, skipping " + source_name
            break

          pos2 = pos2 + len(build_number_prefix)
          pos3 = pos2 + 1
          while pos3 < len(source_version):
            if not source_version[pos2:pos3].isdigit():
              pos3 = pos3 - 1
              break
            pos3 = pos3 + 1
          if not source_version[pos2:pos3].isdigit():
            print >>sys.stderr, source_version + " has not the expected version number scheme, skipping " + source_name
            break

          build_number = str(int(source_version[pos2:pos3]) + 1)
          new_version = source_version[:pos2] + build_number
          if source_version.endswith("~" + from_series_name):
            new_version = new_version + "~" + to_series_name
          print "new source_package_version: " + new_version

        os.mkdir(dir)
        os.chdir(dir)
        print "dget -xuq " + u
        call("dget -xuq " + u, shell = True)
        subdirs = get_subdirs(".")
        for subdir in subdirs:
          os.chdir(subdir)
          if os.access(changelog, os.F_OK | os.W_OK) and os.path.isfile(changelog):
            print "dch --newversion " + new_version + " -u medium --distribution " + to_series_name +" --force-distribution \"" + changelog_message + "\""
            call("dch --newversion " + new_version + " -u medium --distribution " + to_series_name +" --force-distribution \"" + changelog_message + "\"", shell = True)
            print "debuild -S -sa -k$GPGKEY"
            call("debuild -S -sa -k$GPGKEY", shell = True, preexec_fn = lambda: signal(SIGPIPE, SIG_DFL))
          os.chdir(os.path.join(cwd, dir))
          changes_file = source_name + "_" + new_version + "_source.changes"
          if not os.access(changes_file, os.F_OK | os.R_OK) or not os.path.isfile(changes_file):
            print >>sys.stderr, "can't find " + changes_file + " for upload"
          else:
            print "dput -U ppa:" + to_user_name + "/" + to_ppa_name + " " + changes_file
            call("dput -U ppa:" + to_user_name + "/" + to_ppa_name + " " + changes_file, shell = True)
        os.chdir(cwd)
        shutil.rmtree(dir)
