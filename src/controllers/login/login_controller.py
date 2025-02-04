from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from src.database import database

from sqlalchemy import select
from sqlalchemy.orm import Session

from typing import Optional, List

from pydantic import BaseModel

from src.utils import generate_random_string

from korean_name_generator import namer

from datetime import datetime
from zoneinfo import ZoneInfo

from passlib.hash import sha256_crypt

router = APIRouter()

class LoginByTokenInfo(BaseModel):
    token: str

class LoginInfo(BaseModel):
    email: str
    password: str

class LoginBySocialInfo(BaseModel):
    email: Optional[str] = None
    social_type: int
    social_uid: Optional[str] = None
    naver_client_id: Optional[str] = None
    kakao_user_id: Optional[int] = None

class LogoutUserInfo(BaseModel):
    token: str

class SocialUser(BaseModel):
    email: Optional[str] = None
    social_type: int
    social_uid: Optional[str] = None
    naver_client_id: Optional[str] = None
    kakao_user_id: Optional[int] = None

class User(BaseModel):
    email: str
    password: str
    nickname: str
    name: str
    contacts: List[str]

class ChangePasswordRequest(BaseModel):
    password: str
    token: str

seoul_time = datetime.now(ZoneInfo('Asia/Seoul'))

@router.post('/login/token', tags=['login'])
def login_with_token(user: LoginByTokenInfo, db: Session = Depends(database.get_db)):
    stmt = select(database.LoginToken).where(database.LoginToken.token == user.token)
    matched_row = db.execute(stmt)
    row = matched_row.scalars().first()

    if row is None:
        return JSONResponse(content=jsonable_encoder({"error": "해당 토큰에 맞는 유저가 없습니다."}))
    else:
        stmt_user = select(database.Users).where(database.Users.id == row.user_id)
        matched_user_row = db.execute(stmt_user)
        user_row = matched_user_row.scalars().first()

        if user_row is None:
            return JSONResponse(content=jsonable_encoder({"error": "매치되는 유저가 없습니다."}))
        else:
            return JSONResponse(content=jsonable_encoder({"success": { "token": row.token, "nickname": user_row.nickname, "tag": user_row.tag, "isSocial": user_row.social_type != 0 }}))


@router.post('/login/email', tags=['login'])
def login_with_email(loginInfo: LoginInfo, db: Session = Depends(database.get_db)):
    stmt = select(database.Users).where(database.Users.email == loginInfo.email, database.Users.password == sha256_crypt.using(salt='fix').hash(loginInfo.password))
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()

    if row and row.id:
        token_before = db.query(database.LoginToken).filter(database.LoginToken.user_id == row.id).first()

        if token_before is not None:
            db.delete(token_before)
            db.commit()
        token = generate_random_string.generate_secure_string(64)

        loginData = database.LoginToken(token=token, user_id=row.id, edited_at=seoul_time)
        db.add(loginData)    
        db.commit()

        return JSONResponse(content=jsonable_encoder({"success": { "token": token, "nickname": row.nickname, "tag": row.tag, "isSocial": False }}))
    else:
        return JSONResponse(content=jsonable_encoder({"error": "로그인에 실패했습니다."}))
    
@router.post('/login/social', tags=['login'])
def login_with_social(loginInfo: LoginBySocialInfo, db: Session = Depends(database.get_db)):
    stmt = None

    if loginInfo.social_type == 1 or loginInfo.social_type == 3:
        stmt = select(database.Users).where(database.Users.social_uid == loginInfo.social_uid, database.Users.social_type == loginInfo.social_type, database.Users.is_deleted == False)
    elif loginInfo.social_type == 4:
        stmt = select(database.Users).where(database.Users.kakao_user_id == loginInfo.kakao_user_id, database.Users.social_type == loginInfo.social_type, database.Users.is_deleted == False)
    elif loginInfo.social_type == 5:
        stmt = select(database.Users).where(database.Users.naver_client_id == loginInfo.naver_client_id, database.Users.social_type == loginInfo.social_type, database.Users.is_deleted == False)
    else:
        stmt = select(database.Users).where(database.Users.email == loginInfo.email, database.Users.social_type == loginInfo.social_type, database.Users.is_deleted == False)
    
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()

    if row and row.id:
        token_before = db.query(database.LoginToken).filter(database.LoginToken.user_id == row.id).first()

        if token_before is not None:
            db.delete(token_before)
            db.commit()
        token = generate_random_string.generate_secure_string(64)

        loginData = database.LoginToken(token=token, user_id=row.id, edited_at=seoul_time)
        db.add(loginData)    
        db.commit()

        return JSONResponse(content=jsonable_encoder({"success": { "token": token, "nickname": row.nickname, "tag": row.tag, "isSocial": row.social_type != 0 }}))
    else:
        return JSONResponse(content=jsonable_encoder({"error": "로그인에 실패했습니다."}))

@router.post('/login/token', tags=['login'])
def login_with_token(user: LoginByTokenInfo, db: Session = Depends(database.get_db)):
    stmt = select(database.LoginToken).where(database.LoginToken.token == user.token)
    matched_row = db.execute(stmt)
    row = matched_row.scalars().first()

    if row is None:
        return JSONResponse(content=jsonable_encoder({"error": "해당 토큰에 맞는 유저가 없습니다."}))
    else:
        stmt_user = select(database.Users).where(database.Users.id == row.user_id)
        matched_user_row = db.execute(stmt_user)
        user_row = matched_user_row.scalars().first()

        if user_row is None:
            return JSONResponse(content=jsonable_encoder({"error": "매치되는 유저가 없습니다."}))
        else:
            return JSONResponse(content=jsonable_encoder({"success": { "token": row.token, "nickname": user_row.nickname, "tag": user_row.tag, "isSocial": user_row.social_type != 0 }}))

@router.post("/logout", tags=['login'])
def logout_with_token(info: LogoutUserInfo, db: Session = Depends(database.get_db)):
    logout_target = db.query(database.LoginToken).filter(database.LoginToken.token == info.token).first()

    if logout_target is not None:
        db.delete(logout_target)
        db.commit()

        return JSONResponse(content=jsonable_encoder({"success": "로그아웃이 완료되었습니다."}))
    else:
        return JSONResponse(content=jsonable_encoder({"error": "로그아웃 대상이 없습니다."}))

@router.post("/user/new/social", tags=['login'])
def add_new_social_user(user: SocialUser, db: Session = Depends(database.get_db)):
    stmt = None

    if user.social_type == 4:
        stmt = select(database.Users).where(database.Users.kakao_user_id == user.kakao_user_id, database.Users.social_type == user.social_type, database.Users.is_deleted == False)
    elif user.social_type == 5:
        stmt = select(database.Users).where(database.Users.naver_client_id == user.naver_client_id, database.Users.social_type == user.social_type, database.Users.is_deleted == False)
    else:
        stmt = select(database.Users).where(database.Users.email == user.email, database.Users.social_type == user.social_type, database.Users.is_deleted == False)
    
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()

    if row is None:
        nickname = namer.generate(True)

        userData = database.Users(email=user.email, nickname=nickname, contacts=None, name=None, password=None, edited_at='NOW()', social_type=user.social_type, social_uid=user.social_uid, naver_client_id=user.naver_client_id, kakao_user_id=user.kakao_user_id)
        db.add(userData)    
        db.commit()

    class SocialLoginUser:
        email = user.email
        social_type = user.social_type
        naver_client_id = user.naver_client_id
        kakao_user_id = user.kakao_user_id
        social_uid = user.social_uid

    return login_with_social(SocialLoginUser, db)

@router.post("/user/new", tags=['login'])
def add_new_user(user: User, db: Session = Depends(database.get_db)):
    stmt = select(database.Users).where(database.Users.email == user.email)
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()

    if row:
        return JSONResponse(content=jsonable_encoder({"error": "이미 존재하는 이메일입니다."}))
    else:
        userData = database.Users(email=user.email, nickname=user.nickname, contacts=",".join(user.contacts), name=user.name, password=sha256_crypt.using(salt='fix').hash(user.password), edited_at='NOW()', social_type=0)
        db.add(userData)    
        db.commit()

        class LoginUser:
            email = userData.email
            password = user.password

        return login_with_email(LoginUser, db)

@router.patch("/user/password/token", tags=['login'])
def add_new_user(info: ChangePasswordRequest, db: Session = Depends(database.get_db)):
    stmt = select(database.ResetPassword).where(database.ResetPassword.token == info.token)
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()

    if row is None:
        return JSONResponse(content=jsonable_encoder({"error": "존재하지 않거나 만료된 토큰입니다."}))
    else:
        db.query(database.Users).filter(database.Users.id == row.user_id).update({'password': sha256_crypt.using(salt='fix').hash(info.password)})
        db.commit()

        expired_token_row = db.query(database.ResetPassword).filter(database.ResetPassword.token == info.token).first()
        db.delete(expired_token_row)
        db.commit()

        return JSONResponse(content=jsonable_encoder({"success": "비밀번호 변경이 완료되었습니다."}))
