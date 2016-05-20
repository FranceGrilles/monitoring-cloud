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
MAXTIME=180
CONF_FILE="tempest.conf"

# Other variables
DIRNAME="$( cd "$(dirname "$0")" ; pwd -P )"
BLFILE="$DIRNAME/config/tests_blacklist.txt"
TEMPEST=$DIRNAME/tempest
RUN_CMD="$TEMPEST/tools/with_venv.sh"
STATUS_OK=0
STATUS_WARNING=1
STATUS_CRITICAL=2
STATUS_UNKNOWN=3
STATUS_DEPENDENT=4
STATUS_ALL=('OK' 'WARNING' 'CRITICAL' 'UNKNOWN' 'DEPENDENT')
SUBUNIT_TRACE="$TEMPEST/.venv/bin/subunit-trace"

# Functions

usage () {
    echo "Usage: $0 [OPTION] ..."
    echo "Run Tempest test suite and filter output for monitoring by Nagios/Icinga"
    echo "Output list of tests, failure traces, and performance data"
    echo ""
    echo "  -c, --config <path_to_file>     Use a custom tempest.conf file location (default : tempest.conf)"
    echo "  -e, --regex '^tempest\.regex'   Launch tests according to the regex (better in quotes)"
    echo "  -h, --help                      Print this usage message"
    echo "  -t, --timeout <time_in_sec>     Raise a WARNING if the test(s) run longer (default : 180s)"
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
    OUT=""

    ## Filter output to get values

    # Check if there was at least a test
    NO_TEST="The test run didn't actually run any tests"
    if [[ $STREAM =~ $NO_TEST ]]; then 
        runExit $STATUS_UNKNOWN "$STREAM" "time=0, nb_tests=0, nb_tests_ok=0, nb_tests_ko=0, nb_skipped=0"        
    fi

    # Get test status
    TIME=$(echo "$STREAM" | awk '/^Ran:.*tests\ in/ {printf "%d", $5}')
    PASSED=$(echo "$STREAM" | awk '/^\ -\ Passed:/ {print $3}')
    SKIPPED=$(echo "$STREAM" | awk '/^\ -\ Skipped:/ {print $3}')
    EXFAIL=$(echo "$STREAM" | awk '/^\ -\ Expected\ Fail:/ {print $4}')
    UNEXOK=$(echo "$STREAM" | awk '/^\ -\ Unexpected\ Success:/ {print $4}')
    FAILED=$(echo "$STREAM" | awk '/^\ -\ Failed:/ {print $3}')

    # Construct PerfData for Nagios
    let NBTESTS=SKIPPED+PASSED+EXFAIL+UNEXOK+FAILED
    let NB_OK=PASSED+EXFAIL
    let NB_KO=UNEXOK+FAILED
    PERFDATA="time=$TIME, nb_tests=$NBTESTS, nb_tests_ok=$NB_OK, nb_tests_ko=$NB_KO, nb_skipped=$SKIPPED"

    # Get LOG output from tests (see tempest.conf/[DEFAULT]/default_log_levels)
    PATTERN="^2[0-9][0-9][0-9]-"
    LOGOUTPUT=$(echo "$STREAM" | awk '/^2[0-9][0-9][0-9]-/ {print}')"\n"
    if [[ $LOGOUTPUT =~ $PATTERN ]]; then
        OUT+="-------------- Captured logging --------------\n"
        OUT+=$LOGOUTPUT"\n"
    fi

    # Compute output status
    if [ $PASSED -gt 0 ] || [ $EXFAIL -gt 0 ]; then
        STATUS=$STATUS_OK
    fi

    # Throw a Warning
    if [ $(bc <<< "($MAXTIME - $TIME) < 0") -eq 1 ] || [ $SKIPPED -gt 0 ] || [ $UNEXOK -gt 0 ]; then
        STATUS=$STATUS_WARNING
    fi

    # Add list of skipped tests
    if [ $SKIPPED -gt 0 ]; then
        OUT+="-------------- Skipped Tests --------------\n"
        OUT+=$(echo "$STREAM" | grep "SKIPPED")"\n\n"
    fi

    # Add details about the failed tests
    if [ $FAILED -gt 0 ]; then 
        STATUS=$STATUS_CRITICAL

        OUT+="-------------- Details / Trace --------------"
        # exclude blank lines, OK and SKIPPED tests, LOGOUTPUT
        OUT+=$(echo "$STREAM" | awk '/(^\s*$)|(.*\ ok$)|(.*\ SKIPPED)|(2[0-9][0-9][0-9]-)|(^~)|(^Sum\ of\ execute\ time)/ {next}; 
              /^Captured\ pythonlogging/ {cap=1; next} /^Captured\ traceback/ {cap=0;next}; 
              /^======$/ {skip=20;next} skip>0 {--skip;next};
              /^.*FAILED$/ {print ""}1;')"\n\n"
    fi

    # Add a summary
    OUT+="-------------- Summary --------------\n"
    OUT+=$(echo "$STREAM" | awk 'prt-->0; /^Ran:.*tests\ in/ {prt=5;print}')"\n"

    # Add a header
    OUT="${STATUS_ALL[$STATUS]} : $PERFDATA\n\n"$OUT

    # Go to output/exit
    runExit $STATUS "$OUT" "$PERFDATA"
}

runExit () {
    STATUS=$1
    OUTPUT="$2"
    PERFDATA="$3"

    echo -e "$OUTPUT\nStatus : $STATUS (${STATUS_ALL[$STATUS]})|$PERFDATA" 
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

    # As of https://bugs.launchpad.net/os-testr/+bug/1506215, we cannot use blacklist for now
    # XXX Skipping tests manually :
    # tempest.api.compute.test_authorization    # fail because of custom FGCloud policy
    # tempest.api.fgcloud.test_user_isolation_* # use ./check_isolation.sh instead
    REGFULL='((?!^tempest.api.compute.test_authorization)(?!^tempest.api.fgcloud.test_user_isolation_)('$REGEX'))'

    STREAM=`$RUN_CMD ostestr --serial --no-slowest --no-pretty --subunit --regex $REGFULL 2>&1 | $SUBUNIT_TRACE`
    STATUS=$?

    # Have to filter the output because of ostestr auto discovery when using regex
    STREAM=$(sed '/^running/,+4d' <<< "$STREAM")

    getPerfData "$STREAM" $STATUS
}

initEnv () {
    # Load custom tempest.conf file
    if [ -f `readlink -f "$DIRNAME/config/$CONF_FILE"` ]; then
        CONF_FILE=`readlink -f "$DIRNAME/config/$CONF_FILE"`
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
