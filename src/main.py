from fastapi import FastAPI, Depends, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select



# 라우터들
from src.controllers.login import login_controller
from src.controllers.application import applicaction_controller
from src.controllers.verify import verify_controller
from src.controllers.lookup import lookup_controller

app = FastAPI()
app.include_router(login_controller.router)
app.include_router(verify_controller.router)
app.include_router(applicaction_controller.router)
app.include_router(lookup_controller.router)

origins = [
    "http://localhost:5173",
    "ws://localhost:3030",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


