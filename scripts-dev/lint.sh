#!/bin/sh
#
# Runs linting scripts over the local checkout
# isort - sorts import statements
# black - opinionated code formatter
# flake8 - lints and finds mistakes

set -e

if [ $# -ge 1 ]
then
    files=$*
  else
    files="drawing_challenge_bot drawing-challenge-bot"
fi

echo "Linting these locations: $files"
isort -y -rc $files
python3 -m black $files
flake8 $files
