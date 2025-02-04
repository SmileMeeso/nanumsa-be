"""init schema

Revision ID: 9a237e861a09
Revises: 
Create Date: 2025-02-03 11:05:14.678010

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import func
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = '9a237e861a09'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'email_verify',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('token', sa.String, nullable=False),
        sa.Column('email', sa.String, nullable=False),
        sa.Column('is_verified', sa.Boolean, nullable=False, default=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), nullable=False),
        sa.Column('edited_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), nullable=False, onupdate=func.now())
    )
    op.execute("COMMENT ON TABLE email_verify IS '이메일 인증 테이블';")

    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('nickname', sa.String, nullable=False),
        sa.Column('email', sa.String),
        sa.Column('password', sa.String),
        sa.Column('contacts', sa.String),
        sa.Column('name', sa.String),
        sa.Column('tag', sa.Integer, nullable=False),
        sa.Column('is_deleted', sa.Boolean, nullable=False, default=False),
        sa.Column('social_type', sa.SmallInteger, nullable=False),
        sa.Column('social_uid', sa.String),
        sa.Column('naver_client_id', sa.String),
        sa.Column('kakao_user_id', sa.String),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), nullable=False),
        sa.Column('edited_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), nullable=False, onupdate=func.now())
    )
    op.execute("COMMENT ON TABLE users IS '유저 정보 테이블';")
    op.execute("COMMENT ON COLUMN users.social_type IS '0: 소셜 아님, 1: 구글, 3: 애플, 4: 카카오, 5: 네이버';")
    op.execute("COMMENT ON COLUMN users.social_uid IS 'firebase 기반 소셜 로그인에만 저장되는 컬럼';")
    op.execute("COMMENT ON COLUMN users.tag IS '트리거로 저장되는 8자리 난수';")
    op.execute("COMMENT ON COLUMN users.nickname IS '소셜 가입인 경우 랜덤 부여';")

    op.create_table(
        'login_token',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('token', sa.String, nullable=False),
        sa.Column('user_id', sa.BigInteger),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), nullable=False),
        sa.Column('edited_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), nullable=False, onupdate=func.now())
    )
    op.execute("COMMENT ON TABLE login_token IS '로그인 정보 테이블';")

    op.create_table(
        'share_info',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('admins', sa.String, nullable=False),
        sa.Column('contacts', sa.String, nullable=False),
        sa.Column('jibun_address', sa.String),
        sa.Column('doro_address', sa.String),
        sa.Column('point_lat', sa.Float),
        sa.Column('point_lng', sa.Float),
        sa.Column('point', Geometry(geometry_type='POINT', srid=4326)),
        sa.Column('point_name', sa.String, nullable=False),
        sa.Column('goods', sa.String, nullable=False),
        sa.Column('status', sa.SmallInteger, nullable=False),
        sa.Column('is_deleted', sa.Boolean, nullable=False, default=False),
        sa.Column('register_user', sa.BigInteger, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), nullable=False),
        sa.Column('edited_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), nullable=False, onupdate=func.now())
    )
    op.execute("COMMENT ON TABLE share_info IS '나눔 정보 테이블';")
    op.execute("COMMENT ON COLUMN share_info.admins IS '유저 태그가 콤마로 묶여 문자열로 저장됨';")
    op.execute("COMMENT ON COLUMN share_info.contacts IS '연락처 정보가 콤마로 묶여 문자열로 저장됨';")
    op.execute("COMMENT ON COLUMN share_info.goods IS '물품 정보 json 배열이 문자열로 저장됨';")
    op.execute("COMMENT ON COLUMN share_info.status IS '0: 진행중, 1: 휴식중, 2: 마감, 3: 신고누적';")

    op.create_table(
        'recent_search_keywords',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger, nullable=False),
        sa.Column('keyword', sa.String, nullable=False),
        sa.Column('type', sa.SmallInteger, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), nullable=False),
        sa.Column('edited_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), nullable=False, onupdate=func.now())
    )
    op.execute("COMMENT ON TABLE recent_search_keywords IS '최근 검색어를 저장하는 테이블';")
    op.execute("COMMENT ON COLUMN recent_search_keywords.type IS '0: 엔터쳐서 검색, 1: 검색 버튼 눌러 검색, 2: 키워드 쳐서 나온 목록 눌러 검색, 3: 최근 검색어 눌러 검색';")

    op.create_table(
        'starred_share',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('share_id', sa.BigInteger, nullable=False),
        sa.Column('user_id', sa.BigInteger, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), nullable=False),
        sa.Column('edited_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), nullable=False, onupdate=func.now())
    )
    op.execute("COMMENT ON TABLE starred_share IS '나눔 물품 찜 저장하는 테이블';")

    op.create_table(
        'reset_password',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger, nullable=False),
        sa.Column('token', sa.String, nullable=False),
        sa.Column('email', sa.String, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), nullable=False),
        sa.Column('edited_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), nullable=False, onupdate=func.now())
    )
    op.execute("COMMENT ON TABLE reset_password IS '비밀번호 재설정 토큰 저장 테이블';")

    # users 테이블 태그 생성 트리거와 함수
    op.execute("""
    CREATE OR REPLACE FUNCTION generate_unique_tag()
    RETURNS TRIGGER AS $$
    DECLARE
        new_tag INTEGER;
    BEGIN
        LOOP
            new_tag := floor(random() * 100000000)::INTEGER;  -- 8자리 난수 생성
            IF NOT EXISTS (
                SELECT 1 FROM users WHERE tag = new_tag
            ) THEN
                NEW.tag := new_tag;  -- 중복이 없으면 값을 설정
                RETURN NEW;
            END IF;
        END LOOP;
    END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE TRIGGER set_unique_tag
    BEFORE INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION generate_unique_tag();
    """)

    # share_info 삽입/수정시 point 생성 트리거와 함수
    op.execute("""
    CREATE OR REPLACE FUNCTION set_point_geometry()
    RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.point_lat IS NOT NULL AND NEW.point_lng IS NOT NULL THEN
            NEW.point := ST_SetSRID(ST_MakePoint(NEW.point_lng, NEW.point_lat), 4326);
        ELSE
            NEW.point := NULL;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE TRIGGER populate_point_geometry
    BEFORE INSERT OR UPDATE ON share_info
    FOR EACH ROW
    EXECUTE FUNCTION set_point_geometry();
    """)

def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS set_unique_tag ON users;")
    op.execute("DROP FUNCTION IF EXISTS generate_unique_tag();")

    op.execute("DROP TRIGGER IF EXISTS populate_point_geometry ON share_info;")
    op.execute("DROP FUNCTION IF EXISTS set_point_geometry();")

    op.drop_table('starred_share')
    op.drop_table('recent_search_keywords')
    op.drop_table('share_info')
    op.drop_table('login_token')
    op.drop_table('users')
    op.drop_table('email_verify')
    op.drop_table('reset_password')