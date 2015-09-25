#!/bin/bash

run(){
    # NOTE: you may need this line if you get an error using ip6tables
    # (host needs ip6 kernel modules to use it in the container)
    # sudo modprobe ip6_tables

    # NOTE: to get X11 socket forwarding to work we need this
    xhost local:root

    # Credentials are being passed to the container for auto login
    CREDS_OPTS=''
    if [[ -n $BITMASK_CREDENTIALS ]]; then
        BITMASK_CREDENTIALS=`realpath $BITMASK_CREDENTIALS`
        CREDS_OPTS="-e BITMASK_CREDENTIALS=/data/credentials.ini -v $BITMASK_CREDENTIALS:/data/credentials.ini"
    fi

    if [[ -n $BITMASK_DAEMON ]]; then
        CONTAINER_OPTS="-d"
    else
        CONTAINER_OPTS="--rm -it"
    fi

    CONTAINER_SUFFIX=""
    if [[ -n $BITMASK_HEADLESS ]]; then
        # In case of headless bitmask we don't want to bind the X11 socket
        X11_OPTS=""
        RUN="headless"
        CONTAINER_SUFFIX="-headless"
    else
        X11_OPTS="-v /tmp/.X11-unix:/tmp/.X11-unix"
        X11_OPTS="$X11_OPTS -e DISPLAY=unix$DISPLAY"
        RUN="run"
    fi

    # NOTE: to use containerized VPN from the host you need to add `--net host`
    docker run $CONTAINER_OPTS \
        --privileged \
        $X11_OPTS \
        $CREDS_OPTS \
        -v `pwd`/data/:/data/ \
        -v `pwd`/data/config:/root/.config/leap \
        -p 2984:1984 -p 3013:2013 \
        -e LEAP_DOCKERIZED=1 \
        --name "bitmask$CONTAINER_SUFFIX" \
        test/bitmask $RUN $@

    # Services' related ports
    # eip: ["80", "53", "443", "1194"]
    # mail: ["1984", "2013"]

    # logs when no ip6_tables module is not loaded on host:
    # root@bitmask-container:/bitmask# sudo ip6tables --new-chain bitmask
    # modprobe: ERROR: ../libkmod/libkmod.c:556 kmod_search_moddep() could not open moddep file '/lib/modules/4.1.6-040106-generic/modules.dep.bin'
    # ip6tables v1.4.21: can't initialize ip6tables table `filter': Table does not exist (do you need to insmod?)
    # Perhaps ip6tables or your kernel needs to be upgraded.

    # logs when ip6_tables module is loaded on host:
    # root@bitmask-container:/bitmask# sudo ip6tables --new-chain bitmask
    # root@bitmask-container:/bitmask# # success!
}

shell(){
    xhost local:root

    # NOTE: to use containerized VPN from the host you need to add `--net host`
    docker run --rm -it \
        --privileged \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -e DISPLAY=unix$DISPLAY \
        -v `pwd`/data/:/data/ \
        -v `pwd`/data/config:/root/.config/leap \
        -v `pwd`:/host/ \
        -p 2984:1984 -p 3013:2013 \
        -e LEAP_DOCKERIZED=1 \
        --name bitmask \
        --entrypoint=bash \
        test/bitmask
}

init(){
    JSON=`realpath $1`
    docker run --rm -it \
        -v `pwd`/data:/data \
        -v $JSON:/shared/bitmask.json \
        test/bitmask init ro /shared/bitmask.json
}

update(){
    JSON=`realpath $1`
    docker run --rm -it \
        -v `pwd`/data:/data \
        -v $JSON:/shared/bitmask.json \
        test/bitmask update /shared/bitmask.json
}

clean_config(){
    docker run --rm \
        -v `pwd`/data/config:/root/.config/leap \
        test/bitmask-headless clean_config
}

build(){
    docker build -t test/bitmask .
}

help() {
    echo ">> Bitmask on docker"
    echo "Run the bitmask app in a docker container."
    echo
    echo "Usage: $0 { init bitmask.json | update bitmask.json | build | shell | run | help }"
    echo
    echo "  ?.json : The bitmask*.json file describes the version that will be used for each repo."
    echo
    echo "    init : Clone repositories, install dependencies, and get bitmask ready to be used."
    echo "  update : Update the repositories and install new deps (if needed)."
    echo "   build : Build the docker image for bitmask."
    echo "   shell : Run a shell inside a bitmask docker container (useful to debug)."
    echo "     run : Run the client (any extra parameters will be sent to the app)."
    echo "    help : Show this help"
    echo
    echo " Notes for run: you can set environment variables to tweak how run behaves."
    echo "  - BITMASK_CREDENTIALS='credentials.ini'"
    echo "      Bitmask will use this file to autologin with the given credentials."
    echo "  - BITMASK_DAEMON=1"
    echo "      Bitmask will run in a daemonized container."
    echo "  - BITMASK_HEADLESS=1"
    echo "      Bitmask will run in headless mode, using a virtual X server instead the host's."
    echo "  - LEAP_DOCKERIZED=1"
    echo "      Bitmask will disable the email firewall. IMAP and SMTP services"
    echo "      will bind to 0.0.0.0 instead localhost only."
}


case "$1" in
    run)
        run "$@"
        ;;
    init)
        init $2
        ;;
    update)
        update $2
        ;;
    build)
        build
        ;;
    shell)
        shell
        ;;
    clean_config)
        clean_config
        ;;
    *)
        help
        ;;
esac
