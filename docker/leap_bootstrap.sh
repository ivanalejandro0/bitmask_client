#!/bin/bash
######################################################################
# repo-versions.sh
# Copyright (C) 2014, 2015 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
######################################################################
set -e  # Exit immediately if a command exits with a non-zero status.
REPOSITORIES="bitmask_client leap_pycommon soledad keymanager leap_mail bitmask_launcher leap_assets"
PACKAGES="leap_pycommon keymanager soledad/common soledad/client leap_mail bitmask_client"

# Helper to easily determine whether we are running inside a docker container
# or not.
_is_docker() {
    grep -q docker /proc/1/cgroup
}

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}"  )" && pwd  )"

_is_docker && BASE_PATH="/data/" || BASE_PATH=$SCRIPT_DIR
REPOS_ROOT="$BASE_PATH/repositories"  # Root path for all the needed repositories
VENV_DIR="$BASE_PATH/bitmask.venv"  # Root path for all the needed repositories

mkdir -p $REPOS_ROOT

BITMASK_APP="python $REPOS_ROOT/bitmask_client/src/leap/bitmask/app.py"

PS4=">> " # for debugging

# Escape code
esc=`echo -en "\033"`

# Set colors
cc_green="${esc}[0;32m"
cc_yellow="${esc}[0;33m"
cc_blue="${esc}[0;34m"
cc_red="${esc}[0;31m"
cc_normal=`echo -en "${esc}[m\017"`

# Install dependencies, this is debian (and derivate) only.
# For other distros, look for similar names.
apt_install_dependencies() {
    status="installing system dependencies"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x
    sudo apt-get install -y git python-dev python-setuptools \
        python-virtualenv python-pip libssl-dev python-openssl \
        libsqlite3-dev g++ openvpn pyside-tools python-pyside \
        libffi-dev libzmq-dev

    set +x
}

# Install or remove the helper files needed for Bitmask.
helpers() {
    if [[ "$1" == "cleanup" ]]; then
        status="removing helper files"
        echo "${cc_green}Status: $status...${cc_normal}"
        set -x
        sudo rm -f /usr/sbin/bitmask-root
        sudo rm -f /usr/share/polkit-1/actions/se.leap.bitmask.policy
        set +x
    else
        status="installing helper files"
        echo "${cc_green}Status: $status...${cc_normal}"
        set -x
        BASE=$REPOS_ROOT/bitmask_client/pkg/linux
        sudo mkdir -p /usr/share/polkit-1/actions/
        sudo cp $BASE/bitmask-root /usr/sbin/
        sudo cp $BASE/polkit/se.leap.bitmask.policy /usr/share/polkit-1/actions/
        set +x
    fi
}

# Clone the repositories needed to run Bitmask.
# They can be cloned read-only or read-write (if you have access)
# NOTE: if the folder for a repository already exist, that clone will be
# skipped.
clone_repos() {
    local status="clone repositories"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    if [[ "$1" == "rw" ]]; then
        # read-write remotes:
        src="ssh://gitolite@leap.se"
    else
        # read-only remotes:
        src="https://leap.se/git"
    fi
    cd $REPOS_ROOT

    for repo in $REPOSITORIES; do
        [ ! -d $repo ] && git clone $src/$repo
    done

    cd -

    set +x
    echo "${cc_green}Status: $status done!${cc_normal}"
}

# Move to a specific point in git history for each of the repositories.
# That point is specified in a json file. Each point can be a tag or a branch.
checkout_repos(){
    local status="checkout repositories"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    for repo in $REPOSITORIES; do
        version=$(cat $1 | python -c "import json,sys;obj=json.load(sys.stdin);print obj['$repo'];")
        cd $REPOS_ROOT/$repo
        git fetch origin && git fetch --tags origin

        if [[ -n `git tag -l | grep $version` ]]; then
            # if is a tag
            git checkout -f $version
        else
            # if is a branch
            git reset --hard origin/$version
        fi
    done

    set +x
    echo "${cc_green}Status: $status done!${cc_normal}"
}

# Create a virtualenv and upgrade pip
create_venv() {
    local status="creating virtualenv"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    virtualenv $VENV_DIR && source $VENV_DIR/bin/activate
    pip install --upgrade pip  # get the latest pip

    set +x
    echo "${cc_green}Status: $status done.${cc_normal}"
}

# Do a 'develop mode' install for each repository.
# NOTE: the installations are done inside the virtualenv.
setup_develop() {
    local status="installing packages"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands
    cd $REPOS_ROOT
    source $VENV_DIR/bin/activate

    # do a setup develop in every package
    for package in $PACKAGES; do
        cd $REPOS_ROOT/$package
        python setup.py develop --always-unzip
    done

    set +x
    echo "${cc_green}Status: $status done.${cc_normal}"
}

# Install all the external Bitmask dependencies, they are specified on each
# repository.
install_dependencies() {
    local status="installing dependencies"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands
    cd $REPOS_ROOT
    source $VENV_DIR/bin/activate

    # install defined 3rd party dependencies for every package
    for package in $PACKAGES; do
        cd $REPOS_ROOT/$package
        pkg/pip_install_requirements.sh --use-leap-wheels
    done

    # symlink system's PySide inside the virtualenv
    $REPOS_ROOT/bitmask_client/pkg/postmkvenv.sh

    # XXX: hack to solve gnupg version problem
    pip uninstall -y gnupg && pip install gnupg

    set +x
    echo "${cc_green}Status: $status done.${cc_normal}"
}

# Helper to remove the bitmask config folder
clean_config() {
    local status="clean config folder"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    rm -fr ~/.config/leap

    set +x
    echo "${cc_green}Status: $status done.${cc_normal}"
}

# In order to get Bitmask running on a docker container there are a couple of
# actions that we need to do. This helper takes care of them.
# We need as a $1 parameter the X DISPLAY variable, this is used when we need
# to run a virtual X server.
docker_stuff() {
    local status="doing stuff needed to run bitmask on a docker container"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    helpers
    DISPLAY=$1 lxpolkit &
    sleep 0.5

    # this is needed for pkexec
    mkdir -p /var/run/dbus
    DISPLAY=$1 dbus-daemon --system | true

    set +x
    echo "${cc_green}Status: $status done.${cc_normal}"
}

# Run the bitmask client
run() {
    local status="running client"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x

    shift  # remove 'run' from arguments list
    passthrough_args=$@

    _is_docker && docker_stuff ":0"

    source $VENV_DIR/bin/activate
    python $REPOS_ROOT/bitmask_client/src/leap/bitmask/app.py -d $passthrough_args

    set +x
    echo "${cc_green}Status: $status done.${cc_normal}"
}

# Run Bitmask.
# This is meant to be used inside a docker container that does not provide a
# standard X11 server but a virtual one. Specifically `Xvfb`.
# This function also takes a couple of screenshots of the running Bitmask.
run_headless() {
    local status="running headless client"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x

    shift  # remove 'run' from arguments list
    passthrough_args=$@

    # This no longer works, keep it here just in case we need an alternative in the future.
    # startx -- `which Xvfb` :1 -screen 0 1024x768x24 &
    Xvfb :1 -screen 0 1024x768x16 &> xvfb.log  &
    sleep 1  # wait the X server to start

    _is_docker && docker_stuff ":1"

    source $VENV_DIR/bin/activate
    DISPLAY=:1 $BITMASK_APP -d $passthrough_args &

    sleep 2  # wait for bitmask to start
    DISPLAY=:1 import -window root $BASE_PATH/bitmask-started.png

    sleep 15  # wait for bitmask to login
    DISPLAY=:1 import -window root $BASE_PATH/bitmask-logged.png

    set +x
    echo "${cc_green}Status: $status done.${cc_normal}"
}

# Initialize Bitmask to be used with this script.
# Clone repos, checkout them, install dependencies, etc.
initialize() {
    shift  # remove 'init' from arguments list
    echo $@
    if [[ "$1" == "ro" ]]; then
        # echo "RO"
        shift  # remove 'ro' from arg list
        clone_repos "ro"
    else
        # echo "RW"
        clone_repos
    fi

    if [[ -z $1 ]]; then
        echo "You need to specify a bitmask.json parameter."
        echo "To see an example go to:"
        echo "https://github.com/leapcode/bitmask_client/blob/develop/docker/bitmask-nightly.json"
        exit 1
    fi

    JSON=`realpath $1`

    checkout_repos $JSON
    create_venv
    install_dependencies
    setup_develop

    cd $REPOS_ROOT/bitmask_client/
    make
    cd -
}

# Update the existing repositories and dependencies.
update() {
    local status="updating repositories"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    if [[ -z $1 ]]; then
        echo "You need to specify a bitmask.json parameter."
        echo "To see an example go to:"
        echo "https://github.com/leapcode/bitmask_client/blob/develop/docker/bitmask-nightly.json"
        exit 1
    fi

    JSON=`realpath $1`

    checkout_repos $JSON
    install_dependencies
    setup_develop

    set +x
    echo "${cc_green}Status: $status done!${cc_normal}"
}


help() {
    echo ">> LEAP bootstrap - help"
    echo "Bootstraps the environment to start developing the bitmask client"
    echo "with all the needed repositories and dependencies."
    echo
    echo "Usage: $0 {init [ro] bitmask.json | update bitmask.json | run | help | deps | helpers}"
    echo
    echo "  ?.json  : The bitmask*.json file describes the version that will be used for each repo."
    echo
    echo "    init  : Initialize Bitmask to be used from code. Clone repos, install dependencies, etc."
    echo "            You can use \`init ro\` in order to use the read-only remotes if you don't have rw access."
    echo "  update  : Update the repositories and install new deps (if needed)."
    echo "     run  : Run the client (any extra parameters will be sent to the app)."
    echo "    help  : Show this help"
    echo " -- system helpers --"
    echo "    deps  : Install the system dependencies needed for bitmask dev (Debian based Linux ONLY)."
    echo " helpers  : Install the helper files needed to use bitmask (Linux only)."
    echo "            You can use \`helpers cleanup\` to remove those files."
    echo " headless : Run bitmask in a virtual X server. Use if you know what you're doing."
    echo
}


case "$1" in
    init)
        initialize "$@"
        ;;
    update)
        update $2
        ;;
    helpers)
        helpers $2
        ;;
    deps)
        apt_install_dependencies
        ;;
    run)
        run "$@"
        ;;
    headless)
        run_headless "$@"
        ;;
    clean_config)
        clean_config
        ;;
    *)
        help
        ;;
esac
