import datetime

TEMPLATE = f"""
Here are the additional contexts:
Current local time: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Current timezone: {datetime.datetime.now().astimezone().tzinfo}
{{{{additional_context}}}}
"""