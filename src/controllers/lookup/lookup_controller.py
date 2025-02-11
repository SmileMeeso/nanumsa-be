from fastapi import APIRouter, Depends, Response, Header, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from src.database import database

from sqlalchemy import select, func, case
from sqlalchemy.orm import Session

from pydantic import BaseModel

from geoalchemy2.shape import to_shape

import requests, json
from typing import Optional, List

from collections import defaultdict

from korean_name_generator import namer

from src.utils import generate_random_string, str_to_bool

from datetime import datetime
from zoneinfo import ZoneInfo

from passlib.hash import sha256_crypt
from src.aws.secretManager import get_secret

import logging

router = APIRouter()

seoul_time = datetime.now(ZoneInfo('Asia/Seoul'))

class MapPoint(BaseModel):
    lat: float
    lng: float

class MapBoundsInfo(BaseModel):
    southwest: MapPoint
    northwest: MapPoint
    northeast: MapPoint
    southeast: MapPoint

class User(BaseModel):
    id: int

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

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_user_id(auth_token: str = Header(None), db: Session = Depends(database.get_db)):
    stmt = select(database.LoginToken).where(database.LoginToken.token == auth_token)
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()
    
    if row is None:
        return None
    
    return User(id = row.user_id)

@router.post('/share/list', tags=['share'])
def get_share_list_with_bounds(bounds: MapBoundsInfo, db: Session = Depends(database.get_db), auth_token: str = Header(None)):
    User = get_user_id(auth_token, db)

    stmt = None

    if User is None:
        stmt = select(database.ShareInfo.id, 
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
                        database.ShareInfo.status
                    ).where(
                        database.ShareInfo.point.ST_Intersects(func.ST_MakeEnvelope(
                        bounds.southwest.lng, bounds.southwest.lat, 
                        bounds.northeast.lng, bounds.northeast.lat, 
                        4326)), database.ShareInfo.is_deleted == False
                    )
        matched_rows = db.execute(stmt)
        results = matched_rows.mappings().all()

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
                "point": to_shape(result.point).__geo_interface__ if result.point else None
            }
            response_data.append(row_dict)
        return JSONResponse(content=jsonable_encoder({"success": response_data}))
    else: 
        stmt = select(
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
                ).outerjoin(database.StarredShare, database.ShareInfo.id == database.StarredShare.share_id).where(
                    database.ShareInfo.point.ST_Intersects(func.ST_MakeEnvelope(
                    bounds.southwest.lng, bounds.southwest.lat, 
                    bounds.northeast.lng, bounds.northeast.lat, 
                4326)), database.ShareInfo.is_deleted == False)
        
        matched_rows = db.execute(stmt)
        results = matched_rows.mappings().all()

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

@router.get('/share/item/{id}', tags=['share']) 
def get_share_item_by_id(id: int, db: Session = Depends(database.get_db), auth_token: str = Header(None)):
    User = get_user_id(auth_token, db)
    
    stmt = None

    if User is None:
        # 좋아요 정보 가져오지 못함
        stmt = select(database.ShareInfo.id, 
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
                    database.ShareInfo.status
                    ).where(database.ShareInfo.id == id, database.ShareInfo.is_deleted == False)
    else:
        # 좋아요 정보 가져옴
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
            .where(database.ShareInfo.id == id, database.ShareInfo.is_deleted == False)
        )
    

    matched_row = db.execute(stmt)
    result = matched_row.fetchone()

    if result is None:
        return JSONResponse(content=jsonable_encoder({"error": "데이터가 없습니다."}))
    
    column_names = [
        "id", "name", "admins", "contacts", "jibun_address", "doro_address",
        "point_lat", "point_lng", "point_name", "goods", "point", "status", "starred"
    ]

    row_dict = dict(zip(column_names, result))

    row_dict["point"] = to_shape(row_dict["point"]).__geo_interface__

    return JSONResponse(content=jsonable_encoder({"success": row_dict}))

@router.patch('/share/contacts/{id}', tags=['app'])
def change_share_contacts(shareInfo: ShareChangeInfo, db: Session = Depends(database.get_db)):
    stmt = select(database.ShareInfo).where(database.ShareInfo.id == shareInfo.id)
    matchedRow = db.execute(stmt)
    row = matchedRow.scalars().first()
    
    if row is None:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터가 없습니다."}))
    
    admins = list(map(int, row.admins.split(",")))

    if shareInfo.tag in admins:
        db.query(database.ShareInfo).filter(database.ShareInfo.id == shareInfo.id).update({'contacts': shareInfo.contacts})
        db.commit()

        return JSONResponse(content=jsonable_encoder({"success": shareInfo.contacts}))
    else:
        return JSONResponse(content=jsonable_encoder({"error": "해당 나눔 데이터의 관리자가 아닙니다."}))

@router.get('/search/keywords/{keyword}', tags=['app'])
def get_like_search_keywords_with_keyword(
    keyword: str, 
    map_only: Optional[str] = None,
    southwest_lng: Optional[float] = None,
    southwest_lat: Optional[float] = None,
    northeast_lng: Optional[float] = None,
    northeast_lat: Optional[float] = None, 
    db: Session = Depends(database.get_db)
):
    is_map_only = str_to_bool.str_to_bool(map_only)
    
    results = None

    if is_map_only is False:
        results = db.query(database.ShareInfo).with_entities(database.ShareInfo.id, database.ShareInfo.name, database.ShareInfo.doro_address, database.ShareInfo.jibun_address,
               database.ShareInfo.point_lat, database.ShareInfo.point_lng).filter(database.ShareInfo.name.like(f"%{keyword}%"))
    else:
        results = db.query(database.ShareInfo).with_entities(database.ShareInfo.id, database.ShareInfo.name, database.ShareInfo.doro_address, database.ShareInfo.jibun_address,
               database.ShareInfo.point_lat, database.ShareInfo.point_lng).filter(database.ShareInfo.name.like(f"%{keyword}%"), database.ShareInfo.point.ST_Intersects(func.ST_MakeEnvelope(southwest_lng, southwest_lat, northeast_lng, northeast_lat, 4326)))

    share_infos = results.all()

    # 결과를 처리할 객체 초기화
    data = []
    point_dict = defaultdict(list)  # (lat, lng) 키에 대해 주소와 이름 리스트를 저장

    for row in share_infos:
        id, name, doro_address, jibun_address, point_lat, point_lng = row
        
        # (lat, lng) 튜플에 따라 저장
        point_dict[(point_lat, point_lng)].append((name, doro_address, jibun_address, id))
    
    # 딕셔너리 순회
    for point, values in point_dict.items():
        if len(values) > 1:
            # 겹치는 경우
            count = len(values)
            names, doro_addresses, jibun_addresses, ids = zip(*values)  # 언팩킹
            # 예제에 따라 우선 첫번째(중복된) 정보를 사용하여 배열에 추가.
            data.append({
                "name": names[0], 
                "doro_address": doro_addresses[0], 
                "jibun_address": jibun_addresses[0],
                "point_lat": point[0],
                "point_lng": point[1],
                "count": count,
            })
        else:
            # 겹치지 않는 경우
            single_value = values[0]
            name, doro_address, jibun_address, id = single_value
            data.append({"id": id, "name": name})

    return JSONResponse(content=jsonable_encoder({"success": data}))

@router.get('/search/results/{keyword}', tags=['app'])
def get_search_results(
    keyword: str, 
    map_only: Optional[str] = None,
    southwest_lng: Optional[float] = None,
    southwest_lat: Optional[float] = None,
    northeast_lng: Optional[float] = None,
    northeast_lat: Optional[float] = None, 
    db: Session = Depends(database.get_db),
    auth_token: str = Header(None)
):
    is_map_only = str_to_bool.str_to_bool(map_only)
    results = None
    User = get_user_id(auth_token, db)
    stmt = None

    logger.info(f"Received request for item_id: {keyword} with query")

    if User is None and is_map_only is True:
        stmt = select(database.ShareInfo.id, 
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
                    database.ShareInfo.status
                    ).where(
                    database.ShareInfo.point.ST_Intersects(func.ST_MakeEnvelope(
                    southwest_lng, southwest_lat, 
                    northeast_lng, northeast_lat, 
                    4326), database.ShareInfo.is_deleted == False, database.ShareInfo.name.like(f"%{keyword}%"))
            )
        matched_rows = db.execute(stmt)
        results = matched_rows.mappings().all()

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
                "point": to_shape(result.point).__geo_interface__ if result.point else None
            }
            response_data.append(row_dict)

        return JSONResponse(content=jsonable_encoder({"success": response_data}))
    elif User is not None and is_map_only is True: 
        stmt = select(
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
                ).outerjoin(database.StarredShare, database.ShareInfo.id == database.StarredShare.share_id).where(
                    database.ShareInfo.point.ST_Intersects(func.ST_MakeEnvelope(
                    southwest_lng, southwest_lat, 
                    northeast_lng, northeast_lat, 
                4326)), database.ShareInfo.is_deleted == False, database.ShareInfo.name.like(f"%{keyword}%"))
        
        matched_rows = db.execute(stmt)
        results = matched_rows.mappings().all()

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
    elif User is None and is_map_only is False:
        stmt = select(database.ShareInfo.id, 
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
                    database.ShareInfo.status
                    ).where(database.ShareInfo.is_deleted == False, database.ShareInfo.name.like(f"%{keyword}%"))
        matched_rows = db.execute(stmt)
        results = matched_rows.mappings().all()

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
                "point": to_shape(result.point).__geo_interface__ if result.point else None
            }
            response_data.append(row_dict)

        return JSONResponse(content=jsonable_encoder({"success": response_data}))
    else:
        stmt = select(
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
                ).outerjoin(database.StarredShare, database.ShareInfo.id == database.StarredShare.share_id).where(
                    database.ShareInfo.is_deleted == False, database.ShareInfo.name.like(f"%{keyword}%"))
        

        matched_rows = db.execute(stmt)
        results = matched_rows.mappings().all()

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