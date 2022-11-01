SRHT_PATH?=/usr/lib/python3.8/site-packages/srht
MODULE=mansrht/
include ${SRHT_PATH}/Makefile

all: api

api:
	cd api && go generate ./graph
	cd api && go build

.PHONY: all api
