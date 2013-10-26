#!/usr/bin/python
# -*- coding:utf-8 -*-
from __future__ import print_function
import ConfigParser
import argparse
import hashlib
import subprocess
import os
import shutil
import sys
import urllib2
from signal import signal, SIGPIPE, SIG_DFL
from launchpadlib.launchpad import Launchpad
from pprint import pprint


def get_subdirs(pdir):
  return [name for name in os.listdir(pdir) if os.path.isdir(name)]


def find_ppa(ppas, name):
  for ppa in ppas:
    if ppa.name == name:
      return ppa
  return None


def md5_for_file(filename):
  md5 = hashlib.md5()
  f = open(filename)
  while True:
    data = f.read(128)
    if not data:
      break
    md5.update(data)
  return md5.digest()


def copy_packages(config):
    cachedir = os.path.join(os.path.expanduser("~"), ".launchpadlib", "cache")
    cwd = os.getcwd()

    print("connecting to Launchpad...")
    launchpad = Launchpad.login_anonymously('yalptool', 'production', cachedir)
    ubuntu = launchpad.distributions["ubuntu"]
    from_series = ubuntu.getSeries(name_or_version=config.from_series_name)
    to_series = ubuntu.getSeries(name_or_version=config.to_series_name)

    changelog = os.path.join("debian", "changelog")

    from_user = launchpad.people[config.from_user_name]
    if not from_user:
      exit("can't find 'from' user {0}".format(config.from_user_name))

    from_ppas = from_user.ppas
    from_ppa = find_ppa(from_ppas, config.from_ppa_name)
    if not from_ppa:
      exit("can't find 'from' ppa {0}".format(config.from_ppa_name))

    to_user = launchpad.people[config.to_user_name]
    if not to_user:
      exit("can't find 'to' user {0}".format(config.to_user_name))

    to_ppas = to_user.ppas
    to_ppa = find_ppa(to_ppas, config.to_ppa_name)
    if not to_ppa:
      exit("can't find 'to' ppa {0}".format(config.to_ppa_name))

    sources = from_ppa.getPublishedSources(distro_series=from_series,
                                                             status="Published")
    failed_sources = []
    for s in sources:
      source_name = urllib2.unquote(s.source_package_name).decode("utf8")
      source_version = s.source_package_version
      if ((not config.include_packages or source_name in config.include_packages)
          and (not config.exclude_packages or not source_name in config.exclude_packages)):
        print("==========\n"
              "source_package_name:", source_name, "\n"
              "source_package_version:", source_version)
        urls = s.sourceFileUrls()
        for u in urls:
          if u.endswith(".dsc"):
            u = urllib2.unquote(u).decode("utf8")
            print(source_name)
            pdir = source_name
            if os.access(pdir, os.F_OK):
              print("{0} already exists, skipping {1}".format(pdir, source_name),
                    file=sys.stderr)
              failed_sources.append(source_name)
              break

            new_version = source_version
            if config.increment_version:
              pos = source_version.rindex("-")
              if pos < 0:
                print("{0} has not the expected version number scheme, skipping {1}".format(
                      source_version,source_name), file=sys.stderr)
                failed_sources.append(source_name)
                break

              pos2 = source_version.find(config.build_number_prefix, pos)
              if pos2 < 0:
                print("{0} has not the expected version number scheme, skipping {1}".format(
                      source_version, source_name), file=sys.stderr)
                failed_sources.append(source_name)
                break

              pos2 = pos2 + len(config.build_number_prefix)
              pos3 = pos2 + 1
              while pos3 < len(source_version):
                if not source_version[pos2:pos3].isdigit():
                  pos3 = pos3 - 1
                  break
                pos3 = pos3 + 1
              if not source_version[pos2:pos3].isdigit():
                print("{0} has not the expected version number scheme, skipping {1}".format(
                      source_version, source_name), file=sys.stderr)
                failed_sources.append(source_name)
                break

              build_number = str(int(source_version[pos2:pos3]) + 1)
              new_version = source_version[:pos2] + build_number
              if source_version.endswith("~" + config.from_series_name):
                new_version = new_version + "~" + config.to_series_name
              print("new source_package_version:", new_version)

            print("")
            os.mkdir(pdir)
            os.chdir(pdir)
            print("dget -xuq {0}".format(u))
            subprocess.call(["dget", "-xuq", u], env=os.environ)
            subdirs = get_subdirs(".")
            for subdir in subdirs:
              os.chdir(subdir)
              if (os.access(changelog, os.F_OK | os.W_OK) and 
                                                     os.path.isfile(changelog)):
                md5_pre = md5_for_file(changelog)
                print(("dch --newversion {0} -u medium --distribution {1}"
                       "--force-distribution \"{2}\"").format(new_version,
                                                              config.to_series_name,
                                                              config.changelog_message)
                )
                subprocess.call(["dch", "--newversion", new_version,
                                "-u", "medium",
                                "--distribution", config.to_series_name,
                                "--force-distribution", config.changelog_message],
                                env=os.environ)
                md5_post = md5_for_file(changelog)
                if md5_pre == md5_post:
                  print("can't modify changelog of {0}".format(source_name),
                        file=sys.stderr)
                  failed_sources.append(source_name)
                  break
                  
                print("debuild -S -sa -k{0}".format(os.environ["GPGKEY"]))
                subprocess.call(["debuild", "-S", "-sa", "-k{0}".format(
                                                         os.environ["GPGKEY"])],
                                preexec_fn = lambda: signal(SIGPIPE, SIG_DFL),
                                env=os.environ)

              os.chdir(os.path.join(cwd, pdir))
              changes_file = "{0}_{1}_source.changes".format(
                                                       source_name, new_version)
              if (not os.access(changes_file, os.F_OK | os.R_OK) or 
                  not os.path.isfile(changes_file)):
                print("can't find {0} for upload".format(changes_file),
                      file=sys.stderr)
                failed_sources.append(source_name)
              else:
                print("dput -U ppa:{0}/{1} {2}".format(config.to_user_name,
                                                        config.to_ppa_name,
                                                        changes_file))
                subprocess.call(["dput", "-U", "ppa:{0}/{1}".format(
                                                            config.to_user_name,
                                                            config.to_ppa_name),
                                changes_file], env=os.environ)

            os.chdir(cwd)
            try:
              shutil.rmtree(pdir.encode('utf-8'))
            except Exception as e:
              print("can't remove directory {0}".format(pdir), file=sys.stderr)
              print(e)
              failed_sources.append(source_name)

    if failed_sources:
      print("there were failures on the following packages:")
      print(failed_sources, file=sys.stderr)


class Config:
    def __init__(self):
        argparser = argparse.ArgumentParser(
                                      description='Copy packages in Launchpad.')
        argparser.add_argument('-c', '--config', metavar='CONFIG',
                               dest='config', action='append', default=None, 
                               help='config file(s)')
        args = vars(argparser.parse_args())
        self.configparser = ConfigParser.SafeConfigParser()
        self.configparser.read(args["config"])
        self.get_config()

    def get_setting(self, category, setting, default=None):
        if self.configparser.has_option(category, setting):
            return self.configparser.get(category, setting)
        else:
            return default

    def get_settingb(self, category, setting, default=False):
        if self.configparser.has_option(category, setting):
            return self.configparser.getboolean(category, setting)
        else:
            return default
        
    def get_config(self):
        # Launchpad Options
        self.from_user_name = self.get_setting("Launchpad", "from_user_name")
        self.from_series_name = self.get_setting("Launchpad", "from_series_name")
        self.from_ppa_name = self.get_setting("Launchpad", "from_ppa_name")
        self.to_user_name = self.get_setting("Launchpad", "to_user_name",
                                                            self.from_user_name)
        self.to_series_name = self.get_setting("Launchpad", "to_series_name",
                                                          self.from_series_name)
        self.to_ppa_name = self.get_setting("Launchpad", "to_ppa_name",
                                                             self.from_ppa_name)
        # Package Options
        self.increment_version = self.get_settingb("Options", "increment_version")
        self.build_number_prefix = self.get_setting("Options", "build_number_prefix",
                                               "ubuntu")
        self.changelog_message = self.get_setting("Options", "changelog_message",
                                               "automatic rebuild")
        # if not empty process only packages in include_packages
        self.include_packages = self.get_setting("Options", "include_packages",
                                                "").split()
        self.exclude_packages = self.get_setting("Options", "exclude_packages",
                                                "").split()
        # Maintainer
        self.debemail = self.get_setting("Maintainer", "debemail")
        self.debfullname = self.get_setting("Maintainer", "debfullname")
        self.gpgkey = self.get_setting("Maintainer", "gpgkey")
        
        # set os.environ Variables
        os.environ["DEBEMAIL"] =  self.debemail
        os.environ["DEBFULLNAME"] = self.debfullname
        os.environ["GPGKEY"] = self.gpgkey


def main():
    config = Config()
    pprint(vars(config))
    copy_packages(config)

        
if __name__ == '__main__':
    main()
