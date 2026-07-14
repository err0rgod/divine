import os, json
chat_dir = 'D:/divine/context/chats'
chats = []
for filename in os.listdir(chat_dir):
    if filename.endswith('.json'):
        with open(os.path.join(chat_dir, filename), 'r', encoding='utf-8') as f:
            chats.append(json.load(f))

chats.sort(key=lambda x: x.get('updatedAt', 0))
for c in chats:
    print('\n--- Chat ID: ' + str(c.get('id')) + ' | Title: ' + str(c.get('title')) + ' ---')
    history = c.get('history', [])
    for msg in history:
        role = msg.get('role')
        content = msg.get('content', '')
        if role == 'user':
            print('USER: ' + (content[:150].replace('\n', ' ') + '...' if len(content)>150 else content.replace('\n', ' ')))
        elif role == 'assistant':
            meta = msg.get('meta', '')
            print('AI (' + str(meta) + '): ' + (content[:150].replace('\n', ' ') + '...' if len(content)>150 else content.replace('\n', ' ')))
