import secrets
import string
import random

# 랜덤 문자열을 만드는 함수
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def generate_secure_string(length: int) -> str:
    """지정한 길이만큼의 안전한 문자열을 생성합니다."""
    
    # 사용할 문자 집합 (대문자, 소문자, 숫자, 특수문자)
    characters = string.ascii_letters + string.digits + string.punctuation
    # 보안성이 높은 임의의 문자열 생성
    secure_string = ''.join(secrets.choice(characters) for _ in range(length))
    
    return secure_string