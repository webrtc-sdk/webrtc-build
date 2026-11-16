#!/bin/bash

set -ex

apt-get update
apt-get -y upgrade

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
