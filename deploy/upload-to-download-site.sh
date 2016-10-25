#!/bin/sh

# Upload source distribution package in `dist` directory to
# New Relic download site.
#
# If running locally, you'll need to set one environment variable:
#
#   1. AGENT_VERSION
#
# By default, the script will upload to the `testing` subdirectory
# on the download servers:
#
#   /data/nr-yum-repo/python_agent/testing
#
# To override the default and upload it to the `release` subdirectory,
# set the following environment variable:
#
#   DOWNLOAD_DIR=/data/nr-yum-repo/python_agent/release
#
# Requires: git, md5sum, and rsync.

set -e

# Run from the top of the repository directory.

cd $(git rev-parse --show-toplevel)

# Define upload function

upload_to_download_site()
{
    if test $# -ne 2
    then
        echo
        echo "ERROR: Wrong number of arguments to upload_to_download_site."
        exit 1
    fi

    SRC=$1
    DST=$2

    CMD="rsync \
        --verbose \
        --perms \
        --ignore-existing \
        --compress\
        $SRC $DST"

    echo
    echo "Running rsync command:"
    echo $CMD

    $CMD
}

# Set and validate environment variables

echo
echo "=== Start uploading ==="
echo
echo "Checking environment variables"

# Source common variables

. ./deploy/common.sh

# If we get to this point, environment variables are OK.

echo "... AGENT_VERSION  = $AGENT_VERSION"
echo "... PACKAGE_NAME   = $PACKAGE_NAME"
echo "... PACKAGE_PATH   = $PACKAGE_PATH"
echo "... MD5_NAME       = $MD5_NAME"
echo "... MD5_PATH       = $MD5_PATH"
echo "... DOWNLOAD_USER  = $DOWNLOAD_USER"
echo "... DOWNLOAD_HOSTS = $DOWNLOAD_HOSTS"
echo "... DOWNLOAD_DIR   = $DOWNLOAD_DIR"

# Make sure permissions are right before uploading

chmod 644 $PACKAGE_PATH
chmod 644 $MD5_PATH

# Bail, if package version already exists on one of the download hosts.

echo
echo "Checking for existing files on download hosts"
echo

for DOWNLOAD_HOST in $DOWNLOAD_HOSTS;
do
    SSH_LOGIN=$DOWNLOAD_USER@$DOWNLOAD_HOST

    PACKAGE_EXISTS="ssh $SSH_LOGIN test -e \"$DOWNLOAD_DIR/$PACKAGE_NAME\""
    MD5_EXISTS="ssh $SSH_LOGIN test -e \"$DOWNLOAD_DIR/$MD5_NAME\""

    echo $PACKAGE_EXISTS

    if $PACKAGE_EXISTS
    then
        echo "ERROR: $PACKAGE_NAME already exists on $DOWNLOAD_HOST."
        exit 1
    fi

    echo $MD5_EXISTS

    if $MD5_EXISTS
    then
        echo "ERROR: $MD5_NAME already exists on $DOWNLOAD_HOST."
        exit 1
    fi
done

# Upload to hosts

for DOWNLOAD_HOST in $DOWNLOAD_HOSTS;
do
    DESTINATION=$DOWNLOAD_USER@$DOWNLOAD_HOST:$DOWNLOAD_DIR

    upload_to_download_site $PACKAGE_PATH $DESTINATION
    upload_to_download_site $MD5_PATH $DESTINATION
done