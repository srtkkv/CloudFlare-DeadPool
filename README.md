# Infrastructure heartbeat (DeadPool)

![img](https://www.freeiconspng.com/thumbs/deadpool-icon-png/face-deadpool-icon-png-4.png)

## Getting started

Тула написана для интеграции с [CloudFlare Load Balancing](https://developers.cloudflare.com/load-balancing/) --> [Monitors ](https://developers.cloudflare.com/load-balancing/understand-basics/monitors/) которая выступает лакмусовой бумажкой работоспособности ДЦ, и позволит осуществлять автоматическое переключение клиентского траффика в случае отказа инфраструктурных компонентов датацентра (таких как ElasticSearch или Mongo DB.) Таким образом это позволит нам избежать 5XX ошибок у клиентов в связи с отказом компонентов DC.

Тула написана на Python с использованием Flask Framework и запускает 2 подпроцесса:

- `SpiderMan` -WEB сервер для ответов на запросы CloudFlare
- `WatchMan` - Процессы опроса инфраструктурных компонентов на их жизнеспособность (

## Configuration approach

```
  Generic:  # общие настройки
    log:  # Настройка серверов логировани (если параметры не настроены то логирует в syslog)
      type: gelf (покатолько gelf)
      server: localhost #gl.your.domain
      port: 12201
      level: debug
  WEB:  # настройки веб сервера отвечающего CF
    port: 9001  # 
    host: 0.0.0.0
    base_url: /
    access_token: WyI1NTE1MjhmNDMxY2Q3NTEwOTQxY2ZhYTgiLCI2Yjc4NTA4MzBlYzM0Y2NhZTdjZjIxNzlmZjhiNTA5ZSJd.B_bF8g.t1oUMxHr_fQfRUAF4aLpn2zjja0    #  Это Bearer  токен для осева лишних интересантов.
    name: "TEST SERVER"   # выдает в ответе свое имя.
  WatchMan:
    probe_status_folder: probe   #Где храним файлы-флаги недоступности инфра компонентов 
  probes: # Тут ведем перечень компонентов которые оправшиваем
   elastic:  # имя компонента
      module: url_probe  # модуль который будет опрашивать
      isEnabled: True  # выключатель
      period: 3 # периодичность опроса в секундах
      query: # что опрашиваем (описывается в формате модуля)
         url: 'http://localhost:9200/_cat/health' #"localhost:9200/_cluster/health?wait_for_status=yellow&timeout=50s&pretty"  # URL  к которому обращаемся
         header: {}  #с обращение передаем хедер
         query_type: get  # указываем тип запроса
         timeout: 2 # максимальное время ожидаем
      success_criteria: # раздел содержит критерии проверки полученного ответа
         body:  
            type: re_search  #применяется реЕксп по телу ответа
            query: 'elasticsearch+ green+'  #сам регэксп если есть вхождения то саксес
         status:
            type: status_in   #проверка на статут ответа
            query: [200]  # должен быть 200

```

## Принцип работы `SpiderMan`

При поступлении запроса на базовый URL

1. проверяем Bearer токен, если не правильный отдаем `511` и `Auth ERR`
2. идем в папку %probe_status_folder% и согласно перечню включенных Probe смотрим наличие файлов %probe_name%.dead:
   * если таковые с **ИМЕЮТСЯ**: отдаем перечень упавших сервисов и код ответа `503`
   * если таковых **НЕТ**: отдаем  `OK` и код ответа `200`

---

# Принцип работы `WatchMan`

Бежим по конфигурационному файлу по перечню WatchMan:probes и если проба включена (`isEnabled`):

1. берем название модуля и подгружаем его из папки mod
2. Запускаем в отдельном треде метод `Probe`  из данного модуля с переданным набором конфигрурации для данной Probe.
3. Модуль с полученными настройками уходит в бесконечный цикл опроса при котором он предварительно удаляет %probe_name%.dead если таковой существует.
4. В случае если модуль отваливается по TimeOut или ответ не соответсвует критерию создается файл %probe_name%.dead с содержимым ошибки.

##
