import boto3
from botocore.config import Config
from db import users_table

s3 = boto3.client('s3', config=Config(signature_version='s3v4'))

PHOTO_URL = "https://vault-profile-images.s3.us-east-1.amazonaws.com/profile-photos"

def get_upload_url(user_addr, file_type):
    url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': 'vault-profile-images',
            'Key': f'profile-photos/{user_addr}.{file_type}',
            'ContentType': f'image/{file_type}'
        },
        ExpiresIn=300
    )
    return url

def update_db(username, user_addr, file_type):
    url = f"{PHOTO_URL}/{user_addr}.{file_type}"

    users_table.update_item(
        Key={"username":username},
        UpdateExpression='SET profile_photo = :url', 
        ExpressionAttributeValues={':url': url}
    )

    return url


def get_photo(username):
    res = users_table.get_item(Key={"username":username})

    if "Item" in res:
        item = res["Item"]
        if "profile_photo" in item:
            return res["Item"]["profile_photo"]
        else:
            return ""
    return ""
    
    
    