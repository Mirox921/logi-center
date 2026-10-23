"""Read-only environment checks and bounded, redacted operation logs."""
from pathlib import Path
import json,logging,logging.handlers,os,shutil
from execution import Fault,FaultCode,classify,redact
from i18n import tr as _

REMEDIES={
 FaultCode.DEVICE_UNSUPPORTED:('Устройство не поддерживает функцию','Выбери доступную функцию для этой модели.'),
 FaultCode.BACKEND_UNSUPPORTED:('Backend не поддерживает операцию','Проверь установленную версию backend и его возможности.'),

 FaultCode.MISSING:('Не установлен компонент','Установи пакет из репозитория своего дистрибутива.'),
 FaultCode.UNAVAILABLE:('Компонент установлен, но не работает','Проверь версию и зависимости компонента; попробуй запустить его отдельно.'),
 FaultCode.PERMISSION:('Нет доступа к устройству или программе','Переподключи устройство и проверь правила доступа из пакета backend. Не используй chmod 777.'),
 FaultCode.UNSUPPORTED:('Функция не поддерживается','Проверь возможности модели и версию backend.'),
 FaultCode.DISCONNECTED:('Устройство отключено','Подключи или включи устройство. Список обновится автоматически.'),
 FaultCode.TIMEOUT:('Истекло время ожидания','Проверь связь с устройством и повтори действие.'),
 FaultCode.CANCELLED:('Операция отменена','Состояние устройства изменилось или приложение закрывается.'),
 FaultCode.CONNECTION:('Ошибка связи с устройством или сервисом','Проверь, запущен ли нужный сервис, и подключено ли устройство.'),
 FaultCode.CONFIG:('Некорректная конфигурация','Проверь формат файла и совместимость с устройством.'),
 FaultCode.INTERNAL:('Внутренняя ошибка приложения','Сохрани диагностический отчёт и сообщи об ошибке.'),
}

def fault_for(error,component='application'):
    if isinstance(error,Fault):return error
    if isinstance(error,FileNotFoundError):return Fault(FaultCode.MISSING,component,'Component or file not found')
    if isinstance(error,PermissionError):return Fault(FaultCode.PERMISSION,component,'Access denied')
    if isinstance(error,(ValueError,KeyError,TypeError)):return Fault(FaultCode.CONFIG,component,redact(str(error)))
    if isinstance(error,TimeoutError):return Fault(FaultCode.TIMEOUT,component,'Operation timed out')
    return Fault(FaultCode.INTERNAL,component,type(error).__name__)

def describe(error):
    fault=fault_for(error);title,hint=REMEDIES[fault.code]
    return fault.component+' · '+_(title)+'\n'+_(hint)+('\n'+redact(fault.message) if fault.message else '')

class PrivateRotatingHandler(logging.handlers.RotatingFileHandler):
    def _open(self):
        return open(self.baseFilename,self.mode,encoding=self.encoding,errors=self.errors,
                    opener=lambda path,flags:os.open(path,flags,0o600))

class SafeLog:
    def __init__(self,path=None):
        self.path=Path(path) if path else Path.home()/'.local/state/logi-center/diagnostics.log'
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.logger=logging.Logger('logi-center-'+str(id(self)),level=logging.INFO)
        handler=PrivateRotatingHandler(self.path,maxBytes=128*1024,backupCount=2)
        os.chmod(self.path,0o600);handler.setFormatter(logging.Formatter('%(message)s'));self.logger.addHandler(handler)
    def fault(self,error):
        fault=fault_for(error)
        self.logger.info(json.dumps({'kind':'fault','component':redact(fault.component),'code':fault.code.value,'detail':redact(fault.message)},ensure_ascii=False))
    def operation(self,result):
        # Never log requested/actual values: button macros can contain sensitive text.
        self.logger.info(json.dumps({'kind':'operation','component':redact(result.component),'state':result.state.value,'source':result.source,'fault':result.fault.code.value if result.fault else None}))
    def close(self):
        for handler in list(self.logger.handlers):handler.close();self.logger.removeHandler(handler)

def collect(runner=None,which=None,sysfs='/sys/class/hidraw'):
    from backend import run,mouse_list
    runner=runner or run;which=which or shutil.which
    report=[]
    commands={'ratbagctl':['--version'],'solaar':['--version'],'pactl':['--version'],'easyeffects':['--version']}
    for component in ['ratbagctl','piper','solaar','headsetcontrol','easyeffects','pactl','parec','paplay']:
        if not which(component):
            fault=Fault(FaultCode.MISSING,component,'Required executable not found')
            report.append({'component':component,'state':fault.code.value,'description':describe(fault)});continue
        if component not in commands:
            report.append({'component':component,'state':'found','description':_('Программа найдена; аппаратные функции проверяются при использовании.')});continue
        try:
            output=runner([component,*commands[component]],timeout=5)
            version=' '.join(output.splitlines()[:2])[:160]
            report.append({'component':component,'state':'available','description':redact(version)})
        except Exception as error:
            fault=fault_for(error,component);report.append({'component':component,'state':fault.code.value,'description':describe(fault)})
    try:
        names=[name for device,name in mouse_list(runner(['ratbagctl','list'],timeout=8))]
        report.append({'component':'mouse','state':'connected' if names else 'disconnected','description':', '.join(names) or _('Поддерживаемая мышь не найдена.')})
    except Exception as error:
        fault=fault_for(error,'ratbagctl');report.append({'component':'mouse','state':fault.code.value,'description':describe(fault)})
    for node in Path(sysfs).glob('*'):
        try:text=(node/'device/uevent').read_text()
        except OSError:continue
        if '0000046D' not in text:continue
        permitted=os.access('/dev/'+node.name,os.R_OK|os.W_OK)
        report.append({'component':'Logitech HID access','state':'available' if permitted else 'permission_denied',
                       'description':_('Доступ к интерфейсу устройства есть.') if permitted else describe(Fault(FaultCode.PERMISSION,'HID','Device access denied'))})
    try:
        sources=json.loads(runner(['pactl','-f','json','list','sources'],timeout=8))
        physical=[s for s in sources if not s['name'].endswith('.monitor') and not s['name'].startswith('easyeffects_')]
        report.append({'component':'microphone','state':'available' if physical else 'disconnected','description':str(len(physical))+' '+_('доступных источников; запись не запускалась.')})
    except Exception as error:
        fault=fault_for(error,'pactl');report.append({'component':'microphone','state':fault.code.value,'description':describe(fault)})
    return report
