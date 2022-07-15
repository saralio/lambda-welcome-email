from datetime import datetime
from utils import generate_html, generate_links, get_total_registered_users, send_mail
from saral_utils.utils.env import get_env_var
import urllib
import boto3

def emailer(event, context):

    env = get_env_var("MY_ENV")
    region = get_env_var("MY_REGION")

    records = event['Records']
    #TODO: [SAR-116] parse emailSendTime and emailSendTimeZone properly
    for record in records:
        event_name = record['eventName']
        value = record['dynamodb']['NewImage']
        email_id = value['emailId']['S']
        email_send_time_zone = value['emailSendTimeZone']['S']
        email_send_time = value['emailSendTime']['S']

        # put event bridge rule
        rule_name = f'RuleFor_{email_id.replace("@", "_").replace(".", "_")}'
        print(f'putting rule for {email_id} with rule name: {rule_name} at time {email_send_time}')
        time = datetime.strptime(email_send_time, '%H:%M')
        cron_expr = f'{time.minute} {time.hour} * * ? *'
        print(f'cron expression: {cron_expr}')

        # create rule
        rule_client = boto3.client('events')
        response = rule_client.put_rule(
            Name=rule_name,
            ScheduleExpression=f'cron({cron_expr})',
            State='ENABLED',
            Description=f'rule for user with email id: {email_id}'
        )

        # create target
        response2 = rule_client.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    'Id': f'SendEmail_{rule_name}',
                    'Arn': f'arn:aws:lambda:{region}:240478177988:function:lambda-daily-emails-{env}-emailer',
                    'Input': f'{{"emailId": "{email_id}"}}'
                }
            ]
        )

        print('event bridge rule created and target created')

        # sending emails
        ses_client = boto3.client('ses')
        links = generate_links(email_id=email_id)
        tweet = f'Check out {links["saral_website_link"]}. You can subscribe to receive a daily question on #RStats programming directly in your inbox'
        sharing_link = f'{links["base_sharing_link"]}{urllib.parse.quote_plus(tweet)}' #type:ignore
        footer =  f"*Please consider supporting us by [sharing]({sharing_link}) or by making a [donation]({links['donation_link']}). Your contribution, helps us to keep the services afloat. To unsubscribe click [here]({links['unsubscribe_link']}).*"

        # email text for new user
        welcome_body = [ 
            f"# Welcome to [#RStats Question a Day]({links['twitter_account_link']})",
            "We are glad to be a part of your journey of learning R.",
            f"R is a wonderful programming language with even more wonderful community with wonderful people. To join the conversation, simply head on to twitter and follow the hashtag [#RStats]({links['twitter_hashtag_link']}).",
            f"As a part of this email service, you will receive a question, daily at {email_send_time}. If you wish to change the time, you can resubscribe [here]({links['saral_website_link']})",
            f"Thanks,  \n[Mohit]({links['personal_account_link']})",
            footer
        ]

        # email text for confirming updated time
        time_change_body = [
            f"### Time updated successfully!",
            f"Now, you will receive a new question on R programming language, daily at {email_send_time}",
            f"Thanks,  \n[Saral]({links['twitter_account_link']})",
            footer
        ]

        if event_name == 'INSERT':
            print(f'event name is {event_name}, hence sending update emails')

            # send welcome email to user
            welcome_html = generate_html(welcome_body)
            response = send_mail(
                ses_client=ses_client, 
                to=email_id, 
                frm="Saral<welcome@saral.club>", 
                body=welcome_html, 
                body_type='html', 
                subject='Welcome to #RStats Question A Day'
            )
            print('Welcome email send to user')

            total_registered_users = get_total_registered_users()
            # drop email to saral with info
            response = send_mail(
                ses_client=ses_client, 
                to="info@saral.club", frm="welcome@saral.club", 
                body_type='text',
                body=f"New Registration. Total registered users: {total_registered_users}",
                subject="New Registration",
                cc="mohitlakshya@gmail.com"
            )

            print('info mail send to saral')
        else:
            print(f'event name is {event_name}, skipping sending emails')
            
            # send confirmation mail of time update
            time_change_html = generate_html(time_change_body)
            response = send_mail(
                ses_client=ses_client,
                to=email_id, 
                frm="Saral<support@saral.club>",
                body=time_change_html,
                subject="Time Changed",
                body_type="html"
            )
            
    return {
        'statusCode': 200
    }
