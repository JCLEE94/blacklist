# Custom Redis Image for Blacklist System
# registry.jclee.me/jclee94/blacklist-redis
FROM redis:7-alpine

# 메타데이터 라벨
LABEL maintainer="jclee94@blacklist-system"
LABEL version="1.0.0"
LABEL description="Custom Redis for Blacklist IP Management System"
LABEL com.watchtower.enable="true"
LABEL com.watchtower.scope="blacklist"

# Redis 설정 파일 복사
COPY redis.conf /usr/local/etc/redis/redis.conf
COPY custom-entrypoint.sh /usr/local/bin/

# 권한 설정
RUN chmod +x /usr/local/bin/custom-entrypoint.sh

# 헬스체크 개선
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD redis-cli ping || exit 1

# 기본 포트
EXPOSE 6379

# 커스텀 entrypoint 사용
ENTRYPOINT ["/usr/local/bin/custom-entrypoint.sh"]
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]