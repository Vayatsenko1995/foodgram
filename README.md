# Фудграм

**Фудграм** — сайт для обмена рецептами понравившихся блюд.

## Описание

«Фудграм» — это платформа, на которой пользователи могут:

- Публиковать свои рецепты.
- Добавлять чужие рецепты в избранное.
- Подписываться на публикации других авторов.
- Пользоваться сервисом «Список покупок», который позволяет создавать и скачивать список необходимых продуктов в формате .pdf.

## CI/CD с помощью GitHub Actions

При нажатии на кнопку деплоя в GitHub Actions происходит:

- Проверка кода бэкенда на соответствие PEP8.
- Запуск тестов для фронтенда и бэкенда.
- Сборка образов Docker и отправка их на Docker Hub.
- Обновление образов на сервере и перезапуск приложения с помощью Docker Compose.
- Выполнение миграций и сборка статики, перенос её в volume.
- Уведомление в Telegram об успешном завершении деплоя.

## Установка на удалённый сервер

### 1. Клонирование репозитория

bash
git clone github.com/Vayatsenko1995/foodgram


### 2. Создание файла переменных окружения

Создайте файл `.env` и заполните его необходимыми данными.

### 3. Создание и загрузка Docker образов

Создайте образы локально:

bash
docker build -t <yourusername>/foodgramfront .
docker build -t <yourusername>/foodgramback .
docker build -t <yourusername>/foodgramgateway .


Загрузите образы на DockerHub:

bash
docker push yourusername/foodgramfrontend
docker push yourusername/foodgrambackend
docker push yourusername/foodgramgateway


### 4. Деплой на сервер

- Подключитесь к серверу:

bash
ssh -i путьдофайласSSHключом/названиефайлазакрытогоSSH-ключа login@ip


- Установите Docker и Docker Compose:

bash
sudo apt install curl
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo apt-get install docker-compose-plugin


- Скопируйте на сервер файлы `docker-compose.yml`:

bash
scp -i PATHTOSSHKEY/SSHKEYNAME docker-compose.yml YOURUSERNAME@SERVERIPADDRESS:/home/YOUR_USERNAME/foodgram/docker-compose.yml


### 5. Настройка GitHub Actions

В разделе **Secrets > Actions** создайте переменные окружения:

- SECRET_KEY
- DOCKER_USERNAME
- DOCKER_PASSWORD
- TELEGRAM_TOKEN
- и другие, необходимые для работы

### 6. Запуск контейнеров

На сервере выполните:

bash
sudo docker compose up -d


### 7. Дальнейшие команды:

- Выполнить миграции:

bash
sudo docker-compose exec backend python manage.py migrate


- Собрать и перенести статику:

bash
sudo docker-compose exec backend python manage.py collectstatic
sudo docker compose exec backend cp -r /app/collectedstatic/. /backendstatic/static/


- Загрузить данные:

bash
sudo docker-compose exec backend python manage.py load_data


- Создать суперпользователя:

bash
sudo docker compose exec backend python manage.py createsuperuser


### 8. Настройка Nginx

Откройте конфигурационный файл:

bash
sudo nano /etc/nginx/sites-enabled/default


Измените настройки `location`:

text
location / {
    proxysetheader Host $httphost;
    proxypass http://127.0.0.1:8000;
}


Перезапустите Nginx:

bash
sudo service nginx reload


```

Этот формат README.md будет легко читаемым и структурированным, что облегчит использование и настройку проекта другими пользователями.
