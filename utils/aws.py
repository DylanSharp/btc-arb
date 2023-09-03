import json

import boto3

ssm = boto3.client('ssm', region_name='us-east-1')


def get_ssm_param(name):
	return ssm.get_parameter(Name=name, WithDecryption=True).get('Parameter').get('Value')


def get_ssm_json_param(name):
	return json.loads(get_ssm_param(name))
