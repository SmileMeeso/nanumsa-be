from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

import os
import logging

from sqlalchemy.sql import func

from sqlalchemy import Boolean, Column, Integer, String, Time, DateTime, Sequence, Float
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geometry

from src.aws.secretManager import get_secret


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

connection_info = get_secret('candleHelper/DB/postgres/prod')

engine = create_engine(f'postgresql://{connection_info["username"]}:{connection_info["password"]}@{os.getenv("POSTGRESQL_HOST") or "localhost"}:{os.getenv("POSTGRESQL_PORT") or "5432"}/{connection_info["dbname"]}')
session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_db():
    db = session()
    
    try:
        yield db
    finally:
    	db.close()

Base = declarative_base()
Base.metadata.create_all(bind=engine)

class EmailVerify(Base):
    __tablename__ = "email_verify"

    id = Column(Integer, Sequence('email_verify_id_seq', start=0), primary_key=True)
    token = Column(String)
    email = Column(String)
    is_verified = Column(Boolean, default=False)
    edited_at = Column(Time)

class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, Sequence('user_id_seq', start=0), primary_key=True)
    nickname = Column(String)
    email = Column(String)
    contacts = Column(String)
    name = Column(String)
    tag = Column(Integer)
    is_deleted = Column(Boolean, default=False)
    social_type = Column(Integer)
    edited_at = Column(Time)
    password = Column(String)
    social_uid = Column(String)
    naver_client_id = Column(String)
    kakao_user_id = Column(Integer)

class LoginToken(Base):
    __tablename__ = "login_token"

    id = Column(Integer, Sequence('login_token_id_seq', start=0), primary_key=True)
    token = Column(String)
    user_id = Column(Integer)
    edited_at = Column(DateTime)

class ShareInfo(Base):
    __tablename__ = "share_info"

    id = Column(Integer, Sequence('share_item_id_seq', start=0), primary_key=True)

    name = Column(String)
    admins = Column(String)
    contacts = Column(String)
    jibun_address = Column(String)
    doro_address = Column(String)
    point_lat = Column(Float)
    point_lng = Column(Float)
    point_name = Column(String)
    goods = Column(String)
    point = Column(Geometry(geometry_type='POINT', srid=4326))
    register_user = Column(Integer)
    edited_at = Column(DateTime)
    status = Column(Integer,  default=0)
    is_deleted = Column(Boolean, default=False)

class RecentSearchKeywords(Base):
    __tablename__ = "recent_search_keywords"

    id = Column(Integer, Sequence('recent_search_keywords_id_seq', start=0), primary_key=True)
    user_id = Column(Integer)
    keyword = Column(String)
    type = Column(Integer)
    created_at = Column(DateTime, default=func.now())

class StarredShare(Base):
    __tablename__ = "starred_share"

    id = Column(Integer, Sequence('starred_share_id_seq', start=0), primary_key=True)
    share_id = Column(Integer)
    user_id = Column(Integer)

class ResetPassword(Base):
    __tablename__ = "reset_password"

    id = Column(Integer, Sequence('reset_password_id_seq', start=0), primary_key=True)
    user_id = Column(Integer, nullable=False)
    token = Column(String, nullable=False)
    email = Column(String, nullable=False)
    edited_at = edited_at = Column(DateTime)


def object_as_dict(obj):
    return {
        c.key: getattr(obj, c.key)
        for c in inspect(obj).mapper.column_attrs
    }

