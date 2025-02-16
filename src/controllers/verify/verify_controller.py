from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

import os

from src.database import database

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from pydantic import BaseModel

from src.utils import generate_random_string

from datetime import datetime
from zoneinfo import ZoneInfo

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import traceback

from src.aws.secretManager import get_secret

import socketio
import websockets

class VerifyEmailToken(BaseModel):
    email: str

class VerifyEmail(BaseModel):
    token: str


class ChangePassword(BaseModel):
    email: str

router = APIRouter()

seoul_time = datetime.now(ZoneInfo('Asia/Seoul'))

@router.post("/password/change", tags=['verify'])
def send_change_password_email(info: ChangePassword, db: Session = Depends(database.get_db)):
    email = info.email

    stmt = select(database.Users).where(database.Users.email == email)
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()

    if row is None:
        return JSONResponse(content=jsonable_encoder({"error": "일치하는 이메일이 없습니다."}))

    verifyToken = generate_random_string.id_generator(20)

    email_account_auth_info = get_secret('candleHelper/Account/VerifyEmailSender')

    msg = MIMEMultipart('alternative')
    msg['From'] = email_account_auth_info['email']
    msg['To'] = email
    msg['Subject'] = '나눔사 비밀번호 재설정 메일입니다.'

    html = MIMEText('다음의 버튼을 클릭하시면 비밀번호 재설정 화면으로 이동합니다.<br />원하지 않으시면 이 메일을 무시해주세요.<br /><br /><form action="%s" target="_blank method="get"><input id="token" type="hidden" name="token" value="%s" /><input type="submit" value="비밀번호 변경하기" /></form>' % (os.getenv("HOST") + "/change/password" or "http://localhost/change/password",verifyToken), 'html')

    msg.attach(html)

    server = smtplib.SMTP_SSL('smtp.naver.com', 465)
    server.ehlo()
    # server.starttls()
    
    server.login(email_account_auth_info['id'], email_account_auth_info['password'])
    server.sendmail(email_account_auth_info['email'], [email], msg.as_string())
    server.quit()

    db.query(database.ResetPassword).filter(database.ResetPassword.email == info.email).delete()
    db.commit()

    emailVerifyData = database.ResetPassword(email=email, user_id=row.id, edited_at=func.now(), token=verifyToken)
    db.add(emailVerifyData)
    db.commit()

    return JSONResponse(content=jsonable_encoder({"success": "비밀번호 변경 이메일 발송에 성공했습니다."}))
 
@router.post("/verify/email/token", tags=['verify'])
def send_verify_email_and_save_data(email: VerifyEmailToken, db: Session = Depends(database.get_db)):
    email = email.email
    verifyToken = generate_random_string.id_generator(20)

    email_account_auth_info = get_secret('candleHelper/Account/VerifyEmailSender')

    msg = MIMEMultipart('alternative')
    msg['From'] = email_account_auth_info['email']
    msg['To'] = email
    msg['Subject'] = '나눔사 인증 메일입니다.'

    html = MIMEText('다음의 버튼을 클릭하시면 인증 화면으로 이동합니다.<br />인증을 원하지 않으시면 이 메일을 무시해주세요.<br /><br /><form action="%s" target="_blank method="get"><input id="token" type="hidden" name="token" value="%s" /><input type="submit" value="인증하기" /></form>' % (os.getenv("HOST") + "/verify/email" or "http://localhost/verify/email", verifyToken), 'html')

    msg.attach(html)

    server = smtplib.SMTP_SSL('smtp.naver.com', 465)
    server.ehlo()
    # server.starttls()
    
    server.login(email_account_auth_info['id'], email_account_auth_info['password'])
    server.sendmail(email_account_auth_info['email'], [email], msg.as_string())
    server.quit()

    db.query(database.EmailVerify).filter(database.EmailVerify.email == email).delete()
    db.commit()

    emailVerifyData = database.EmailVerify(email=email, edited_at="NOW()", token=verifyToken)
    db.add(emailVerifyData)
    db.commit()

    return JSONResponse(content=jsonable_encoder({"token": verifyToken}))

@router.post("/verify/email", tags=['verify'])
def make_email_verify_with_token(token:VerifyEmail, db: Session = Depends(database.get_db)):
    stmt = select(database.EmailVerify).where(database.EmailVerify.token == token.token)
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()

    if row and row.is_verified is False:
        
        # socket.io 클라이언트 생성
        session_cookie = token.token
        sio = socketio.Client()

        @sio.on('*')
        def any_event(event, sid, data):
            print(event)
            print(sid)
            print(data)

        # 서버와의 연결 이벤트 핸들러
        @sio.event
        def connect():
            print('Connection established')

        # 연결 해제 이벤트 핸들러
        @sio.event
        def disconnect():
            print('Disconnected from server')

        @sio.event
        def connect_error(message):
            print('Connection was rejected due to ' + message)

        sio.connect('url', transports=['websocket'], wait_timeout=10, wait=True)
        sio.send(token.token)

        @sio.event
        def acknowledged(message):
            print('Acknowledged by server:', message)
            # 연결 종료
            sio.disconnect()

        db.query(database.EmailVerify).filter(database.EmailVerify.token == token.token).update({'is_verified': True, 'edited_at': 'NOW()'}, synchronize_session = False)
        db.commit()

        return JSONResponse(content=jsonable_encoder({"email": row.email}))
    elif row and row.is_verified is True:
        return JSONResponse(content=jsonable_encoder({"result": 0}))
    else:
        return JSONResponse(content=jsonable_encoder({"result": 1}))
    