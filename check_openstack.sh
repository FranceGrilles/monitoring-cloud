#!/bin/bash

# Copyright 2015 France-Grilles - IDGC - CNRS
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
##############################################################################
# Lauch commands/tests, filter and present output to monitoring service
##############################################################################

# Default values
MAXTIME=120
CONF_FILE="config/tempest.conf"

# Other variables
DIRNAME="$( cd "$(dirname "$0")" ; pwd -P )"
TEMPEST=$DIRNAME/tempest
RUN_CMD="$TEMPEST/tools/with_venv.sh"
STATUS_OK=0
STATUS_WARNING=1
STATUS_CRITICAL=2
STATUS_UNKNOWN=3
STATUS_DEPENDENT=4
STATUS_ALL="OWCUD"
SUBUNIT_TRACE="$TEMPEST/.venv/bin/subunit-trace"

# Functions

usage () {
    echo "Usage: $0 [OPTION] ..."
    echo "Run Tempest test suite and filter output for monitoring by Nagios/Icinga"
    echo "Output list of tests, failure traces, and performance data"
    echo ""
    echo "  -c, --config <path_to_file>     Use a custom tempest.conf file location (default : config/tempest.conf)"
    echo "  -e, --regex '^tempest\.regex'   Launch tests according to the regex (better in quotes)"
    echo "  -h, --help                      Print this usage message"
    echo "  -t, --timeout <time_in_sec>     Raise a WARNING if the test(s) run longer (default : 120s)"
    echo "  -u, --update                    Update the virtual environment"
    echo "  -- <single.test.to.run>         After any other options add a double dash following a test.name.to.run"
    echo ""
    echo "Exemple : $0 -t 90 -- tempest.scenario.test_basic_scenario"
    echo "Exemple : $0 -e '(^tempest\.scenario\.test_basic_(scenario|values))'"
    runExit $STATUS_CRITICAL "No test was run !" "time=0, nb_test=0, nb_tests_ok=0, nb_tests_ko=0, nb_skipped=0"
}

getPerfData () {
    STREAM="$1"
    STATUS=$2

    # Filter output to get values

    # List tests status and ids + all errors from tempest's tests (see tempest.conf/[DEFAULT]/default_log_levels)
    SUMMARY=$(echo "$STREAM" | awk '/^\{/ {print $5,$2,$3} /^2[0-9][0-9][0-9]-/ {$1=$2=$3=""; print $0}')
    TIME=$(echo "$STREAM" | awk '/^Sum\ of/ {print $8}')
    PASSED=$(echo "$STREAM" | awk '/^\ -\ Passed:/ {print $3}')
    SKIPPED=$(echo "$STREAM" | awk '/^\ -\ Skipped:/ {print $3}')
    EXFAIL=$(echo "$STREAM" | awk '/^\ -\ Expected\ Fail:/ {print $4}')
    UNEXOK=$(echo "$STREAM" | awk '/^\ -\ Unexpected\ Success:/ {print $4}')
    FAILED=$(echo "$STREAM" | awk '/^\ -\ Failed:/ {print $3}')

    # Construct PerfData

    let NBTESTS=SKIPPED+PASSED+EXFAIL+UNEXOK+FAILED
    let NB_OK=PASSED+EXFAIL
    let NB_KO=UNEXOK+FAILED
    PERFDATA="time=$TIME, nb_tests=$NBTESTS, nb_tests_ok=$NB_OK, nb_tests_ko=$NB_KO, nb_skipped=$SKIPPED"

    # Compute output status

    if [ $PASSED -gt 0 ] || [ $EXFAIL -gt 0 ]; then
        STATUS=$STATUS_OK
    fi

    # Throw a Warning if execution time is over $MAXTIME
    if [ $(bc <<< "($MAXTIME - $TIME) < 0") -eq 1 ] || [ $SKIPPED -gt 0 ] || [ $UNEXOK -gt 0 ]; then
        STATUS=$STATUS_WARNING
    fi

    if [ $FAILED -gt 0 ]; then 
        STATUS=$STATUS_CRITICAL

        # Add details about the failed tests, hidding empty lines and direct output of tests as they are already captured
        TRACE=$(echo "$STREAM" | awk '/^\s*$/ {next} /^2[0-9][0-9][0-9]-/ {next} /^[\{|=]/ {flag=0;printf "\n"}flag; /\]\ ...\ FAILED/ {flag=1;print}')
        SUMMARY=$(echo -e "$SUMMARY\n\n-------------- Details / Trace --------------\n$TRACE")
    fi

    # Go to output/exit
    runExit $STATUS "$SUMMARY" "$PERFDATA"
}

runExit () {
    STATUS=$1
    OUTPUT="$2"
    PERFDATA="$3"

    printf "$OUTPUT\nStatus : $STATUS (%s)|$PERFDATA" $(echo ${STATUS_ALL:$STATUS:1})
    cd $OLDPWD
    exit $STATUS
}

runOneTest () {
    TEST_ID=$1

    # Running a single test using subunit.run
    # Redirecting output and error to subunit-trace then $STREAM
    STREAM=`$RUN_CMD python -m subunit.run $TEST_ID 2>&1 | $SUBUNIT_TRACE`
    STATUS=$?

    getPerfData "$STREAM" $STATUS
}

runRegexTests () {
    REGEX=$1

    # Running many tests using ostestr with a regex
    # Redirecting output and error to subunit-trace then $STREAM
    STREAM=`$RUN_CMD ostestr --serial --no-slowest --no-pretty --subunit --regex $REGEX 2>&1 | $SUBUNIT_TRACE`
    STATUS=$?

    # Have to filter the output because of ostestr auto discovery when using regex
    STREAM=$(sed '/^running/,+4d' <<< "$STREAM")

    getPerfData "$STREAM" $STATUS
}

initEnv () {
    # Load custom tempest.conf file
    if [ -f `readlink -f "$CONF_FILE"` ]; then
        CONF_FILE=`readlink -f "$CONF_FILE"`
        export TEMPEST_CONFIG_DIR=`dirname "$CONF_FILE"`
        export TEMPEST_CONFIG=`basename "$CONF_FILE"`
    fi

    # Check from where we are running the script
    if [ $DIRNAME != $(pwd) ]; then
        PWDOLD=$(pwd)
    fi

    # All commands have to be run from $TEMPEST/ directory
    cd $TEMPEST

    if [ ! -d $TEMPEST/.venv ] || [ $UPDATEVENV ]; then
        python $TEMPEST/tools/install_venv.py
    fi

    if [ ! -d .testrepository ]; then
        ${RUN_CMD} $TEMPEST/.venv/bin/testr init
    fi

    ${RUN_CMD} find $TEMPEST -type f -name "*.pyc" -delete

}

runMain () {
    initEnv

    if [ -n "$TEST" ]; then
        runOneTest $TEST
    elif [ -n "$REGEX" ]; then
        runRegexTests $REGEX
    else
        usage
    fi
}

if ! OPTIONS=$(getopt -o c:e:ht:u -l config:,regex:,help,timeout:,update -- "$@") ; then
    usage
fi
if [ $# -eq 0 ] ; then
    usage    
fi

eval set -- $OPTIONS
FIRST_UU=yes

while [ $# -gt 0 ]; do
    case "$1" in
        -c|--config)
            CONF_FILE=$2
            shift 2
            ;;

        -e|--regex)
            REGEX=$2
            shift 2
            ;;

        -h|--help)
            usage
            ;;

        -t|--timeout)
            MAXTIME=$2
            shift 2
            ;;

        -u|--update)
            UPDATEVENV=1
            shift 
            ;;

        --)
            if [ "yes" == "$FIRST_UU" ]; then
                TEST=$2
                FIRST_UU=no
            fi
            break
            ;;

        *)
            usage
            ;;
    esac
done

runMain

##EOF
