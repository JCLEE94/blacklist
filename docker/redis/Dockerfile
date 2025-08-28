FROM redis:7-alpine

# KST 타임존 설정
ENV TZ=Asia/Seoul

# 타임존 패키지 설치
RUN apk add --no-cache tzdata && \
    cp /usr/share/zoneinfo/Asia/Seoul /etc/localtime && \
    echo "Asia/Seoul" > /etc/timezone

# Redis 설정
RUN mkdir -p /usr/local/etc/redis && \
    echo "maxmemory 256mb" >> /usr/local/etc/redis/redis.conf && \
    echo "maxmemory-policy allkeys-lru" >> /usr/local/etc/redis/redis.conf

# Watchtower 라벨
LABEL com.centurylinklabs.watchtower.enable="true"

EXPOSE 6379

CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
