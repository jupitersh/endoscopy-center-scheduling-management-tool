#!/bin/sh
# 备份数据库
name=$(date +%m%d%H%M)
sudo docker exec -it mongo mongodump -d app -o /mongo/$name
