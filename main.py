import os
import time
from datetime import datetime
from flask import Flask, render_template_string
import vk_api

app = Flask(__name__)

# Получаем данные из переменных окружения (или подставляем свои для локального теста)
TOKEN = os.environ.get('VK_TOKEN', 'ВАШ_ТОКЕН_ЗДЕСЬ')
GROUP_ID = int(os.environ.get('VK_GROUP_ID', 0)) # ID группы БЕЗ минуса

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Архив ролевых постов</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #f8fafc;
            --accent-color: #38bdf8;
            --secondary-text: #94a3b8;
            --border-color: #334155;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        .sidebar {
            width: 300px;
            background-color: #090d16;
            border-right: 1px solid var(--border-color);
            padding: 20px;
            overflow-y: auto;
            box-sizing: border-box;
        }

        .sidebar h2 {
            font-size: 1.1rem;
            color: var(--accent-color);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 20px;
            margin-bottom: 10px;
        }

        .nav-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .nav-item {
            padding: 8px 12px;
            margin-bottom: 4px;
            border-radius: 6px;
            cursor: pointer;
            color: var(--secondary-text);
            transition: all 0.2s;
        }

        .nav-item:hover, .nav-item.active {
            background-color: var(--card-bg);
            color: var(--text-color);
        }

        .content {
            flex: 1;
            padding: 30px;
            overflow-y: auto;
        }

        .post-card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .post-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
            margin-bottom: 15px;
            font-size: 0.9rem;
            color: var(--secondary-text);
        }

        .post-author {
            color: var(--accent-color);
            font-weight: bold;
            text-decoration: none;
        }

        .post-topic {
            background: #334155;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
        }

        .post-text {
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-word;
        }
    </style>
</head>
<body>

    <div class="sidebar">
        <h1>📜 Архив РП</h1>
        
        <h2>Сюжеты / Теги</h2>
        <ul class="nav-list">
            <li class="nav-item active" onclick="filterPosts('all')">Все посты ({{ total_count }})</li>
            {% for tag, posts in stories.items() %}
            <li class="nav-item" onclick="filterPosts('tag-{{ loop.index }}')">
                {{ tag }} ({{ posts|length }})
            </li>
            {% endfor %}
        </ul>

        <h2>Игроки (ID)</h2>
        <ul class="nav-list">
            {% for author, posts in players.items() %}
            <li class="nav-item" onclick="filterPosts('author-{{ author }}')">
                ID {{ author }} ({{ posts|length }})
            </li>
            {% endfor %}
        </ul>
    </div>

    <div class="content">
        <div id="posts-container">
            {% if total_count == 0 %}
                <p>Постов с хештегами не найдено или группа недоступна. Проверьте токен и ID группы.</p>
            {% endif %}
            
            {% for post in all_posts %}
            <div class="post-card post-item tag-{{ post.tag_index }} author-{{ post.author_id }}">
                <div class="post-header">
                    <div>
                        Автор: <a class="post-author" href="https://vk.com/id{{ post.author_id }}" target="_blank">id{{ post.author_id }}</a>
                    </div>
                    <div>
                        <span class="post-topic">{{ post.topic_title }}</span>
                        <span>{{ post.date }}</span>
                    </div>
                </div>
                <div class="post-text">{{ post.text }}</div>
            </div>
            {% endfor %}
        </div>
    </div>

    <script>
        function filterPosts(filterClass) {
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            event.target.classList.add('active');

            const posts = document.querySelectorAll('.post-card');
            posts.forEach(post => {
                if (filterClass === 'all' || post.classList.contains(filterClass)) {
                    post.style.display = 'block';
                } else {
                    post.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""

def fetch_roleplay_data():
    if not TOKEN or not GROUP_ID or TOKEN == 'ВАШ_ТОКЕН_ЗДЕСЬ':
        return {}, {}, [], 0

    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()

    try:
        topics = vk.board.getTopics(group_id=GROUP_ID, preview=0)['items']
    except Exception as e:
        print(f"Ошибка доступа к группе: {e}")
        return {}, {}, [], 0
    
    stories = {}   
    players = {}   
    all_posts = [] 

    tag_map = {}   
    tag_counter = 1

    for topic in topics:
        topic_id = topic['id']
        topic_title = topic['title']
        
        offset = 0
        count = 100
        
        while True:
            try:
                res = vk.board.getComments(group_id=GROUP_ID, topic_id=topic_id, offset=offset, count=count)
                items = res['items']
                if not items:
                    break
                
                for comment in items:
                    text = comment.get('text', '')
                    author_id = comment['from_id']
                    date_str = datetime.fromtimestamp(comment['date']).strftime('%d.%m.%Y %H:%M')
                    
                    # Ищем теги вида #сюжет
                    tags = [word.lower() for word in text.split() if word.startswith('#')]
                    
                    if not tags:
                        tags = ['#без_тега']

                    for tag in tags:
                        if tag not in tag_map:
                            tag_map[tag] = tag_counter
                            tag_counter += 1
                            
                        tag_idx = tag_map[tag]

                        post_data = {
                            'topic_title': topic_title,
                            'author_id': author_id,
                            'date': date_str,
                            'text': text,
                            'tag_index': tag_idx
                        }

                        if tag not in stories:
                            stories[tag] = []
                        stories[tag].append(post_data)

                        if author_id not in players:
                            players[author_id] = []
                        players[author_id].append(post_data)

                        all_posts.append(post_data)

                offset += count
                time.sleep(0.35)
            except Exception as e:
                print(f"Ошибка в теме {topic_id}: {e}")
                break

    return stories, players, all_posts, len(all_posts)

@app.route('/')
def home():
    stories, players, all_posts, total_count = fetch_roleplay_data()
    return render_template_string(
        HTML_TEMPLATE, 
        stories=stories, 
        players=players, 
        all_posts=all_posts, 
        total_count=total_count
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
