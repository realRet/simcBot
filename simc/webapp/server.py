import flask
import logging

from simc.bot.simc import Simc
from simc.config import settings


app = flask.Flask(__name__, static_folder=str(settings.SIMCRAFT_SIMS_DIR))
logger = logging.getLogger(__name__)


def webservice():
    logger.debug("SimC Web App Starting...")
    app.run(host=settings.LISTEN_IP, port=settings.LISTEN_PORT, threaded=True)


@app.route('/')
def home():
    return flask.render_template('403.html')


@app.route('/<addon_url>')
def my_form(addon_url):
    sim_cog = Simc.get_cog('Simulation')

    if sim_cog.wait_data:
        return flask.render_template("data_receieve.html")
    else:
        return flask.render_template("403.html")


@app.route('/submit', methods=['POST'])
def submit_textarea():
    sim_cog = Simc.get_cog('Simulation')

    text = flask.request.form['text']
    sim_cog.addon_data = text
    with open(sim_cog.sims[sim_cog.user]['addon'], "w") as fo:
        fo.write(text)
    sim_cog.wait_data = False
    return 'Data received\nThis page can now be closed'
