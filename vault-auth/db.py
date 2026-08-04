import boto3

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
users_table = dynamodb.Table("vault-users")
