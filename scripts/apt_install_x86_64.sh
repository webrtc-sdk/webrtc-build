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

apt-get -y install \
  binutils \
  git \
  locales \
  lsb-release \
  pkg-config \
  python3 \
  ninja-build \
  python3-setuptools \
  rsync \
  sudo \
  unzip \
  vim \
  wget \
  xz-utils
