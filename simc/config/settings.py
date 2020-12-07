import json
import logging.config
import pathlib

cwd = pathlib.Path(__file__).parent
config_file_path = cwd / "user_data.json"

with open(str(config_file_path), "r") as config_file:
    configs = json.load(config_file)

# Web Server Configs
# These are all configurations related to the Flask web server.
LISTEN_IP = configs["web_server_opts"]["listen_ip"]
LISTEN_PORT = configs["web_server_opts"]["listen_port"]


# SimC Bot Configs
# All configurations related to the configuration of the SimC Bot.
DISCORD_SERVER_ID = configs["simc_bot_opts"]["server_id"]
DISCORD_CHANNEL_ID = configs["simc_bot_opts"]["channel_id"]
DISCORD_API_TOKEN = configs["simc_bot_opts"]["token"]
SIMC_QUEUE_LIMIT = configs["simc_bot_opts"]["queue_limit"]
SIMC_LOG_LEVEL = configs["simc_bot_opts"]["log_level"]
SIMC_LOGS_DIR = pathlib.Path(configs["simc_bot_opts"]["logs_dir"])


# Simulation Craft Options
# Configurations relating to the running of Simulation Craft
SIMC_WEBSITE_URL = configs["simcraft_opts"]["website_url"]
SIMCRAFT_API_KEY = configs["simcraft_opts"]["api_key"]
SIMCRAFT_SIMS_DIR = pathlib.Path(configs["simcraft_opts"]["sims_dir"])
SIMCRAFT_CACHE_DIR = pathlib.Path(configs["simcraft_opts"]["sims_cache_dir"])
SIMCRAFT_DEFAULT_REALM = configs["simcraft_opts"]["default_realm"]
SIMCRAFT_EXE_DIR = pathlib.Path(configs["simcraft_opts"]["simcraft_dir"])
SIMCRAFT_EXE_NAME = configs["simcraft_opts"]["simcraft_exe_name"]
SIMCRAFT_REGION = configs["simcraft_opts"]["region"]
SIMCRAFT_ALLOW_ITERATION = configs["simcraft_opts"]["allow_iteration"]
SIMCRAFT_DEFAULT_ITERATIONS = configs["simcraft_opts"]["default_iterations"]
SIMCRAFT_FIGHT_STYLES = configs["simcraft_opts"]["fight_styles"]
SIMCRAFT_AOE_TARGETS = configs["simcraft_opts"]["aoe_targets"]
SIMCRAFT_THREADS = configs["simcraft_opts"]["threads"]
SIMCRAFT_PROCESS_PRIORITY = configs["simcraft_opts"]["process_priority"]
SIMCRAFT_LENGTH = configs["simcraft_opts"]["length"]
SIMCRAFT_DATA_TIMEOUT = configs["simcraft_opts"]["data_timeout"]
SIMCRAFT_TIMEOUT = configs["simcraft_opts"]["timeout"]

if not SIMCRAFT_CACHE_DIR.exists():
    SIMCRAFT_CACHE_DIR.mkdir(parents=True, exist_ok=True)


# Logging Dict Settings
if not SIMC_LOGS_DIR.exists():
    SIMC_LOGS_DIR.mkdir(parents=True, exist_ok=True)

SIMC_LOG_FILE = pathlib.Path(SIMC_LOGS_DIR) / "simc.log"

logging.config.dictConfig({
    "version": 1,
    "formatters": {
        "standard": {
            'format': "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "standard"
        },
        "file": {
            "level": SIMC_LOG_LEVEL,
            "class": "logging.FileHandler",
            "filename": SIMC_LOG_FILE,
            "formatter": "standard"
        }
    },
    "loggers": {
        "": {   # root logger
            "level": SIMC_LOG_LEVEL,
            "handlers": ['console', 'file'],
            "propagate": False
        },
        "simc_bot.bot": {
            "level": SIMC_LOG_LEVEL,
            "handlers": ['console', 'file'],
            "propagate": False
        },
        "simc_bot.webapp": {
            "level": SIMC_LOG_LEVEL,
            "handlers": ['console', 'file'],
            "propagate": False
        }
    }
})
