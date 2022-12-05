sudo docker run -d \
--restart unless-stopped \
--name mongo \
-p 27017:27017 \
-v $PWD/mongo:/mongo \
mongo
