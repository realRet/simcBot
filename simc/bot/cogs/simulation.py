import asyncio
from datetime import datetime
import discord
from discord.ext import commands
import logging
import os
import pathlib
import re
import subprocess
import time

from simc.config import settings


logger = logging.getLogger(__name__)


class Simulation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.waiting = False
        self.wait_data = False
        self.busy = False
        self.addon_data = None
        self.sims = {}
        self.threads = os.cpu_count() if not settings.SIMCRAFT_THREADS else settings.SIMCRAFT_THREADS
        self.user = ''

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Logged in as: {self.bot.user.name} - {self.bot.user.id}")
        logger.info(f"Simulation Craft Version: {self.check_simc()}")

        await self.set_status()

    @classmethod
    def check_simc(cls):
        stdout = open(str(settings.SIMCRAFT_CACHE_DIR / 'simc.ver'), 'w+')
        try:
            subprocess.Popen(str(settings.SIMCRAFT_EXE_DIR / settings.SIMCRAFT_EXE_NAME),
                             universal_newlines=True, stderr=subprocess.DEVNULL, stdout=stdout)
        except FileNotFoundError as e:
            logger.critical('Simulationcraft program could not be run. (ERR: %s)' % e)
        time.sleep(1)
        with open(str(settings.SIMCRAFT_CACHE_DIR / 'simc.ver'), errors='replace') as v:
            version = v.readline().rstrip('\n')
        return version

    async def set_status(self):
        presence = discord.Status.dnd if len(self.sims) == settings.SIMC_QUEUE_LIMIT else discord.Status.online
        queue = f"{len(self.sims)} / {settings.SIMC_QUEUE_LIMIT}"
        try:
            await self.bot.change_presence(
                status=presence,
                activity=discord.Game(name=f"Sim: {queue}")
            )
        except:
            logger.warning(f"Failed to set presence for the current queue: {queue}.")
            pass

    async def data_sim(self):
        failed = False
        m_temp = ''
        while not self.waiting:
            self.waiting = True
            timer = 0
            if self.sims[self.user]['data'] == 'addon':

                self.sims[self.user]['addon'] = '%s/%s-%s.simc' % (
                    str(settings.SIMCRAFT_SIMS_DIR / self.sims[self.user]['char']), self.sims[self.user]['char'],
                    self.sims[self.user]['timestr'])
                addon_url = '%s-%s' % (self.sims[self.user]['char'], self.sims[self.user]['timestr'])
                await self.set_status()
                msg = 'You can add your addon data here: %s/%s' % (settings.SIMC_WEBSITE_URL, addon_url)
                await self.sims[self.user]['message'].author.send(msg)
                self.wait_data = True
                while self.wait_data:
                    timer += 1
                    await asyncio.sleep(1)
                    if timer > settings.SIMCRAFT_DATA_TIMEOUT:
                        self.wait_data = False
                if not os.path.isfile(self.sims[self.user]['addon']):
                    await self.sims[self.user]['message'].author.send('No data given. Resetting session.')
                    del self.sims[self.user]
                    self.waiting = False
                    await self.set_status()
                    logger.info('No data was given to bot. Aborting sim.')
                    failed = True
                else:
                    healing_roles = ['restoration', 'holy', 'discipline', 'mistweaver']
                    for crole in healing_roles:
                        crole = 'spec=' + crole
                        if crole in self.addon_data:
                            await self.sims[self.user]['message'].channel.send(
                                                   'SimulationCraft does not support healing.')
                            del self.sims[self.user]
                            self.waiting = False
                            await self.set_status()
                            logger.info('Character is a healer. Aborting sim.')
                            failed = True

            # if self.sims[self.user]['data'] != 'addon':
            #     api = await check_spec(self.sims[self.user]['region'], self.sims[self.user]['realm'].replace('_', '-'),
            #                            self.sims[self.user]['char'])
            #     if api == 'HEALING':
            #         await self.sims[self.user]['message'].channel.send('SimulationCraft does not support healing.')
            #         self.waiting = False
            #         del self.sims[self.user]
            #         logger.info('Character is a healer. Aborting sim.')
            #         failed = True
            #     elif not api == 'DPS' and not api == 'TANK':
            #         msg = 'Something went wrong: %s' % api
            #         await self.sims[self.user]['message'].channel.send(msg)
            #         self.waiting = False
            #         del self.sims[self.user]
            #         logger.warning('Simulation could not start: %s' % api)
            #         failed = True
            for item in settings.SIMCRAFT_FIGHT_STYLES:
                if item.lower() == self.sims[self.user]['fightstyle'].lower():
                    m_temp = m_temp + '**__' + item + '__**, '
                else:
                    m_temp = m_temp + item + ', '
            for key in self.sims[self.user]:
                if key == 'movements':
                    self.sims[self.user]['movements'] = m_temp
            if self.busy:
                position = len(self.sims) - 1
                if position > 0:
                    await self.sims[self.user]['message'].channel.send(
                                           'Simulation added to queue. Queue position: %s' % position)
                    await self.set_status()
                    logger.info('A new simulation has been added to queue')
            if not failed:
                self.bot.loop.create_task(self.sim())
            else:
                return

    async def sim(self):
        running = 0
        self.waiting = False
        while not self.busy:
            self.busy = True
            ptr = 'No'
            sim_user = list(sorted(self.sims))[0]
            filename = '%s-%s' % (self.sims[sim_user]['char'], self.sims[sim_user]['timestr'])
            link = 'Simulation: %s/sims/%s/%s.html' % (settings.SIMC_WEBSITE_URL,
                                                            self.sims[sim_user]['char'], filename)
            message = self.sims[sim_user]['message']
            loop = True
            scale_stats = 'agility,strength,intellect,crit_rating,haste_rating,mastery_rating,versatility_rating'
            options = 'calculate_scale_factors=%s scale_only=%s html=%s threads=%s iterations=%s ' \
                      'fight_style=%s enemy=%s apikey=%s process_priority=%s max_time=%s' % (
                self.sims[sim_user]['scale'], scale_stats, str(
                    settings.SIMCRAFT_SIMS_DIR / self.sims[sim_user]['char'] / f"{filename}.html"),
                self.threads, self.sims[sim_user]['iterations'], self.sims[sim_user]['fightstyle'],
                self.sims[sim_user]['enemy'], settings.SIMCRAFT_API_KEY, settings.SIMCRAFT_PROCESS_PRIORITY,
                self.sims[sim_user]['length']
            )

            if self.sims[sim_user]['data'] == 'addon':
                options += ' input=%s' % self.sims[sim_user]['addon']
            else:
                options += ' armory=%s,%s,%s' % (
                                                 self.sims[sim_user]['region'], self.sims[sim_user]['realm'].replace('_', '-'),
                                                 self.sims[sim_user]['char'])

            if self.sims[sim_user]['l_fixed'] == 1:
                options += ' vary_combat_length=0.0 fixed_time=1'
            if self.sims[sim_user]['ptr'] == 1:
                options += ' ptr=1'
                ptr = 'Yes'

            await self.set_status()
            command = "%s %s" % (str(settings.SIMCRAFT_EXE_DIR / settings.SIMCRAFT_EXE_NAME), options)
            stout = open(str(settings.SIMCRAFT_CACHE_DIR / 'simc.stout'), "w+")
            sterr = open(str(settings.SIMCRAFT_CACHE_DIR / 'simc.sterr'), "w+")
            try:
                process = subprocess.Popen(command.split(" "), universal_newlines=True, stdout=stout, stderr=sterr)
                logger.info('----------------------------------')
                logger.info('%s started a simulation:' % self.sims[sim_user]['message'].author)
                logger.info('Character: ' + self.sims[sim_user]['char'].capitalize())
                logger.info('Realm: ' + self.sims[sim_user]['realm'].title().replace('_', ' '))
                logger.info('Fightstyle: ' + self.sims[sim_user]['movements'][
                                             self.sims[sim_user]['movements'].find("**__") + 4:self.sims[sim_user]['movements'].find(
                                                 "__**")])
                logger.info('Fight Length: ' + str(self.sims[sim_user]['length']))
                logger.info('AOE: ' + self.sims[sim_user]['aoe'])
                logger.info('Iterations: ' + self.sims[sim_user]['iterations'])
                logger.info('Scaling: ' + self.sims[sim_user]['scaling'].capitalize())
                logger.info('Data: ' + self.sims[sim_user]['data'].capitalize())
                logger.info('PTR: ' + ptr)
                logger.info('----------------------------------')
            except FileNotFoundError as e:
                await self.sims[sim_user]['message'].channel.send('ERR: Simulation could not start.')
                logger.critical('Bot could not start simulationcraft program. (ERR: %s)' % e)
                del self.sims[sim_user]
                await self.set_status()
                self.busy = False
                return
            msg = '```Realm: %s\nCharacter: %s\nFightstyle: %s\nFight Length: %s\nAoE: %s\n' \
                  'Iterations: %s\nScaling: %s\nData: %s\nPTR: %s```' % (
                      self.sims[sim_user]['realm'].title().replace('_', ' '), self.sims[sim_user]['char'].capitalize(),
                      self.sims[sim_user]['movements'],
                      self.sims[sim_user]['length'], self.sims[sim_user]['aoe'].capitalize(), self.sims[sim_user]['iterations'],
                      self.sims[sim_user]['scaling'].capitalize(), self.sims[sim_user]['data'].capitalize(), ptr)
            await self.sims[sim_user]['message'].channel.send('\nSimulationCraft:\n' + msg)
            load = await self.sims[sim_user]['message'].channel.send('Simulating: Starting...')
            await asyncio.sleep(1)
            while loop:
                running += 2
                if running > settings.SIMCRAFT_TIMEOUT * 60:
                    await load.edit_message(content='Simulation timeout')
                    process.terminate()
                    del self.sims[sim_user]
                    await self.set_status()
                    logger.warning('Simulation timeout')
                    loop = False
                    self.busy = False
                    while self.wait_data:
                        logger.info('Wont start next sim, still waiting on data')
                        await asyncio.sleep(1)
                    if len(self.sims) == 0:
                        return
                    else:
                        self.bot.loop.create_task(self.sim())

                await asyncio.sleep(1)
                with open(str(settings.SIMCRAFT_CACHE_DIR / 'simc.stout'), 'r+', errors='replace') as p:
                    process_check = p.readlines()
                with open(str(settings.SIMCRAFT_CACHE_DIR / 'simc.sterr'), 'r+', errors='replace') as e:
                    err_check = e.readlines()
                if len(err_check) > 0:
                    if 'ERROR' in err_check[-1]:
                        await load.edit_message(content='Simulation failed: ' + '\n'.join(err_check))
                        process.terminate()
                        del self.sims[sim_user]
                        await self.set_status()
                        logger.warning('Simulation failed: ' + '\n'.join(err_check))
                        loop = False
                        self.busy = False
                        while self.wait_data:
                            logger.info('Wont start next sim, still waiting on data')
                            await asyncio.sleep(1)
                        if len(self.sims) == 0:
                            return
                        else:
                            self.bot.loop.create_task(self.sim())

                if len(process_check) > 1:
                    if 'report took' in process_check[-2]:
                        loop = False
                        await load.edit(content='Simulation done.')
                        await self.sims[sim_user]['message'].channel.send(
                                               link + ' {0.author.mention}'.format(message))
                        process.terminate()
                        self.busy = False
                        del self.sims[sim_user]
                        await self.set_status()
                        logger.info('Simulation completed.')
                        while self.wait_data:
                            logger.info('Wont start next sim, still waiting on data')
                            await asyncio.sleep(1)
                        if len(self.sims) != 0:
                            self.bot.loop.create_task(self.sim())
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
                                await load.edit(content=status + ' ' + progressbar + ' ' + str(percentage) + '%' + timer)
                            except:
                                logger.warning('Failed updating progress')
                                pass

    @commands.command()
    async def simc(self, ctx, *, args):
        a_temp = ''
        channel = settings.DISCORD_CHANNEL_ID
        timestr = datetime.utcnow().strftime('%Y%m%d.%H%m%S%f')[:-3]
        logger.debug(f"New simc command from {ctx.author}.")
        if ctx.author == self.bot.user:
            return

        arg_re = re.compile(r"-([a-z]+(?:\s+|$)(?:\s+|[^-]+)?)(?:(?!-)?|$)")
        args = re.findall(arg_re, args.lower())

        if args:
            try:
                if args[0].startswith(('h', 'help')):
                    with open(pathlib.Path(__file__).parent / 'help.file', errors='replace') as h:
                        msg = h.read()
                    await ctx.author.send(msg)
                    return
                elif args[0].startswith(('v', 'version')):
                    await ctx.channel.send(self.check_simc())
                    return
                else:
                    if str(ctx.channel.id) != channel:
                        await ctx.channel.send('Please use the correct channel.')
                        return
                    if args[0].startswith(('q', 'queue')):
                        if self.busy:
                            await ctx.channel.send(
                                                   'Queue: %s/%s' % (len(self.sims), settings.SIMC_QUEUE_LIMIT))
                        else:
                            await ctx.channel.send('Queue is empty')
                        return
                    if self.busy:
                        if len(self.sims) > settings.SIMC_QUEUE_LIMIT - 1:
                            await ctx.channel.send(
                                                   '**Queue is full, please try again later.**')
                            logger.info('Sim could not be started because queue is full.')
                            return
                    if self.waiting:
                        await ctx.channel.send(
                                               '**Waiting for simc addon data from %s.**' %
                                               self.sims[self.user]['message'].author.display_name)
                        logger.info('Failed starting sim. Still waiting on data from previous sim')
                        return
                    self.user = timestr + '-' + str(ctx.author)
                    user_sim = {self.user: {'realm': settings.SIMCRAFT_DEFAULT_REALM,
                                       'region': settings.SIMCRAFT_REGION,
                                       'iterations': settings.SIMCRAFT_DEFAULT_ITERATIONS,
                                       'scale': 0,
                                       'scaling': 'no',
                                       'data': 'addon',
                                       'char': '',
                                       'aoe': 'no',
                                       'enemy': '',
                                       'addon': '',
                                       'fightstyle': settings.SIMCRAFT_FIGHT_STYLES[0],
                                       'movements': '',
                                       'length': settings.SIMCRAFT_LENGTH,
                                       'l_fixed': 0,
                                       'ptr': 0,
                                       'timestr': datetime.utcnow().strftime('%Y%m%d.%H%m%S%f')[:-3],
                                       'message': '',
                                       }
                                }
                    self.sims.update(user_sim)
                    for key in self.sims[self.user]:
                        if key == 'message':
                            self.sims[self.user]['message'] = ctx
                    for i in range(len(args)):
                        if args[i].startswith(('r ', 'realm ')):
                            temp = args[i].split()
                            for key in self.sims[self.user]:
                                if key == 'realm':
                                    self.sims[self.user]['realm'] = "_".join(temp[1:])
                        elif args[i].startswith(('c ', 'char ', 'character ')):
                            temp = args[i].split()
                            for key in self.sims[self.user]:
                                if key == 'char':
                                    self.sims[self.user]['char'] = temp[1]
                        # elif args[i].startswith(('s ', 'scaling ')):
                        #     temp = args[i].split()
                        #     for key in self.sims[user]:
                        #         if key == 'scaling':
                        #             self.sims[user]['scaling'] = temp[1]
                        # elif args[i].startswith(('d ', 'data ')):
                        #     temp = args[i].split()
                        #     for key in self.sims[user]:
                        #         if key == 'data':
                        #             self.sims[user]['data'] = temp[1]
                        elif args[i].startswith(('i ', 'iterations ')):
                            if settings.SIMCRAFT_ALLOW_ITERATION:
                                temp = args[i].split()
                                for key in self.sims[self.user]:
                                    if key == 'iterations':
                                        self.sims[self.user]['iterations'] = temp[1]
                            else:
                                await ctx.channel.send('Custom iterations is disabled')
                                logger.info('%s tried using custom iterations while the option is disabled')
                                return
                        elif args[i].startswith(('f ', 'fight ', 'fightstyle ')):
                            fstyle = False
                            temp = args[i].split()
                            for opt in range(len(settings.SIMCRAFT_FIGHT_STYLES)):
                                if temp[1] == settings.SIMCRAFT_FIGHT_STYLES[opt].lower():
                                    for key in self.sims[self.user]:
                                        if key == 'fightstyle':
                                            self.sims[self.user]['fightstyle'] = temp[1]
                                    fstyle = True
                            if fstyle is not True:
                                await ctx.channel.send('Unknown fightstyle.\nSupported Styles: ' +
                                                           ', '.join(settings.SIMCRAFT_FIGHT_STYLES))
                                logger.info(
                                    '%s tried starting sim with unknown fightstyle: %s' % (ctx.author, temp[1]))
                                return
                        # elif args[i].startswith(('a ', 'aoe ')):
                        #     temp = args[i].split()
                        #     for key in self.sims[self.user]:
                        #         if key == 'aoe':
                        #             self.sims[self.user]['aoe'] = temp[1]
                        elif args[i].startswith(('l ', 'length ')):
                            temp = args[i].split()
                            for key in self.sims[self.user]:
                                if key == 'length':
                                    self.sims[self.user]['length'] = temp[1]
                            if len(temp) > 2:
                                if temp[2] == 'fixed':
                                    for key in self.sims[self.user]:
                                        if key == 'l_fixed':
                                            self.sims[self.user]['l_fixed'] = 1
                        # elif args[i] == 'ptr':
                        #     for key in self.sims[user]:
                        #         if key == 'ptr':
                        #             self.sims[user]['ptr'] = 1
                        else:
                            await ctx.channel.send('Unknown command. Use !simc -h/help for commands')
                            del self.sims[self.user]
                            logger.info('Unknown command given to bot.')
                            return
                    if self.sims[self.user]['char'] == '':
                        await ctx.channel.send('Character name is needed')
                        del self.sims[self.user]
                        logger.info('No character name given. Aborting sim.')
                        return
                    if self.sims[self.user]['scaling'] == 'yes':
                        for key in self.sims[self.user]:
                            if key == 'scale':
                                self.sims[self.user]['scale'] = 1
                    if self.sims[self.user]['aoe'] == 'yes':
                        for targets in range(0, settings.SIMCRAFT_AOE_TARGETS):
                            targets += + 1
                            a_temp += 'enemy=target%s ' % targets
                        for key in self.sims[self.user]:
                            if key == 'enemy':
                                self.sims[self.user]['enemy'] = a_temp

                    os.makedirs(os.path.dirname(os.path.join(settings.SIMCRAFT_SIMS_DIR,
                                                             self.sims[self.user]['char'], 'test.file')),
                                exist_ok=True)
                    self.bot.loop.create_task(self.data_sim())
            except IndexError as e:
                await ctx.channel.send('Unknown command. Use !simc -h/help for commands')
                logger.info('No command given to bot.(ERR: %s)' % e)
                return


def setup(bot):
    bot.add_cog(Simulation(bot))
