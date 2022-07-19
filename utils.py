import markdown
from typing import Union, List
from saral_utils.utils.env import get_env_var
from saral_utils.extractor.dynamo import DynamoDB

def generate_html(txts: List[str]) -> str:
    """Given a list of strings, concatenates them and convert markdown into html strings

    Args:
        txts (List[str]): List of markdown strings

    Returns:
        str: A single string in html format
    """    
    email_str = "\n\n".join(txts)
    return markdown.markdown(email_str)

def get_total_registered_users():
    env = get_env_var("MY_ENV")
    region = get_env_var("MY_REGION")

    reg_db = DynamoDB(table=f'registered-users-{env}', env=env, region=region)
    unreg_db = DynamoDB(table=f'deregistered-users-{env}', env=env, region=region)

    registered_users = len(reg_db.ddb.scan(TableName=reg_db.table)['Items'])
    unregistered_users = len(unreg_db.ddb.scan(TableName=unreg_db.table)['Items'])
    total_registered_users = registered_users - unregistered_users
    return total_registered_users

def send_mail(ses_client, to: Union[str, List], frm, body, subject, body_type: str = 'text', cc: Union[str, List, None] = None):
    CHARSET='UTF-8'
    destination = {
        'ToAddresses': to if isinstance(to, list) else [to]
    }
    if cc is not None:
        destination['CcAddresses'] = cc if isinstance(cc, list) else [cc]

    if body_type == 'text':
        message = {'Body': {'Text': {'Data': body, 'Charset': CHARSET}},
        'Subject': {'Charset': CHARSET, 'Data': subject}}
    elif body_type == 'html':
        message = {'Body': {'Html': {'Charset': CHARSET, 'Data': body}},
        'Subject': {'Charset': CHARSET, 'Data': subject}}
    else:
        raise ValueError(f'Invalid body type, can only be "html" or "text"')

    resp = ses_client.send_email(
        Destination = destination, 
        Message = message,
        Source = frm
    )

    return resp