import boto3
from botocore.exceptions import ClientError

import os

import json

aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

def get_secret(secret_name:str):
    region_name = "ap-northeast-2"

    # Create a Secrets Manager client
    session = boto3.session.Session()

    client = None

    if aws_access_key_id and aws_secret_access_key:
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name,
            aws_access_key_id=aws_access_key_id, 
            aws_secret_access_key=aws_secret_access_key
        )
    else: 
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name,
        )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = get_secret_value_response['SecretString']

    return json.loads(secret)