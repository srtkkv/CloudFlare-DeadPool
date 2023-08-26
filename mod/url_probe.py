import time
import os
import requests

class Probe():
    switcher = True
    ModuleName = "url_probe"
    config = {'module': 'url_probe',
              'config': None,
              'query': '',
              'period': 10,
              'runner': None,
              'basedir': 'probe'}
    prober = None
    req = {
        'get': requests.get,
        'post': requests.post
    }
    optimist=True

    def __init__(self, config:dict):
        self.config = config["probe_cfg"]
        self.config['probe_name'] = config["probe_name"]
        self.config['basedir'] = config["watchman"]['probe_status_folder']
        self.prober = os.path.join(self.config['basedir'],self.config['probe_name'])
        self.delay = self.config.get("period",10)
        self.logging = config['logger']
        pass
    def check_re_search(self, responce, creteria) -> bool:
        result = self.optimist
        import re
        pattern = re.compile(creteria)
        res = re.search(pattern=pattern, string=responce.text)
        return res


    def check_status_in(self,responce, criteria) -> bool:

        try:
            result = responce.status_code in criteria
        except:
            result = self.optimist
        return result

    def check_pass(self,responce, criteria) -> bool:
        return self.optimist
    def check(self):

        req = self.req[str(self.config['query']['query_type']).lower()]

        self.logging.debug("Request: "+ str(self.config["query"]["url"]))
        """
        ТУТ запрашиваем данные  по правилам которые 
        регулируются разделом конфига пробы: 'query'
        """
        try:
            res = req(self.config["query"]["url"],
                 headers=self.config["query"].get("header",None),
                 timeout=self.config["query"]["timeout"],)
            self.logging.debug(str(res.content) +  str(res.status_code))
        except Exception as err:
            #Ловим ошибку получения данных --> считаем что ресурс не доступен
            self.logging.error(err.__str__())
            self.logging.error(f"{self.config['probe_name']} marked as DEAD!")
            with open(self.prober+".dead", 'w') as dead:
                dead.writelines(err.__str__())
            return -1
        """
        далее делаем проверку по правилам описанных в разделе
        конфига пробы: Success_criteria
        """
        __criterias = {"re_search":self.check_re_search,
                       "status_in": self.check_status_in,
                       "pass":self.check_pass}

        if os.path.exists(self.prober+".dead"):
            os.remove(self.prober+".dead") # перед опросом удаляем
            self.logging.info('Delete old flagFile')

        for  chk in self.config["success_criteria"]: # Если какой то из критериев не прошел считаем мертвым
            if not __criterias[self.config["success_criteria"][chk].get('type',"pass")](res,self.config["success_criteria"][chk]['query']):
                with open(self.prober + ".dead", 'w') as dead:
                    dead.writelines(f"responce: " +
                                    str(res.text) +
                                    f"\n is not much to SUCCESS_CRITERIA: {chk} \n {self.config['success_criteria'][chk]} ")
                self.logging.debug(f"{self.config['probe_name']} with resp: {res.content} is not pass the criteria: {chk}")
                self.logging.error(f"{self.config['probe_name']} marked as DEAD!")

        pass

    def run(self):
        while self.switcher:
            if self.config.get('isEnabled',True):
                self.check()
            time.sleep(self.delay)
        pass