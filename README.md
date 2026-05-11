# **🤖 Telegram VPN Bot**

Проект представляет собой основу для Telegram-бота, который проверяет подписку на канал, принимает оплату через YooKassa и затем отдает готовую VPN subscription-ссылку для Xray-клиентов.

---

## **🚀 Что умеет бот**

* **Проверка доступа**: Доступ выдаётся только после подтверждения подписки на канал.  
* **Платный доступ**: Бот выдает VPN после оплаты и умеет продлевать доступ на фиксированный срок.  
* **YooKassa**: Поддерживается создание платежа, проверка статуса и webhook-активация доступа.  
* **Выдача готового доступа**: Бот отправляет пользователю subscription-ссылку и помогает выбрать способ подключения по типу устройства.  
* **Быстрый импорт в приложение**: Бот умеет открыть отдельную страницу для импорта в `v2RayTun` и дать запасной ручной вариант.  
* **Контроль доступа**: Бот сохраняет пользователей в локальную базу, может навсегда блокировать тех, кто получил доступ и потом отписался, и поддерживает админ-команды для просмотра банов.  
* **Поддержка локального и продакшн-окружения**: Гибкая настройка через файл окружения.  
* **Расширяемая бизнес-логика**: Проект готов к дальнейшей доработке и масштабированию под новые задачи.

---

## **📦 Стек технологий**

* **Python**  
* **Docker / Docker Compose**  
* **Telegram Bot API**  
* **Xray / v2RayTun**  
* **Certbot / Let's Encrypt**

---

## **🔧 Установка и запуск**

### **1\. Клонирование репозитория**

Клонируйте репозиторий и перейдите в его директорию:

```bash
git clone https://github.com/yarodya1/telegram-vpn-bot.git  
cd telegram-vpn-bot
```

### **2\. Создание и настройка файлов окружения**

Скопируйте шаблоны файлов с настройками:

```bash
cat env.dist > .env
```

**Основные параметры файла:**

* `BOT_TOKEN='TOKEN'` – Токен Telegram-бота. Его можно получить через @BotFather.  
* `DOMAIN='localhost'` – Домен; для локального тестирования используйте `localhost`, а для продакшена – свой домен.  
* `ADMIN=222222` – Telegram ID администратора.  
* `CHANNEL_ID='-1001234567890'` – ID канала для проверки подписки.  
* `CHANNEL_URL='https://t.me/your_channel'` – Ссылка на канал.  
* `VPN_PAID_DURATION_DAYS=30` и `VPN_PAID_TRAFFIC_GB=50` – Параметры оплаченного доступа.  
* `VPN_PRICE_RUB=200` – Стоимость продления.  
* `YOOKASSA_ENABLED=False` – Включает оплату через YooKassa.  
* `YOOKASSA_SHOP_ID='1355330'` – ID магазина YooKassa.  
* `YOOKASSA_SECRET_KEY=''` – Секретный ключ YooKassa для API.  
* `BOT_IP=127.0.0.1` – Внешний IP сервера, который используется для страницы быстрого импорта в `v2RayTun`.  
* `DATABASE_PATH='bot.db'` – Путь до SQLite-базы пользователей и вечных банов.  
* `XUI_ENABLED=False` – Включает персональную выдачу через x-ui.  
* `XUI_BASE_URL='https://your-domain.com:2053/your-panel-path'` – URL панели x-ui.  
* `XUI_USERNAME='admin'` и `XUI_PASSWORD='password'` – Данные входа в x-ui.  
* `XUI_INBOUND_ID=1` – ID inbound, в который бот будет создавать клиентов.  
* `XUI_SUB_BASE_URL='https://your-domain.com:2096/sub'` – Базовый subscription URL для основного x-ui сервера.  
* `XUI_CLIENT_PREFIX='tg'` – Префикс email клиента в x-ui.  
* `XUI_VERIFY_SSL=True` – Проверять SSL при работе с x-ui.  
* `XUI_AGGREGATOR_BASE_URL='http://your-server-ip:8080'` – Внешний URL бота, через который можно отдать одну общую subscription-ссылку для нескольких x-ui серверов.  
* `XUI_PRIMARY_LABEL=''` – Человекочитаемое имя для основного узла, например `🇳🇱 Нидерланды`. Если указано, бот заменит исходный label основной подписки на него.  
* `XUI_PRIMARY_HOST=''` – Если указано, бот заменит адрес основного узла в subscription, например на `nl.filserver.website`, чтобы в клиенте не светился IP.  
* `XUI_EXTRA_STATIC_SUB_URLS='[]'` – JSON-массив дополнительных готовых subscription URL, которые нужно просто подмешать в одну общую ссылку без логина в чужую x-ui панель. Можно передавать как строки или как объекты с `url` и `label`, чтобы переименовать узел, например: `[{"url":"https://de.example.com:2096/sub/abcd","label":"Германия"}]`.  
* `XUI_EXTRA_NODES='[]'` – JSON-массив дополнительных x-ui узлов. Пример: `[{"base_url":"https://de.example.com:2053/panel","username":"admin","password":"pass","inbound_id":1,"sub_base_url":"https://de.example.com:2096/sub","verify_ssl":true}]`  
* `VPN_ACCESS_TEXT='https://your-domain.com:2096/sub/your_subscription_token'` – Subscription-ссылка, ключ или текст, которые бот отправит пользователю после проверки подписки.  
* `CERT_FULLCHAIN_PATH=''` и `CERT_KEY_PATH=''` – Пути к сертификату и ключу соответственно.

### **3. Выпуск сертификатов**

**Локальное окружение (самоподписанные сертификаты):**

Для локального тестирования можно использовать самоподписанные сертификаты:

```bash
openssl req -x509 -newkey rsa:2048 -nodes -keyout privkey.pem -out fullchain.pem -days 365 -subj "/CN=localhost"
```

После генерации сертификатов пропишите полный путь к файлам `fullchain.pem` и `privkey.pem` в файле `.env`.

**Продакшн окружение (Let's Encrypt):**

Для получения сертификатов на продакшене выполните следующие команды (пример для Alpine Linux):

```bash
apt update  
apt install certbot  
certbot certonly --standalone -d www.yourdomain.com
```

После успешного получения сертификатов обновите переменные в `.env`:

CERT_FULLCHAIN_PATH=/etc/letsencrypt/live/yourdomain_com/fullchain.pem  
CERT_KEY_PATH=/etc/letsencrypt/live/yourdomain_com/privkey.pem

### **4. Сборка и запуск проекта**

Для сборки и запуска всего проекта выполните:

```bash
./refresh.sh
```

---

## **✅ Проверка работы**

**Проверка Telegram-бота:**

Отправьте команду `/start` боту в Telegram, подпишитесь на канал и убедитесь, что после проверки доступа бот показывает оплату и затем выдает кнопки подключения для разных устройств.

**Админ-команды:**

* `/users` – посмотреть сохраненных пользователей.  
* `/banned` – посмотреть пользователей с вечным баном.  
* `/ban 123456789` – вручную выдать вечный бан.  
* `/unban 123456789` – снять вечный бан.  

**Аудит клиентов x-ui:**

На сервере можно запустить локальный аудит базы `x-ui`, чтобы увидеть клиентов, их трафик, известные IP и пометки по подозрительной активности:

```bash
python3 scripts/audit_xui.py --db /etc/x-ui/x-ui.db
```

Проверка одного клиента:

```bash
python3 scripts/audit_xui.py --db /etc/x-ui/x-ui.db --email tg_1017786982
```

**Live-мониторинг активных IP на VPN-порту:**

```bash
bash scripts/live_clients.sh
```

Для другого порта:

```bash
bash scripts/live_clients.sh 443
```

**Карта активных IP:**

Скрипт соберёт текущие IP на VPN-порту, определит страну и город и создаст HTML-карту:

```bash
python3 scripts/map_live_clients.py --port 443
```

По умолчанию Чита считается нормальной зоной, а остальные города помечаются как подозрительные. При необходимости доверенный город можно переопределить:

```bash
python3 scripts/map_live_clients.py --port 443 --trusted-city Chita
```

По умолчанию карта сохранится в:

```bash
reports/live_clients_map.html
```
