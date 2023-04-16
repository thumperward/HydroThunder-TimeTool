#!/bin/bash

(
  cd data || exit
  tar xzf test-case.tar.gz
  cd test-case || exit
)
