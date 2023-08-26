from flask import Flask, request
import yaml
import os
import threading
import importlib
import argparse
import logging
import sys
from logging_gelf.formatters import GELFFormatter
from logging_gelf.handlers import GELFTCPSocketHandler

#TODO_DONE Нужен логер
class WatchMan():
    """
    This class is working with probs and checks required systems for their health status.
    """

    def __init__(self,conf):
        self.WatchManCFG = conf.get('WatchMan')
        self.probes = conf.get('probes')
        self.logger =conf['Generic']['logger']
        self.logger.debug("Инициализация модулей")


    # TODO_DONE Импортнуть модули по списку проб
    # TODO_DONE запустить каждую пробу в отдельном треде
    def init_pobes(self):
        for probe  in self.probes:
            try:
                if self.probes[probe].get('isEnabled') or self.probes[probe].get('isEnabled') is None :
                    mod_name = self.probes[probe].get('module')
                    self.logger.info(f"Инициализация модуля:{mod_name} для опросника: {probe}")
                    self.probes[probe]["runner"] = importlib.import_module(f"mod.{mod_name}")  # подрубаем библиотеку
                    threading.Thread(target=lambda: self.probes[probe]["runner"] \
                                     .Probe(config={
                                                "probe_name": probe,
                                                "probe_cfg" : self.probes[probe],
                                                "watchman":self.WatchManCFG,
                                                "logger": self.logger,
                                                })
                                     .run() #.check()
                                     ).start() # запускаем в отельном поток
            except:
                self.logger.critical(f"Can't load and module: {self.probes[probe].get('module')}")


class SpiderMan():
    '''
    THis class is responding for external checker. This cluss is using probe_status_folder as state of infrastructure.
    '''
    def check4Dead(self):
        out = f"Server: {self.conf.get('WEB').get('name')} reports:\n"
        cnt=0
        for probe in self.conf.get('probes'):
            if self.conf['probes'][probe].get('isEnabled')  or self.conf['probes'][probe].get('isEnabled') is None:
                probe_file = os.path.join(
                                 self.conf.get('WatchMan').get('probe_status_folder'),
                                 probe+'.dead')
                if os.path.exists(probe_file):
                    cnt+=1
                    out+= f"The {probe} is DEAD!\n"
        if cnt >0:
            return out, 503

        return out + "OK",200
    def __init__(self, conf):
        self.conf = conf
        self.logger = self.conf['Generic']['logger']

    def runserver(self):
        app = Flask("DeadPool for Cloudflare")
        @app.route(self.conf.get('WEB').get('base_url',"/"))
        def index():
            if request.headers.get('Authorization') != "Bearer " +\
                    self.conf.get('WEB').get('access_token',"") \
                    and \
                    self.conf.get('WEB').get('access_token',"") != "":
                return "Auth ERR", 511

            return self.check4Dead()

        app.run(host=self.conf.get('WEB').get('host',"0.0.0.0"),
            port=self.conf.get('WEB').get('port',8080) ,
            debug=True,
            use_reloader=False
            )



def run():
    #Read Conf File
    parser = argparse.ArgumentParser(description='Provide Config before run.')
    parser.add_argument('-c','--config', type=str, help='Config  file (Default: config.yaml)', default="config.yaml")
    args = parser.parse_args()
    try:
        with open(args.config, 'r') as cfg:
            conf = yaml.full_load(cfg)
    except:
        print(f"Config file: {args.config}  has incorrect grammar!")
        exit(-1)

    ###INIT Logging
    log_level= {
        "info": logging.INFO,
        'debug':logging.DEBUG,
        'error':logging.ERROR,
        'critical': logging.CRITICAL,
        'fatal': logging.FATAL,
        'def':logging.ERROR
        }

    try:
        logger = logging.getLogger(conf['Generic']['log']['type'])
        logger.setLevel(log_level[str(conf.get('Generic', 'def').get('log', 'def').get('level', 'def')).lower()])

        handler = GELFTCPSocketHandler(
                    host=str(conf.get('Generic', 'gl-sb.corp.swiftcom.uk').get('log', 'gl-sb.corp.swiftcom.uk').get('server', 'gl-sb.corp.swiftcom.uk')),
                    port=conf.get('Generic', 12201).get('log', 12201).get('port', 12201))

        handler.setFormatter(GELFFormatter(null_character=True))
        logger.addHandler(handler)

    except KeyError as ke:
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.info("Log configuration empty or invalid..")

    try:
        conf['Generic']['logger'] = logger
    except KeyError:
        conf['Generic']= {}
        conf['Generic']['logger'] = logger

    ##RUN Threads with checker and web service
    try:


        threading.Thread(target=lambda: WatchMan(conf=conf).init_pobes()).start()
        logger.info("WatchMan started")

        #threading.Thread(target=lambda: SpiderMan(conf=conf).runserver()).start()
        SpiderMan(conf=conf).runserver()
        logger.info("Flask started")
    except threading.ThreadError as e:
        logging.FATAL(str(e))
    #w = WatchMan(conf=conf)

if __name__ == "__main__":
    run()