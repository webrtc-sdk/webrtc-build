#!/bin/bash

set -ex

# Retry downloads: a mirror timing out (e.g. packages.microsoft.com on CI
# runners) would otherwise fail the job. Also applies to later apt-get calls.
echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries

apt-get update
# No `apt-get upgrade`: it upgrades everything preinstalled on the runner
# (hundreds of MB of dotnet, azure-cli, mysql, ...) that the build never uses.

# tzdata を noninteractive にしないと実行が止まってしまう
# need to set tzdata to noninteractive or else it'll stop
apt-get -y install tzdata
echo 'Asia/Tokyo' > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata

export DEBIAN_FRONTEND=noninteractive

# rtc_unittests
apt-get -y install libx11-6

# module_unittests
apt-get -y install \
  libxcomposite1 \
  libxdamage1 \
  libxext6 \
  libxfixes3 \
  libxrandr2 \
  libxtst6 \
  libgbm1

# test_support_unittests
# Very large package (525MB), skipping for now
# sudo apt-get install -y libgl1