import time
import pymssql
import os
def Probe(*args,**kwargs):
    return MSSQL_Probe(*args,**kwargs)

class MSSQL_Probe():
    switcher = True
    optimist = True
    def __init__(self, config):
        self.config = config["probe_cfg"]
        self.config['probe_name'] = config["probe_name"]
        self.config['basedir'] = config["watchman"]['probe_status_folder']
        self.prober = os.path.join(self.config['basedir'], self.config['probe_name'])
        self.delay = self.config.get("period", 10)
        self.logging = config['logger']
        pass
    def check_exists(self, results, query:dict):
        for row in results:
            chk = True
            for q in query.keys():
                if row.get(q,None) != query[q]:
                    chk = False
                    break
            if chk:
                return chk

        return False
    def check_pass(self, results, query:dict):
        return self.optimist
    def check(self):
        print(__name__)
        #TODO запилить прием кредов из переменных
        try:
            conn = pymssql.connect(server=self.config['query'].get('server'),
                                   user=self.config['query'].get('user'),
                                   password=self.config['query'].get('pass'),
                                   database=self.config['query'].get('db_name'),
                                   port=self.config['query'].get('port'),
                                   )
            print("connected")
            cursor = conn.cursor(as_dict=True)
            cursor.execute(self.config['query']['query'])
            self.res = cursor.fetchall()
            print(self.res)

        except:
            with open(self.prober + ".dead", 'w') as dead:
                dead.writelines(f"""Can't connect to 
                    server:{self.config['query'].get('server')}
                    port: {self.config['query'].get('port')}
                    DB: {self.config['query'].get('db_name')}""")
            self.logging.debug(f"{self.config['probe_name']} connection fails to server: {self.config['query'].get('server')}")
            self.logging.error(f"{self.config['probe_name']} marked as DEAD!")
            return -1


        __criterias = {"exists": self.check_exists,
                       "pass": self.check_pass}
        if os.path.exists(self.prober+".dead"):
            os.remove(self.prober+".dead") # перед опросом удаляем
            self.logging.info('Delete old flagFile')

        for chk in self.config["success_criteria"]: # Если какой то из критериев не прошел считаем мертвым
            if not __criterias[self.config["success_criteria"][chk].get('type',"pass")](self.res,self.config["success_criteria"][chk]['query']):
                with open(self.prober + ".dead", 'w') as dead:
                    dead.writelines(f"responce: " +
                                    str(self.res) +
                                    f"\n is not much to SUCCESS_CRITERIA: {chk} \n {self.config['success_criteria'][chk]} ")
                self.logging.debug(f"{self.config['probe_name']} with resp: {str(self.res)} is not pass the criteria: {chk}")
                self.logging.error(f"{self.config['probe_name']} marked as DEAD!")

        pass

    pass

    def run(self):
        while self.switcher:
            if self.config.get('isEnabled',True):
                self.check()

            time.sleep(self.delay)
