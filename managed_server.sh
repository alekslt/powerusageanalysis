#!/bin/sh

while [ 1 ]; do
	../bin/pserve development.ini --reload
	sleep 5
done
