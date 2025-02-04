from fastapi import APIRouter, Depends, Response, Header, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from src.database import database

import logging

from sqlalchemy import select, func, delete, case, cast, update
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import ARRAY

from typing import Optional, List

from pydantic import BaseModel

from src.utils import generate_random_string, str_to_bool
from geoalchemy2.shape import to_shape

import requests, json

from korean_name_generator import namer

from datetime import datetime
from zoneinfo import ZoneInfo

from passlib.hash import sha256_crypt
from src.aws.secretManager import get_secret

import firebase_admin
from firebase_admin import auth
from firebase_admin import credentials

import os

class EditWithTokenUserInfo(BaseModel):
    nickname: Optional[str] = None
    password: Optional[str] = None
    contacts: Optional[str] = None
    tag: Optional[int] = None
    password: Optional[str] = None

class ShareInfo(BaseModel):
    name: str
    admins: str
    contacts: Optional[str] = None
    jibun_address: Optional[str] = None
    doro_address: Optional[str] = None
    point_lat: Optional[float] = None
    point_lng: Optional[float] = None
    point_name: str
    goods: str

class ShareChangeStatusInfo(BaseModel):
    id: int
    status: int
    tag: int

class ShareChangeInfo(BaseModel):
    id: int
    tag: int
    goods: Optional[str] = None
    name: Optional[str] = None
    jibun_address: Optional[str] = None
    doro_address: Optional[str] = None
    point_lat: Optional[float] = None
    point_lng: Optional[float] = None
    point_name: Optional[str] = None
    contacts: Optional[str] = None
    admins: Optional[str] = None

class LikeSearchInfo(BaseModel):
    map_only: Optional[str] = None
    southwest_lng: Optional[float] = None
    southwest_lat: Optional[float] = None
    northeast_lng: Optional[float] = None
    northeast_lat: Optional[float] = None

class User(BaseModel):
    id: int

class RecentKeyword(BaseModel):
    keyword: str
    type: int

class ShareStarInfo(BaseModel):
    id: int
    to_be: bool

class UpdateComplexedShareInfo(BaseModel):
    id: int
    type: str
    admins: Optional[str] = None

class UpdateComplexedShareInfoRequest(BaseModel):
    data: List[UpdateComplexedShareInfo]

def verify_token(auth_token: str = Header(None), db: Session = Depends(database.get_db)):
    if auth_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="AuthToken header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    stmt = select(database.LoginToken).where(database.LoginToken.token == auth_token)
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()
    
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return User(id = row.user_id)

def get_token_using_id(id: int, db: Session):
    stmt = select(database.Users).where(database.Users.id == id)
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()

    if row is None:
        return None
    else:
        return row.tag

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_token)])

seoul_time = datetime.now(ZoneInfo('Asia/Seoul'))


cred = credentials.Certificate(os.environ["NANUMSA_SERVER_FIREBASE_ADMIN_CREDENTIAL_FILE_PATH"])
firebase_admin.initialize_app(cred)

@router.patch('/user/nickname', tags=['app'])
def change_nickname_with_user_token(userInfo: EditWithTokenUserInfo, user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    db.query(database.Users).filter(database.Users.id == user.id).update({'nickname': userInfo.nickname})
    db.commit()

    return JSONResponse(content=jsonable_encoder({"success": { "nickname": userInfo.nickname }}))

@router.patch('/user/password', tags=['app'])
def change_password_with_user_token(userInfo: EditWithTokenUserInfo, user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    db.query(database.Users).filter(database.Users.id == user.id).update({'password': sha256_crypt.using(salt='fix').hash(userInfo.password)})
    db.commit()

    return JSONResponse(content=jsonable_encoder({"success": "비밀번호가 성공적으로 변경되었습니다." }))

@router.patch('/user/contacts', tags=['app'])
def change_contacts_with_user_token(userInfo: EditWithTokenUserInfo, user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    db.query(database.Users).filter(database.Users.id == user.id).update({'contacts': userInfo.contacts})
    db.commit()

    return JSONResponse(content=jsonable_encoder({"success": "연락처가 성공적으로 변경되었습니다." }))

@router.post('/user/password', tags=['app'])
def change_password_with_user_token(userInfo: EditWithTokenUserInfo, user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    stmt_user = select(database.Users).where(database.Users.id == user.id, database.Users.password == sha256_crypt.using(salt='fix').hash(userInfo.password))
    matched_row_user = db.execute(stmt_user)
    row_user = matched_row_user.scalars().first()

    if row_user is None:
        return JSONResponse(content=jsonable_encoder({"error": "비밀번호가 틀립니다."}))
    else:
        return JSONResponse(content=jsonable_encoder({"success": "비밀번호가 일치합니다." }))

@router.get('/user/contacts', tags=['app'])
def pass_contacts_with_user_token(user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    stmt_uer = select(database.Users).where(database.Users.id == user.id)
    matched_row_user = db.execute(stmt_uer)
    row_user = matched_row_user.scalars().first()

    if row_user is None:
        return JSONResponse(content=jsonable_encoder({"error": "유저 정보를 찾을 수 없습니다."}))
    else:
        return JSONResponse(content=jsonable_encoder({"success": { "contacts": row_user.contacts }}))

@router.get('/user/tags/{tags}', tags=['app'])
def pass_tag_with_user_tag(tags: str, db: Session = Depends(database.get_db)):
    tags_tuple = tuple(int(num) for num in tags.split(','))

    stmt_tags = select(database.Users).where(database.Users.tag.in_(tags_tuple), database.Users.is_deleted != True)
    matched_row_tags = db.execute(stmt_tags)
    rows_as_dicts = matched_row_tags.mappings().all()

    response_data = [user["Users"] for user in rows_as_dicts]

    if not rows_as_dicts:
        return JSONResponse(content=jsonable_encoder({"error": "유저 정보를 찾을 수 없습니다."}))
    else:
        return JSONResponse(content=jsonable_encoder({"success": response_data}))

@router.get("/address", tags=['app'])
def read_address_with_keyword(keyword: str):
    url = "https://business.juso.go.kr/addrlink/addrLinkApi.do"
    token = get_secret('candleHelper/authToken/searchAddress')
    data = {"confmKey": token['token'], "currentPage": 1, "countPerPage": 10, "keyword": keyword, "resultType": "json"}
    response = requests.get(url, data=data)

    kakao_url = "https://dapi.kakao.com/v2/local/search/address.${FORMAT}"
    kakao_token = get_secret('candleHelper/authToken/searchAddressToPoint')
    kakao_headers = {"Authorization": "KakaoAK %s"  % (kakao_token['token'])}

    returnResponse = []

    for juso in response.json()['results']['juso']:
        kakao_params = {"query": juso['jibunAddr']}
        kakao_response = requests.get(kakao_url, headers=kakao_headers, params=kakao_params)

        kakao_response_address_info = kakao_response.json()['documents'][0]['address']

        returnResponse.append({'doroAddress': juso['roadAddrPart1'], 'jibunAddress': juso['jibunAddr'], 'lat': float(kakao_response_address_info['y']), 'lng': float(kakao_response_address_info['x'])})

    returnResponse = json.dumps(returnResponse)
    return Response(returnResponse, media_type="application/json")

@router.post("/share/add", tags=['app'])
def add_share_info(shareInfo: ShareInfo, user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    registed_id = user.id

    share_info = database.ShareInfo(
        name=shareInfo.name,
        admins=shareInfo.admins, 
        contacts=shareInfo.contacts,
        jibun_address=shareInfo.jibun_address,
        doro_address=shareInfo.doro_address,
        point_lat=shareInfo.point_lat,
        point_lng=shareInfo.point_lng,
        point_name=shareInfo.point_name,
        goods=shareInfo.goods,
        register_user=registed_id,
        edited_at=seoul_time
    )
    db.add(share_info)    
    db.commit()

    return JSONResponse(content=jsonable_encoder({"success": share_info.id}))

@router.patch("/share/status/{id}", tags=['app'])
def chage_share_status(shareInfo: ShareChangeStatusInfo, user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    stmt = select(database.ShareInfo).where(database.ShareInfo.id == shareInfo.id)
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()
    
    if row is None:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터가 없습니다."}))
    
    admins = list(map(int, row.admins.split(",")))

    if shareInfo.tag in admins:
        db.query(database.ShareInfo).filter(database.ShareInfo.id == shareInfo.id).update({'status': shareInfo.status})
        db.commit()

        return JSONResponse(content=jsonable_encoder({"success": shareInfo.status}))
    else:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터의 관리자가 아닙니다."}))
    
@router.patch('/share/goods/quantity/{id}', tags=['app'])
def change_share_goods_quantity(shareInfo: ShareChangeInfo, db: Session = Depends(database.get_db)):
    stmt = select(database.ShareInfo).where(database.ShareInfo.id == shareInfo.id)
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()
    
    if row is None:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터가 없습니다."}))
    
    admins = list(map(int, row.admins.split(",")))

    if shareInfo.tag in admins:
        db.query(database.ShareInfo).filter(database.ShareInfo.id == shareInfo.id).update({'goods': shareInfo.goods})
        db.commit()

        return JSONResponse(content=jsonable_encoder({"success": shareInfo.goods}))
    else:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터의 관리자가 아닙니다."}))

@router.patch('/share/name/{id}', tags=['app'])
def change_share_name(shareInfo: ShareChangeInfo, db: Session = Depends(database.get_db)):
    stmt = select(database.ShareInfo).where(database.ShareInfo.id == shareInfo.id)
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()
    
    if row is None:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터가 없습니다."}))
    
    admins = list(map(int, row.admins.split(",")))

    if shareInfo.tag in admins:
        db.query(database.ShareInfo).filter(database.ShareInfo.id == shareInfo.id).update({'name': shareInfo.name})
        db.commit()

        return JSONResponse(content=jsonable_encoder({"success": shareInfo.name}))
    else:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터의 관리자가 아닙니다."}))

@router.patch('/share/point/{id}', tags=['app'])
def change_share_point_info(shareInfo: ShareChangeInfo, db: Session = Depends(database.get_db)):
    stmt = select(database.ShareInfo).where(database.ShareInfo.id == shareInfo.id)
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()
    
    if row is None:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터가 없습니다."}))
    
    admins = list(map(int, row.admins.split(",")))

    if shareInfo.tag in admins:
        db.query(database.ShareInfo).filter(database.ShareInfo.id == shareInfo.id).update({'jibun_address': shareInfo.jibun_address, 'doro_address': shareInfo.doro_address, 'point_lat': shareInfo.point_lat, 'point_lng': shareInfo.point_lng, 'point_name': shareInfo.point_name})
        db.commit()

        return JSONResponse(content=jsonable_encoder({"success": {'jibun_address': shareInfo.jibun_address, 'doro_address': shareInfo.doro_address, 'point_lat': shareInfo.point_lat, 'point_lng': shareInfo.point_lng, 'point_name': shareInfo.point_name}}))
    else:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터의 관리자가 아닙니다."}))
    
@router.patch('/share/admins/{id}', tags=['app'])
def change_share_admins_info(shareInfo: ShareChangeInfo, db: Session = Depends(database.get_db)):
    stmt = select(database.ShareInfo).where(database.ShareInfo.id == shareInfo.id)
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()
    
    if row is None:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터가 없습니다."}))
    
    admins = list(map(int, row.admins.split(",")))

    if shareInfo.tag in admins:
        db.query(database.ShareInfo).filter(database.ShareInfo.id == shareInfo.id).update({'admins': shareInfo.admins})
        db.commit()

        return JSONResponse(content=jsonable_encoder({"success": shareInfo.admins}))
    else:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터의 관리자가 아닙니다."}))

@router.patch('/share/goods/{id}', tags=['app'])
def change_share_goods(shareInfo: ShareChangeInfo, db: Session = Depends(database.get_db)):
    stmt = select(database.ShareInfo).where(database.ShareInfo.id == shareInfo.id)
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()
    
    if row is None:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터가 없습니다."}))
    
    admins = list(map(int, row.admins.split(",")))

    if shareInfo.tag in admins:
        db.query(database.ShareInfo).filter(database.ShareInfo.id == shareInfo.id).update({'goods': shareInfo.goods})
        db.commit()

        return JSONResponse(content=jsonable_encoder({"success": shareInfo.goods}))
    else:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터의 관리자가 아닙니다."}))

@router.post('/search/recent', tags=['app'])
def add_recent_search_keyword(keywordInfo: RecentKeyword, user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    # 기존에 겹치는 키워드 지우기
    stmt = delete(database.RecentSearchKeywords).where(
        database.RecentSearchKeywords.user_id == user.id,
        database.RecentSearchKeywords.keyword == keywordInfo.keyword
    )
    db.execute(stmt)
    db.commit()

    # 키워드 넣기
    recent_keyword_data = database.RecentSearchKeywords(user_id=user.id, keyword=keywordInfo.keyword, type=keywordInfo.type)
    db.add(recent_keyword_data)
    db.commit()

    return get_recent_search_keyword(user, db)

@router.delete('/search/recent/{id}', tags=['app'])
def delete_recent_search_keyword(id: int, user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    stmt = delete(database.RecentSearchKeywords).where(
        database.RecentSearchKeywords.user_id == user.id,
        database.RecentSearchKeywords.id == id
    )
    db.execute(stmt)
    db.commit()

    return JSONResponse(content=jsonable_encoder({"success": id}))

@router.delete('/search/recent_all', tags=['app'])
def delete_recent_search_keyword(user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    stmt = delete(database.RecentSearchKeywords).where(
        database.RecentSearchKeywords.user_id == user.id,
    )
    db.execute(stmt)
    db.commit()

    return JSONResponse(content=jsonable_encoder({"success": "삭제가 완료되었습니다."}))

@router.get('/search/recent', tags=['app'])
def get_recent_search_keyword(user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    stmt = select(database.RecentSearchKeywords).where(database.RecentSearchKeywords.user_id == user.id).order_by(database.RecentSearchKeywords.created_at.desc())
    matched = db.execute(stmt)
    rows = matched.mappings().all()

    response_data = [recent_keyword["RecentSearchKeywords"] for recent_keyword in rows]

    return JSONResponse(content=jsonable_encoder({"success": response_data}))

@router.post('/share/star', tags=['app'])
def add_share_star(info: ShareStarInfo, user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    if info.to_be:
        star_data = database.StarredShare(user_id=user.id, share_id=info.id)
        db.add(star_data)
        db.commit()
    else:
        stmt = delete(database.StarredShare).where(
            database.StarredShare.user_id == user.id,
            database.StarredShare.share_id == info.id,
        )
        db.execute(stmt)
        db.commit()
    
    return JSONResponse(content=jsonable_encoder({"success": {'status': info.to_be, 'id': info.id}}))

@router.post('/share/admin', tags=['app'])
def change_share_admin_info(info: ShareStarInfo, user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    stmt = select(database.Users).where(database.Users.id == user.id)
    matched = db.execute(stmt)
    user_row = matched.scalars().first()

    share_stmt = select(database.ShareInfo).where(database.ShareInfo.id == info.id)
    share_matched = db.execute(share_stmt)
    share_row = share_matched.scalars().first()
    
    if share_row is None:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터가 없습니다."}))
    
    admins = list(map(int, share_row.admins.split(",")))
    
    if user_row.tag in admins:
        new_admin_data = None

        if info.to_be is False and len(admins) == 1:
            return JSONResponse(content=jsonable_encoder({"error": "최소 한명의 관리자는 필요합니다."}))
        elif info.to_be is False:
            another_admins = [x - user_row.tag for x in admins]
            new_admin_data = ','.join(map(str, another_admins))
        elif info.to_be is True:
            admins.append(user_row.tag)
            new_admin_data = ','.join(map(str, admins))

        db.query(database.ShareInfo).filter(database.ShareInfo.id == info.id).update({'admins': new_admin_data})
        db.commit()

        return JSONResponse(content=jsonable_encoder({"success": {"id": info.id, "admins": new_admin_data}}))
    else:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터의 관리자가 아닙니다."}))

@router.get('/share/list/my', tags=['app'])
def get_my_share_list(user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    tag = get_token_using_id(user.id, db)
    tag = str(tag)

    stmt = (
        select(
            database.ShareInfo.id, 
            database.ShareInfo.name, 
            database.ShareInfo.admins,
            database.ShareInfo.contacts,
            database.ShareInfo.jibun_address,
            database.ShareInfo.doro_address,
            database.ShareInfo.point_lat,
            database.ShareInfo.point_lng,
            database.ShareInfo.point_name,
            database.ShareInfo.goods,
            database.ShareInfo.point,
            database.ShareInfo.status,
            case(
                (database.StarredShare.share_id == database.ShareInfo.id and database.StarredShare.user_id == User.id, True),
                else_=False
            ).label('starred')
        )
        .outerjoin(database.StarredShare, database.ShareInfo.id == database.StarredShare.share_id)
        .where(
            database.ShareInfo.admins.like(f"%{tag}%"),
            database.ShareInfo.is_deleted == False
        )
    )
    

    matched_row = db.execute(stmt)
    results = matched_row.mappings().all()

    if not results:
            return JSONResponse(content=jsonable_encoder({"error": "구역 내부에 값이 없습니다."}))

    response_data = []
    for result in results:
        row_dict = {
            "id": result.id,
            "name": result.name,
            "admins": result.admins,
            "contacts": result.contacts,
            "jibun_address": result.jibun_address,
            "doro_address": result.doro_address,
            "point_lat": result.point_lat,
            "point_lng": result.point_lng,
            "point_name": result.point_name,
            "goods": result.goods,
            "status": result.status,
            "starred": result.starred,
            "point": to_shape(result.point).__geo_interface__ if result.point else None
        }
        response_data.append(row_dict)

    return JSONResponse(content=jsonable_encoder({"success": response_data}))

@router.get('/share/list/starred', tags=['app'])
def get_starred_share_list(user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    tag = get_token_using_id(user.id, db)
    tag = str(tag)

    stmt = (
        select(
            database.ShareInfo.id, 
            database.ShareInfo.name, 
            database.ShareInfo.admins,
            database.ShareInfo.contacts,
            database.ShareInfo.jibun_address,
            database.ShareInfo.doro_address,
            database.ShareInfo.point_lat,
            database.ShareInfo.point_lng,
            database.ShareInfo.point_name,
            database.ShareInfo.goods,
            database.ShareInfo.point,
            database.ShareInfo.status,
            case(
                (database.StarredShare.share_id == database.ShareInfo.id and database.StarredShare.user_id == User.id, True),
                else_=False
            ).label('starred')
        )
        .outerjoin(database.StarredShare, database.ShareInfo.id == database.StarredShare.share_id)
        .where(
            database.StarredShare.share_id != None,
            database.StarredShare.user_id == user.id
        )
    )
    

    matched_row = db.execute(stmt)
    results = matched_row.mappings().all()

    if not results:
            return JSONResponse(content=jsonable_encoder({"error": "구역 내부에 값이 없습니다."}))

    response_data = []
    for result in results:
        row_dict = {
            "id": result.id,
            "name": result.name,
            "admins": result.admins,
            "contacts": result.contacts,
            "jibun_address": result.jibun_address,
            "doro_address": result.doro_address,
            "point_lat": result.point_lat,
            "point_lng": result.point_lng,
            "point_name": result.point_name,
            "goods": result.goods,
            "status": result.status,
            "starred": result.starred,
            "point": to_shape(result.point).__geo_interface__ if result.point else None
        }
        response_data.append(row_dict)

    return JSONResponse(content=jsonable_encoder({"success": response_data}))

@router.get('/admin/info/tag', tags=['app'])
def get_starred_share_list(tags = str, db: Session = Depends(database.get_db)):
    tags = [int(num) for num in tags.split(',')]

    stmt = select(
        database.Users.nickname, 
        database.Users.tag, 
    ).where(
        database.Users.tag.in_(tags)
    )

    matched_row = db.execute(stmt)
    results = matched_row.mappings().all()

    response_data = []
    for result in results:
        row_dict = {
            "nickname": result.nickname,
            "tag": result.tag
        }
        response_data.append(row_dict)

    
    return JSONResponse(content=jsonable_encoder({"success": response_data}))

@router.delete('/share/{id}', tags=['app'])
def delete_share_item(id: int, user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    tag = get_token_using_id(user.id, db)

    stmt = select(database.ShareInfo).where(database.ShareInfo.id == id)
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()
    
    if row is None:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터가 없습니다."}))
    
    admins = list(map(int, row.admins.split(",")))

    if tag in admins:
        db.query(database.ShareInfo).filter(database.ShareInfo.id == id).update({'is_deleted': True})
        db.commit()

        return JSONResponse(content=jsonable_encoder({"success": True}))
    else:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터의 관리자가 아닙니다."}))

@router.delete('/shares/{ids}', tags=['app'])
def delete_share_items(ids: str, db: Session = Depends(database.get_db)):
    ids = [int(num) for num in ids.split(',')]

    logger.info(f"Received request for item_id: {ids}")

    stmt = update(database.ShareInfo).where(database.ShareInfo.id.in_(ids)).values(is_deleted=True)
    db.execute(stmt)
    db.commit()

    return JSONResponse(content=jsonable_encoder({"success": ids}))

@router.post('/share/complexed', tags=['app'])
def update_share_item_complexed(data: UpdateComplexedShareInfoRequest, db: Session = Depends(database.get_db)):
    body = data.data
    result = []

    for info in body:
        result.append(info.id)

        if info.type == "DELETE":
            stmt = update(database.ShareInfo).where(database.ShareInfo.id == info.id).values(is_deleted=True)
            db.execute(stmt)
            db.commit()
        else:
            stmt = update(database.ShareInfo).where(database.ShareInfo.id == info.id).values(admins=info.admins)
            db.execute(stmt)
            db.commit()
    
    return JSONResponse(content=jsonable_encoder({"success": result}))

@router.delete('/user', tags=['app'])
def delete_user(user: User = Depends(verify_token), db: Session = Depends(database.get_db)):
    # 나눔에 관여된 어드민 전부 삭제
    stmt = select(database.Users).where(database.Users.id == user.id)
    matched = db.execute(stmt)
    user_row = matched.scalars().first()

    user_tag = user_row

    share_stmt = select(database.ShareInfo).where(database.ShareInfo.admins.like(f"%{user_tag}%"),)
    share_matched = db.execute(share_stmt)
    share_row = share_matched.mappings().all()

    share_infos = [row["ShareInfo"] for row in share_row]

    for info in share_infos:
        admins = [int(num) for num in info["admins"](',')]
        admins.remove(user_tag)

        stmt = update(database.ShareInfo).where(database.ShareInfo.id == info["id"]).values(admins=",".join(admins))
        db.execute(stmt)
        db.commit()


    # 소셜 회원인 경우 firebase/naver/kakao 컬럼 삭제
    if user_row.social_type == 1 or user_row.social_type == 3:
        auth.delete_user(user_row.social_uid)
    elif user_row.social_type == 5:
        token = get_secret('candleHelper/Auth/LoginWithNaver')
        requests.get(f"https://nid.naver.com/oauth2.0/token?grant_type=delete&client_id={token['id']}&client_secret={token['secret']}&access_token={user_row.naver_client_id}")
    elif user_row.social_type == 4:
        token = get_secret("nanumsa/key/kakao/admin")
        requests.post(f"https://kapi.kakao.com/v1/user/unlink", headers={'Authorization': f"KakaoAK {token["token"]}", "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}, data={"target_id_type": "user_id", "target_id": f"{str(user_row.kakao_user_id)}"})

    # 유저 컬럼에서 is_deleted = true로 변경
    stmt = update(database.Users).where(database.Users.id == user.id).values(is_deleted=True, edited_at=seoul_time)
    db.execute(stmt)
    db.commit()

    # 로그아웃
    logout_target = db.query(database.LoginToken).filter(database.LoginToken.user_id == user.id).first()
    db.delete(logout_target)
    db.commit()

    return JSONResponse(content=jsonable_encoder({"success": "회원 탈퇴가 완료되었습니다."}))