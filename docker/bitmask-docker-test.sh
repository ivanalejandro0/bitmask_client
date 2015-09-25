#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

BASE_PATH=`pwd`  # the path where we start from
WORK_PATH=$BASE_PATH/work/

# Get (download/copy) the needed files to test bitmask
get_files() {
    mkdir -p $WORK_PATH/docker && cd $WORK_PATH/docker

    leapcode="https://raw.githubusercontent.com/leapcode"
    # wget -c $leapcode/bitmask_client/develop/docker/bitmask-docker.sh
    # wget -c $leapcode/bitmask_client/develop/docker/Dockerfile
    # wget -c $leapcode/bitmask_client/develop/docker/leap_bootstrap.sh

    # XXX: temp HACK, copy instead of download since they are WIP
    cp $BASE_PATH/bitmask-docker.sh .
    cp $BASE_PATH/Dockerfile .
    cp $BASE_PATH/leap_bootstrap.sh .

    chmod +x bitmask-docker.sh leap_bootstrap.sh

    cd $WORK_PATH
    [ ! -d mail_breaker ] && git clone https://github.com/leapcode/mail_breaker
    wget -c $leapcode/leap_mail/develop/src/leap/mail/imap/tests/getmail

    chmod +x getmail
}

# Build the docker image and initialize the bitmask repositories
setup_docker() {
    cd $WORK_PATH/docker
    # FIXME: build disabled to prevent local image overwrite
    docker build -t test/bitmask .

    base="$WORK_PATH/docker/data/"
    repo="$base/repositories/bitmask_client"
    venv="$base/bitmask.venv"

    action="init"
    [ -d $repo && -d $venv ] && action="update"
    ./bitmask-docker.sh $action $BASE_PATH/bitmask.json
}

# Seed the config folder with provider files, manually bootstrapped using the
# bitmask app
# Also save the leap.conf file to prevent a "first run start".
seed_provider() {
    $WORK_PATH/docker/bitmask-docker.sh clean_config

    config=$WORK_PATH/docker/data/config
    mkdir -p $config; cd $config

    tar xjf $BASE_PATH/config.tar.bz2
}

# Send a mail batch that will be verified for arrival later.
# The details for the mailing is stored on `options.cfg` file.
send_mail_batch() {
    # options.cfg file with right credentials is needed
    cd $WORK_PATH/mail_breaker/src/
    cp $BASE_PATH/options.cfg .
    ./send-mail-batch.py
}

# Run Bitmask in a container, using a virtual X server and auto login the
# account specified on `credentials.ini`.
run_bitmask() {
    # we need to use a tweaked docker since this one brings UI up and we would
    # like to just start it hidden without X11 forwarding
    cd $WORK_PATH/docker
    cp -f $BASE_PATH/credentials.ini .
    BITMASK_HEADLESS=1 BITMASK_DAEMON=1 BITMASK_CREDENTIALS='credentials.ini' $WORK_PATH/docker/bitmask-docker.sh run -d --danger
}

# Check the bitmask logs and output for any errors.
# Return 0 if no errors, 1 otherwise.
bitmask_logs() {
    cd $WORK_PATH/docker
    error_1=0; error_2=0

    cat data/config/bitmask.log* | grep -E 'Traceback|ERROR|CRITICAL' && error_1=1

    # Parse this too since some errors may not get into the logs
    docker logs bitmask-headless 2>&1 | grep -E 'Traceback|ERROR|CRITICAL' && error_2=1

    [ $error_1 = 0 ] && [ $error_2 = 0 ] && return 0 || return 1
}

# Check for mails on the bitmask account specified on `credentials.ini`.
# Verify that the previously sent mails arrived correctly.
# Return 0 if all the checks passed, 1 otherwise.
check_mails() {
    # * check for mails with getmail script (leap_mail)
    #  - number of mails
    #  - subject of a sample
    #  - date of a sample
    #  - body, headers of a sample
    #  - ... and assert they work.
    #
    # * parse stdio/logfiles (on buildbot report, ideally!)
    return 0  # XXX getmail tool not ready yet

    getmail="$WORK_PATH/getmail"
    credentials="$BASE_PATH/credentials.ini"

    mail_list=`BITMASK_CREDENTIALS=$credentials $getmail --mailbox INBOX`
    mail_count=`BITMASK_CREDENTIALS=$credentials $getmail --mailbox INBOX --count`
    mail_subject=`BITMASK_CREDENTIALS=$credentials $getmail --mailbox INBOX --subject $the_subject`

    # TODO: add checks here and return 0 if all is ok, 1 otherwise.
}

# Stop and remove the running bitmask container
stop_bitmask() {
    docker stop bitmask-headless
    docker kill bitmask-headless
    docker rm bitmask-headless
}

# Main entrypoint where we run the needed steps to make sure that Bitmask works
# on a basic scenario.
do_test() {
    # TODO: needed steps:
    # - register user
    # - bootstrap providers - this could replace seed_provider

    get_files
    setup_docker
    seed_provider
    run_bitmask
    # TODO: check screenshots?
    # send_mail_batch
    sleep 20  # give bitmask some time to sync
    check_mails; mails_error=$?
    bitmask_logs; bitmask_error=$?
    stop_bitmask

    # 0 -> ok ... not 0 -> not ok
    [ $mails_errors = 0 ] && [ $bitmask_errors = 0 ] && exit 0 || exit 1
}

help(){
    echo "Bitmask integration test script"
    echo
    echo "You need to run this script in a directory containing:"
    echo " * bitmask.json    - a version specification for the leap libraries to use."
    echo " * config.tar.gz   - a config folder with provider files, manually bootstrapped using bitmask app"
    echo " * credentials.ini - the credentials to autologin bitmask"
    echo " * options.cfg     - credentials and configs for the batch mail sender"
    echo
}

# XXX: we add this to prevent accidental run until all is working and tested.
if [ -z ${1:-} ]; then
    help
else
    do_test
fi

