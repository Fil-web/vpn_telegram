import asyncio
import logging
from urllib.parse import unquote

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatType
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from loader import config
from tgbot.handlers import routers_list
from tgbot.middlewares.flood import ThrottlingMiddleware
from utils import broadcaster

logger = logging.getLogger(__name__)


async def connect_page_handler(request: web.Request) -> web.Response:
    encoded_config = request.query.get("config", "")
    config_url = unquote(encoded_config).strip()

    if not config_url:
        return web.Response(text="Config URL is required.", status=400)

    app_link = f"v2raytun://import/{encoded_config}"
    html = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Redirecting</title>
  <style>
    body {{
      margin: 0;
      background: #f6fbff;
    }}
  </style>
</head>
<body>
  <script>
    window.setTimeout(function () {{
      window.location.href = "{app_link}";
    }}, 50);
  </script>
</body>
</html>"""
    return web.Response(text=html, content_type="text/html")


async def manual_page_handler(request: web.Request) -> web.Response:
    encoded_config = request.query.get("config", "")
    config_url = unquote(encoded_config).strip()

    if not config_url:
        return web.Response(text="Config URL is required.", status=400)

    html = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ручное подключение</title>
  <style>
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: linear-gradient(180deg, #f6fbff 0%, #eef4f8 100%);
      color: #102a43;
    }}
    .wrap {{
      max-width: 720px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .card {{
      background: #ffffff;
      border-radius: 24px;
      padding: 24px;
      box-shadow: 0 20px 60px rgba(16, 42, 67, 0.08);
    }}
    h1 {{ margin-top: 0; font-size: 28px; }}
    p {{ line-height: 1.6; }}
    .btn {{
      display: block;
      text-align: center;
      text-decoration: none;
      border-radius: 16px;
      padding: 16px 18px;
      font-weight: 600;
      margin: 24px 0 12px;
      background: #eef4f8;
      color: #102a43;
    }}
    .btn.secondary {{
      background: #102a43;
      color: #ffffff;
    }}
    .hint {{
      margin-top: 12px;
      color: #486581;
      font-size: 14px;
    }}
    .status {{
      margin: 12px 0 0;
      color: #1f7a54;
      font-size: 14px;
      min-height: 20px;
    }}
    code {{
      display: block;
      overflow-wrap: anywhere;
      background: #f7fafc;
      border-radius: 12px;
      padding: 14px;
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Ручное добавление VPN</h1>
      <p>
        Android: откройте v2RayTun и добавьте subscription-ссылку вручную.<br>
        iPhone / iOS: установите V2Ray Client из App Store и добавьте subscription-ссылку вручную.
      </p>
      <a class="btn secondary" href="https://apps.apple.com/ru/app/v2ray-client/id6747379524" target="_blank" rel="noopener noreferrer">🍎 Открыть приложение для iPhone / iOS</a>
      <a class="btn" href="#" id="copy-btn">Скопировать ссылку</a>
      <div class="status" id="copy-status"></div>
      <code id="config">{config_url}</code>
      <p class="hint">Если кнопка копирования не сработала, выделите ссылку ниже вручную и вставьте ее в приложение.</p>
    </div>
  </div>
  <script>
    async function copyConfig(event) {{
      event.preventDefault();
      const config = document.getElementById('config').innerText;
      const status = document.getElementById('copy-status');
      try {{
        if (navigator.clipboard && window.isSecureContext) {{
          await navigator.clipboard.writeText(config);
        }} else {{
          const textarea = document.createElement('textarea');
          textarea.value = config;
          textarea.setAttribute('readonly', '');
          textarea.style.position = 'absolute';
          textarea.style.left = '-9999px';
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand('copy');
          document.body.removeChild(textarea);
        }}
        status.textContent = 'Ссылка скопирована.';
      }} catch (error) {{
        status.textContent = 'Не удалось скопировать автоматически. Скопируйте ссылку вручную ниже.';
      }}
    }}
    document.getElementById('copy-btn').addEventListener('click', copyConfig);
  </script>
</body>
</html>"""
    return web.Response(text=html, content_type="text/html")


def create_auxiliary_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/connect", connect_page_handler)
    app.router.add_get("/manual", manual_page_handler)
    return app


async def on_startup(bot: Bot):
    await broadcaster.broadcast(bot, [config.tg_bot.admin_id], "Бот запущен")
    await register_commands(bot)
    if config.webhook.use_webhook:
        await bot.set_webhook(f"https://{config.webhook.domain}{config.webhook.url}webhook")


async def register_commands(bot: Bot):
    commands = [
        BotCommand(command='start', description='Главное меню 🏠'),
        BotCommand(command='help', description='Помощь'),
        BotCommand(command='vpn', description='Получить ключи'),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


def register_global_middlewares(dp: Dispatcher):
    """
    Register global middlewares for the given dispatcher.
    Global middlewares here are the ones that are applied to all the handlers (Specify for the type of update)

    :param dp: The dispatcher instance.
    :type dp: Dispatcher
    :param config: The configuration object from the loaded configuration
    :return: None
    """

    middleware_types = [
        ThrottlingMiddleware(),
    ]
    for middleware_type in middleware_types:
        dp.message.outer_middleware(middleware_type)
        dp.callback_query.outer_middleware(middleware_type)
    dp.callback_query.outer_middleware(CallbackAnswerMiddleware())
    dp.message.filter(F.chat.type == ChatType.PRIVATE)


def main_webhook():
    from loader import bot, dp

    dp.include_routers(*routers_list)
    dp.startup.register(on_startup)
    register_global_middlewares(dp)

    app = web.Application()

    # Create an instance of request handler,
    # aiogram has few implementations for different cases of usage
    # In this example we use SimpleRequestHandler which is designed to handle simple cases
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        # secret_token=WEBHOOK_SECRET,
    )
    # Register webhook handler on application
    webhook_requests_handler.register(app, path=f'{config.webhook.url}webhook')

    # Mount dispatcher startup and shutdown hooks to aiohttp application
    setup_application(app, dp, bot=bot)

    # And finally start webserver
    web.run_app(app, host='vpn_bot', port=config.tg_bot.port)


async def main_polling():
    from loader import bot, dp
    dp.include_routers(*routers_list)

    register_global_middlewares(dp)
    await on_startup(bot)
    await bot.delete_webhook()
    runner = web.AppRunner(create_auxiliary_app())
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=config.tg_bot.port)
    await site.start()
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()


if __name__ == '__main__':
    if config.webhook.use_webhook:
        main_webhook()
    else:
        try:
            asyncio.run(main_polling())
        except (KeyboardInterrupt, SystemExit):
            logging.error("Бот выключен!")
