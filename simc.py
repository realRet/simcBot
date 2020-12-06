import os
import sys
import subprocess
import discord
import aiohttp
import asyncio
import json
import logging
import time
import threading
import wowapi
from datetime import datetime
from urllib.parse import quote
from flask import Flask, app, render_template, request, redirect

os.chdir(os.path.dirname(os.path.abspath(__file__)))
with open('user_data.json') as data_file:
    user_opt = json.load(data_file)

simc_opts = user_opt['simcraft_opt'][0]
server_opts = user_opt['server_opt'][0]

logger = logging.getLogger('discord')
level = logging.getLevelName(server_opts['loglevel'])
logger.setLevel(level)
handler = logging.FileHandler(filename=server_opts['logfile'], encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def webservice():
    app.run(host=server_opts['listen_ip'], port=server_opts['listen_port'], threaded=True)


app = Flask(__name__)
thread = threading.Thread(target=webservice, args=())
thread.daemon = True
thread.start()

bot = discord.Client()
server = bot.get_guild(server_opts['serverid'])
threads = os.cpu_count()
if 'threads' in simc_opts:
    threads = simc_opts['threads']
process_priority = 'below_normal'
if 'process_priority' in simc_opts:
    process_priority = simc_opts['process_priority']
htmldir = simc_opts['htmldir']
website = simc_opts['website']
os.makedirs(os.path.dirname(os.path.join(htmldir + 'debug', 'test.file')), exist_ok=True)
waiting = False
wait_data = False
busy = False
addon_data = None
user = ''
timeout = simc_opts['timeout']
api_key = simc_opts['api_key']
sims = {}


def check_simc():
    null = open(os.devnull, 'w')
    stdout = open(os.path.join(htmldir, 'simc\\debug', 'simc.ver'))
    try:
        subprocess.Popen(simc_opts['executable'], universal_newlines=True, stderr=null, stdout=stdout)
    except FileNotFoundError as e:
        logger.critical('Simulationcraft program could not be run. (ERR: %s)' % e)
    time.sleep(1)
    with open(os.path.join(htmldir, 'simc\\debug', 'simc.stout'), errors='replace') as v:
        version = v.readline().rstrip('\n')
    return version

async def set_status():
    if len(sims) == server_opts['queue_limit']:
        try:
            await bot.change_presence(status=discord.Status.dnd,
                                      game=discord.Game(name='Sim: %s/%s' % (len(sims), server_opts['queue_limit'])))
        except:
            logger.warning('Failed to set presence for full queue.')
            pass
    else:
        try:
            await bot.change_presence(status=discord.Status.online,
                                      game=discord.Game(name='Sim: %s/%s' % (len(sims), server_opts['queue_limit'])))
        except:
            logger.warning('Failed to set presence for queue.')
            pass


async def check_spec(region, realm, char):
    global api_key
    url = "https://%s.api.battle.net/wow/character/%s/%s?fields=talents&locale=en_GB&apikey=%s" % (region, realm,
                                                                                                   quote(char), api_key)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            try:
                data = await response.json()
                if 'reason' in data:
                    return data['reason']
                else:
                    spec = 0
                    for i in range(len(data['talents'])):
                        for line in data['talents']:
                            if 'selected' in line:
                                role = data['talents'][spec]['spec']['role']
                                return role
                            else:
                                spec += +1
            except:
                logger.critical('Error in aiohttp request: %s', url)
                return 'Failed to look up class spec from armory.'

@app.route('/')
def default():
    return redirect('https://github.com/stokbaek/simc-discord', code=302)


@app.route('/<addon_url>')
def my_form(addon_url):
    if wait_data:
        return render_template("data_receieve.html")
    else:
        return render_template("403.html")


@app.route('/submit', methods=['POST'])
def submit_textarea():
    global addon_data
    global wait_data
    text = request.form['text']
    addon_data = text
    with open(sims[user]['addon'], "w") as fo:
        fo.write(text)
    wait_data = False
    return 'Data received\nThis page can now be closed'


async def data_sim():
    global api_key
    global waiting
    global wait_data
    failed = False
    m_temp = ''
    while not waiting:
        waiting = True
        timer = 0
        if sims[user]['data'] == 'addon':
            sims[user]['addon'] = '%ssims/%s/%s-%s.simc' % (
                htmldir, sims[user]['char'], sims[user]['char'], sims[user]['timestr'])
            addon_url = '%s-%s' % (sims[user]['char'], sims[user]['timestr'])
            await set_status()
            msg = 'You can add your addon data here: %s:%s/%s' % (website, server_opts['listen_port'], addon_url)
            await sims[user]['message'].author.send(msg)
            wait_data = True
            while wait_data:
                timer += 1
                await asyncio.sleep(1)
                if timer > simc_opts['data_timeout']:
                    wait_data = False
            if not os.path.isfile(sims[user]['addon']):
                await sims[user]['message'].author.send('No data given. Resetting session.')
                del sims[user]
                waiting = False
                await set_status()
                logger.info('No data was given to bot. Aborting sim.')
                failed = True
            else:
                healing_roles = ['restoration', 'holy', 'discipline', 'mistweaver']
                for crole in healing_roles:
                    crole = 'spec=' + crole
                    if crole in addon_data:
                        await sims[user]['message'].channel.send(
                                               'SimulationCraft does not support healing.')
                        del sims[user]
                        waiting = False
                        await set_status()
                        logger.info('Character is a healer. Aborting sim.')
                        failed = True

        if sims[user]['data'] != 'addon':
            api = await check_spec(sims[user]['region'], sims[user]['realm'].replace('_', '-'), sims[user]['char'])
            if api == 'HEALING':
                await sims[user]['message'].channel.send('SimulationCraft does not support healing.')
                waiting = False
                del sims[user]
                logger.info('Character is a healer. Aborting sim.')
                failed = True
            elif not api == 'DPS' and not api == 'TANK':
                msg = 'Something went wrong: %s' % api
                await sims[user]['message'].channel.send(msg)
                waiting = False
                del sims[user]
                logger.warning('Simulation could not start: %s' % api)
                failed = True
        for item in simc_opts['fightstyles']:
            if item.lower() == sims[user]['fightstyle'].lower():
                m_temp = m_temp + '**__' + item + '__**, '
            else:
                m_temp = m_temp + item + ', '
        for key in sims[user]:
            if key == 'movements':
                sims[user]['movements'] = m_temp
        if busy:
            position = len(sims) - 1
            if position > 0:
                await sims[user]['message'].channel.send(
                                       'Simulation added to queue. Queue position: %s' % position)
                await set_status()
                logger.info('A new simulation has been added to queue')
        if not failed:
            bot.loop.create_task(sim())
        else:
            return

async def sim():
    global sims
    global busy
    global waiting
    running = 0
    waiting = False
    while not busy:
        busy = True
        ptr = 'No'
        sim_user = list(sorted(sims))[0]
        filename = '%s-%s' % (sims[sim_user]['char'], sims[sim_user]['timestr'])
        link = 'Simulation: %s/sims/%s/%s.html' % (website, sims[sim_user]['char'], filename)
        message = sims[sim_user]['message']
        loop = True
        scale_stats = 'agility,strength,intellect,crit_rating,haste_rating,mastery_rating,versatility_rating'
        options = 'calculate_scale_factors=%s scale_only=%s html=%ssims/%s/%s.html threads=%s iterations=%s ' \
                  'fight_style=%s enemy=%s apikey=%s process_priority=%s max_time=%s' % (sims[sim_user]['scale'],
                                                                                         scale_stats, htmldir,
                                                                                         sims[sim_user]['char'],
                                                                                         filename,
                                                                                         threads, sims[sim_user][
                                                                                             'iterations'],
                                                                                         sims[sim_user]['fightstyle'],
                                                                                         sims[sim_user]['enemy'],
                                                                                         api_key,
                                                                                         process_priority,
                                                                                         sims[sim_user]['length'])
        if sims[sim_user]['data'] == 'addon':
            options += ' input=%s' % sims[sim_user]['addon']
        else:
            options += ' armory=%s,%s,%s' % (
                                             sims[sim_user]['region'], sims[sim_user]['realm'].replace('_', '-'),
                                             sims[sim_user]['char'])

        if sims[sim_user]['l_fixed'] == 1:
            options += ' vary_combat_length=0.0 fixed_time=1'
        if sims[sim_user]['ptr'] == 1:
            options += ' ptr=1'
            ptr = 'Yes'

        await set_status()
        command = "%s %s" % (simc_opts['executable'], options)
        stout = open(os.path.join(htmldir, 'debug', 'simc.stout'), "w")
        sterr = open(os.path.join(htmldir, 'debug', 'simc.sterr'), "w")
        try:
            process = subprocess.Popen(command.split(" "), universal_newlines=True, stdout=stout, stderr=sterr)
            logger.info('----------------------------------')
            logger.info('%s started a simulation:' % sims[sim_user]['message'].author)
            logger.info('Character: ' + sims[sim_user]['char'].capitalize())
            logger.info('Realm: ' + sims[sim_user]['realm'].title().replace('_', ' '))
            logger.info('Fightstyle: ' + sims[sim_user]['movements'][
                                         sims[sim_user]['movements'].find("**__") + 4:sims[sim_user]['movements'].find(
                                             "__**")])
            logger.info('Fight Length: ' + str(sims[sim_user]['length']))
            logger.info('AOE: ' + sims[sim_user]['aoe'])
            logger.info('Iterations: ' + sims[sim_user]['iterations'])
            logger.info('Scaling: ' + sims[sim_user]['scaling'].capitalize())
            logger.info('Data: ' + sims[sim_user]['data'].capitalize())
            logger.info('PTR: ' + ptr)
            logger.info('----------------------------------')
        except FileNotFoundError as e:
            await sims[sim_user]['message'].channel.send('ERR: Simulation could not start.')
            logger.critical('Bot could not start simulationcraft program. (ERR: %s)' % e)
            del sims[sim_user]
            await set_status()
            busy = False
            return
        msg = 'Realm: %s\nCharacter: %s\nFightstyle: %s\nFight Length: %s\nAoE: %s\n' \
              'Iterations: %s\nScaling: %s\nData: %s\nPTR: %s' % (
                  sims[sim_user]['realm'].title().replace('_', ' '), sims[sim_user]['char'].capitalize(),
                  sims[sim_user]['movements'],
                  sims[sim_user]['length'], sims[sim_user]['aoe'].capitalize(), sims[sim_user]['iterations'],
                  sims[sim_user]['scaling'].capitalize(), sims[sim_user]['data'].capitalize(), ptr)
        await sims[sim_user]['message'].channel.send('\nSimulationCraft:\n' + msg)
        load = await sims[sim_user]['message'].channel.send('Simulating: Starting...')
        await asyncio.sleep(1)
        while loop:
            running += 2
            if running > timeout * 60:
                await bot.edit_message(load, 'Simulation timeout')
                process.terminate()
                del sims[sim_user]
                await set_status()
                logger.warning('Simulation timeout')
                loop = False
                busy = False
                while wait_data:
                    logger.info('Wont start next sim, still waiting on data')
                    await asyncio.sleep(1)
                if len(sims) == 0:
                    return
                else:
                    bot.loop.create_task(sim())

            await asyncio.sleep(1)
            with open(os.path.join(htmldir, 'debug', 'simc.stout'), errors='replace') as p:
                process_check = p.readlines()
            with open(os.path.join(htmldir, 'debug', 'simc.sterr'), errors='replace') as e:
                err_check = e.readlines()
            if len(err_check) > 0:
                if 'ERROR' in err_check[-1]:
                    await bot.edit_message(load, 'Simulation failed: ' + '\n'.join(err_check))
                    process.terminate()
                    del sims[sim_user]
                    await set_status()
                    logger.warning('Simulation failed: ' + '\n'.join(err_check))
                    loop = False
                    busy = False
                    while wait_data:
                        logger.info('Wont start next sim, still waiting on data')
                        await asyncio.sleep(1)
                    if len(sims) == 0:
                        return
                    else:
                        bot.loop.create_task(sim())

            if len(process_check) > 1:
                if 'report took' in process_check[-2]:
                    loop = False
                    await discord.message.Message.edit('Simulation done.')
                    await sims[sim_user]['message'].channel.send(
                                           link + ' {0.author.mention}'.format(message))
                    process.terminate()
                    busy = False
                    del sims[sim_user]
                    await set_status()
                    logger.info('Simulation completed.')
                    while wait_data:
                        logger.info('Wont start next sim, still waiting on data')
                        await asyncio.sleep(1)
                    if len(sims) != 0:
                        bot.loop.create_task(sim())
                    else:
                        return
                else:
                    if 'Generating' in process_check[-1]:
                        done = '█' * (20 - process_check[-1].count('.'))
                        missing = '░' * (process_check[-1].count('.'))
                        progressbar = done + missing
                        percentage = 100 - process_check[-1].count('.') * 5
                        status = process_check[-1].split()[1]
                        if 'sec' in process_check[-1].split()[-1] or 'min' in process_check[-1].split()[-1]:
                            if 'min' in process_check[-1].split()[-2]:
                                timer = ' (' + process_check[-1].split()[-2] + ' ' + process_check[-1].split()[-1] + \
                                        ' left)'
                            else:
                                timer = ' (' + process_check[-1].split()[-1] + ' left)'
                        else:
                            timer = ''
                        try:
                            load = await bot.edit_message(load, status + ' ' + progressbar + ' ' +
                                                          str(percentage) + '%' + timer)
                        except:
                            logger.warning('Failed updating progress')
                            pass


def check(addon_data):
    if addon_data.channel.is_private:
        return addon_data.content.endswith('DONE')


@bot.event
async def on_message(message):
    global busy
    global user
    global sims
    a_temp = ''
    channel = server_opts['channelid']
    timestr = datetime.utcnow().strftime('%Y%m%d.%H%m%S%f')[:-3]
    args = message.content.lower()
    if message.author == bot.user:
        return
    #if discord.channel.ChannelType.private:
    #    logger.info('%s sent follow data to bot: %s' % (message.author, message.content))
    if args.startswith('!simc'):
        args = args.split(' -')
        if args:
            try:
                if args[1].startswith(('h', 'help')):
                    with open('help.file', errors='replace') as h:
                        msg = h.read()
                    await message.author.send(msg)
                    return
                elif args[1].startswith(('v', 'version')):
                    await message.channel.send(check_simc())
                    return
                else:
                    if str(message.channel.id) != channel:
                        await message.channel.send('Please use the correct channel.')
                        return
                    if args[1].startswith(('q', 'queue')):
                        if busy:
                            await message.channel.send(
                                                   'Queue: %s/%s' % (len(sims), server_opts['queue_limit']))
                        else:
                            await message.channel.send('Queue is empty')
                        return
                    if busy:
                        if len(sims) > server_opts['queue_limit'] - 1:
                            await message.channel.send(
                                                   '**Queue is full, please try again later.**')
                            logger.info('Sim could not be started because queue is full.')
                            return
                    if waiting:
                        await message.channel.send(
                                               '**Waiting for simc addon data from %s.**' %
                                               sims[user]['message'].author.display_name)
                        logger.info('Failed starting sim. Still waiting on data from previous sim')
                        return
                    user = timestr + '-' + str(message.author)
                    user_sim = {user: {'realm': simc_opts['default_realm'],
                                       'region': simc_opts['region'],
                                       'iterations': simc_opts['default_iterations'],
                                       'scale': 0,
                                       'scaling': 'no',
                                       'data': 'addon',
                                       'char': '',
                                       'aoe': 'no',
                                       'enemy': '',
                                       'addon': '',
                                       'fightstyle': simc_opts['fightstyles'][0],
                                       'movements': '',
                                       'length': simc_opts['length'],
                                       'l_fixed': 0,
                                       'ptr': 0,
                                       'timestr': datetime.utcnow().strftime('%Y%m%d.%H%m%S%f')[:-3],
                                       'message': '',
                                       }
                                }
                    sims.update(user_sim)
                    for key in sims[user]:
                        if key == 'message':
                            sims[user]['message'] = message
                    for i in range(len(args)):
                        if args[i] != '!simc':
                            if args[i].startswith(('r ', 'realm ')):
                                temp = args[i].split()
                                for key in sims[user]:
                                    if key == 'realm':
                                        sims[user]['realm'] = "_".join(temp[1:])
                            elif args[i].startswith(('c ', 'char ', 'character ')):
                                temp = args[i].split()
                                for key in sims[user]:
                                    if key == 'char':
                                        sims[user]['char'] = temp[1]
                            elif args[i].startswith(('s ', 'scaling ')):
                                temp = args[i].split()
                                for key in sims[user]:
                                    if key == 'scaling':
                                        sims[user]['scaling'] = temp[1]
                            elif args[i].startswith(('d ', 'data ')):
                                temp = args[i].split()
                                for key in sims[user]:
                                    if key == 'data':
                                        sims[user]['data'] = temp[1]
                            elif args[i].startswith(('i ', 'iterations ')):
                                if simc_opts['allow_iteration_parameter']:
                                    temp = args[i].split()
                                    for key in sims[user]:
                                        if key == 'iterations':
                                            sims[user]['iterations'] = temp[1]
                                else:
                                    await message.channel.send('Custom iterations is disabled')
                                    logger.info('%s tried using custom iterations while the option is disabled')
                                    return
                            elif args[i].startswith(('f ', 'fight ', 'fightstyle ')):
                                fstyle = False
                                temp = args[i].split()
                                for opt in range(len(simc_opts['fightstyles'])):
                                    if temp[1] == simc_opts['fightstyles'][opt].lower():
                                        for key in sims[user]:
                                            if key == 'fightstyle':
                                                sims[user]['fightstyle'] = temp[1]
                                        fstyle = True
                                if fstyle is not True:
                                    await message.channel.send('Unknown fightstyle.\nSupported Styles: ' +
                                                           ', '.join(simc_opts['fightstyles']))
                                    logger.info(
                                        '%s tried starting sim with unknown fightstyle: %s' % (message.author, temp[1]))
                                    return
                            elif args[i].startswith(('a ', 'aoe ')):
                                temp = args[i].split()
                                for key in sims[user]:
                                    if key == 'aoe':
                                        sims[user]['aoe'] = temp[1]
                            elif args[i].startswith(('l ', 'length ')):
                                temp = args[i].split()
                                for key in sims[user]:
                                    if key == 'length':
                                        sims[user]['length'] = temp[1]
                                if len(temp) > 2:
                                    if temp[2] == 'fixed':
                                        for key in sims[user]:
                                            if key == 'l_fixed':
                                                sims[user]['l_fixed'] = 1
                            elif args[i] == 'ptr':
                                for key in sims[user]:
                                    if key == 'ptr':
                                        sims[user]['ptr'] = 1
                            else:
                                await message.channel.send('Unknown command. Use !simc -h/help for commands')
                                del sims[user]
                                logger.info('Unknown command given to bot.')
                                return
                    if sims[user]['char'] == '':
                        await message.channel.send('Character name is needed')
                        del sims[user]
                        logger.info('No character name given. Aborting sim.')
                        return
                    if sims[user]['scaling'] == 'yes':
                        for key in sims[user]:
                            if key == 'scale':
                                sims[user]['scale'] = 1
                    if sims[user]['aoe'] == 'yes':
                        for targets in range(0, simc_opts['aoe_targets']):
                            targets += + 1
                            a_temp += 'enemy=target%s ' % targets
                        for key in sims[user]:
                            if key == 'enemy':
                                sims[user]['enemy'] = a_temp

                    os.makedirs(os.path.dirname(os.path.join(htmldir,'sims', sims[user]['char'], 'test.file')),
                                exist_ok=True)
                    bot.loop.create_task(data_sim())
            except IndexError as e:
                await message.channel.send('Unknown command. Use !simc -h/help for commands')
                logger.info('No command given to bot.(ERR: %s)' % e)
                return


@bot.event
async def on_ready():
    logger.info('Logged in as')
    logger.info(bot.user.name)
    logger.info(bot.user.id)
    logger.info(check_simc())
    logger.info('--------------')
    await set_status()

bot.run(server_opts['token'])
