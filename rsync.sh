#!/bin/bash

rsync -avzP --delete --exclude='service-logs.log' --exclude='.git/' --exclude='.idea/' --exclude='.venv/' --exclude='__pycache__/' ./ brumberry:~/fpv_crawler/
