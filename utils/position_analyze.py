import json

with open('user_data.json','r',encoding='utf-8') as file:
    user = json.load(file)

print(user["sleep_time"])

#后续更改为读取位置