#!/bin/sh
echo "Switching to dir from arg ($1)"
cd $1
COMMAND=homie_combined.py
LOGFILE=homie-combined.log

writelog() {
  now=`date`
  echo "$now $*" >> $LOGFILE
}

while true ; do
  writelog "Python starting..."
  OUTPUT=$(python $COMMAND 2>/dev/null)
  writelog "Exit status $? - output: ${OUTPUT}"
  sleep 1
done
