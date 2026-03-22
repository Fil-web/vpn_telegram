#!/bin/bash

docker compose down
docker compose build vpn_bot
docker compose up -d --remove-orphans
