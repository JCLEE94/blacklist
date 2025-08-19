# Custom PostgreSQL Image for Blacklist System
# registry.jclee.me/jclee94/blacklist-postgresql
FROM postgres:15-alpine

# 메타데이터 라벨
LABEL maintainer="jclee94@blacklist-system"
LABEL version="1.0.0"
LABEL description="Custom PostgreSQL for Blacklist IP Management System"
LABEL com.watchtower.enable="true"
LABEL com.watchtower.scope="blacklist"

# 필요한 패키지 설치
RUN apk add --no-cache \
    curl \
    bash \
    postgresql-contrib

# 초기화 스크립트 복사
COPY init-scripts/ /docker-entrypoint-initdb.d/
COPY custom-entrypoint.sh /usr/local/bin/
COPY postgresql.conf /etc/postgresql/postgresql.conf

# 권한 설정
RUN chmod +x /usr/local/bin/custom-entrypoint.sh
RUN chmod 644 /etc/postgresql/postgresql.conf

# PostgreSQL 설정
ENV POSTGRES_DB=blacklist
ENV POSTGRES_USER=blacklist_user
ENV POSTGRES_PASSWORD=blacklist_password_change_me
ENV PGDATA=/var/lib/postgresql/data/pgdata

# 헬스체크
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD pg_isready -U $POSTGRES_USER -d $POSTGRES_DB || exit 1

# 포트
EXPOSE 5432

# 커스텀 entrypoint 사용
ENTRYPOINT ["/usr/local/bin/custom-entrypoint.sh"]
CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]