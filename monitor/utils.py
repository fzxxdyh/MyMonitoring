import hashlib
import os
import string
import random
# import redis
import pymysql
from DBUtils.PooledDB import PooledDB
from MyMonitoring import settings
import paramiko
import threading
import datetime
import subprocess

def get_encrypt_value(strings):
    '''
    for i in range(127):
        print(i, chr(i))
    a-z: 97-122,   A-Z:  65-90,  0-9: 48-57
    ord('a') --> 97
    chr(97)  --> 'a'
    '''
    if not strings.strip():
        return ""
    # letters = string.ascii_letters # 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    lowercase = string.ascii_lowercase # 'abcdefghijklmnopqrstuvwxyz'  取2个
    uppercase = string.ascii_uppercase # 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'  取2个
    digits = string.digits # '0123456789' 取2个
    punctuation = string.punctuation # '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~' 取2个
    enc_str = ''

    # 1、加8个随机字符串
    for i in range(2):# 小写、大写、数字、特殊字符都取2个，总共长度加8
        enc_str += random.choice(lowercase) + random.choice(uppercase) + random.choice(digits) + random.choice(punctuation)

    # 2、加上2位原字符串长度
    length =  len(strings) #原始字符串的长度
    if length < 10 and length > 0:
        s_len = "0" + str(length)  # 08、07 。。
    else:
        s_len = str(length)
    enc_str += s_len  #8位随机字符串+2位原字符长度，总计10位

    # 3、原字符串-4
    for i in strings:
        num = ord(i) - 4 #在原数值上减4
        enc_str += chr(num)

    # 4、补满50位
    str_box = string.ascii_letters + string.digits + string.punctuation #大小写+数字+符号
    for i in range(0, 50-length, 1):#range(start, stop[, step])
        enc_str += random.choice(str_box)
    return enc_str


def get_decode_value(strings):
    if not strings.strip():
        return ""
    length = int(strings[8:10]) #原始字符串长度
    sub_str = strings[10:length+10] #取中间部分
    dec_str = ''
    for i in sub_str:
        num = ord(i) + 4 #加回来
        dec_str += chr(num)
    return dec_str


def get_md5_value(strings):
    if strings:
        m = hashlib.md5(bytes('GgsDdu', encoding='utf-8'))
        m.update(bytes(strings, encoding='utf-8'))
        return m.hexdigest()


def rmdir_all(dirPath):
    if not os.path.isdir(dirPath):
        return

    for file in os.listdir(dirPath):
        filePath = os.path.join(dirPath, file)
        if os.path.isfile(filePath):
            os.remove(filePath)
        elif os.path.isdir(filePath):
            rmdir_all(filePath)

    for folder in os.listdir(dirPath):
        os.rmdir(os.path.join(dirPath, folder))


# def open_db_conn():
#     connect = pymysql.connect(host=settings.DATABASES['default']['HOST'], port=settings.DATABASES['default']['PORT'], database=settings.DATABASES['default']['NAME'], user=settings.DATABASES['default']['USER'],
#                               password=settings.DATABASES['default']['123456'], charset="utf8")
#
#     return connect


def open_db_pool(db_dict):
    POOL = PooledDB(
        creator=pymysql,  # 使用链接数据库的模块
        maxconnections=10,  # 连接池允许的最大连接数，0和None表示不限制连接数
        mincached=2,  # 初始化时，链接池中至少创建的空闲的链接，0表示不创建
        maxcached=5,  # 链接池中最多闲置的链接，0和None不限制
        maxshared=3,
        # 链接池中最多共享的链接数量，0和None表示全部共享。PS: 无用，因为pymysql和MySQLdb等模块的 threadsafety都为1，所有值无论设置为多少，_maxcached永远为0，所以永远是所有链接都共享。
        blocking=True,  # 连接池中如果没有可用连接后，是否阻塞等待。True，等待；False，不等待然后报错
        maxusage=None,  # 一个链接最多被重复使用的次数，None表示无限制
        setsession=[],  # 开始会话前执行的命令列表。如：["set datestyle to ...", "set time zone ..."]
        ping=0,
        # ping MySQL服务端，检查是否服务可用。# 如：0 = None = never, 1 = default = whenever it is requested, 2 = when a cursor is created, 4 = when a query is executed, 7 = always
        host=db_dict['HOST'],
        port=int(db_dict['PORT']), #必须是整数
        user=db_dict['USER'],
        password=db_dict['PASSWORD'],
        database=db_dict['NAME'],
        charset='utf8'
    )
    return POOL




def dateDiffInSeconds(date1, date2):
    '''求两个日期之间的秒数'''
    interval = date2 - date1
    return interval.days*24*3600 + interval.seconds


def ssh_cmd(script):#传入一个models.Script()实例
    cmd = '''tail -n 10 {logfile}|grep -w "{keyword}"|wc -l'''.format(logfile=script.logfile, keyword=script.ok_str)
    if script.host.ip == '127.0.0.1' or script.host.ip.upper() == "LOCALHOST":#1、本机
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        p.wait() #等待子进程结束
        for line in p.stderr.readlines():
            print('error:', line)
        out = p.stdout.read() # bytes类型
        count = out.decode("utf-8").strip() #如果执行过程异常，count=''
    else:#2、网络主机
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if script.host.private_key:
            keyfile = paramiko.RSAKey.from_private_key_file(script.host.private_key, password="123456") #如果证书有密码，则要填入
            ssh.connect(hostname=script.host.ip, port=script.host.port, username=script.host.username, pkey=keyfile, timeout=5)
        else:
            passwd = get_decode_value(script.host.password)
            try:
                ssh.connect(hostname=script.host.ip, port=script.host.port, username=script.host.username, password=passwd, timeout=5)
            except Exception as e:
                print('connect error:', e)

        stdin, stdout, stderr = ssh.exec_command(cmd)
        # ssh.close() # 不能现在关闭，否则后面拿不到数据

        for line in stderr.readlines():
            print('error:', line)

        count = stdout.read().decode("utf-8").strip() #stdout.read()返回bytes
        ssh.close()

    print('count:', count, type(count))
    if count and int(count) == 1:
        script.status = 0 #脚本执行成功
    else:
        script.status = 1 #脚本执行异常

    script.check_time = datetime.datetime.now()
    script.save()



POOL = open_db_pool(settings.DATABASES['default'])

if __name__ == "__main__":
    # pool = redis.ConnectionPool(host='10.10.10.2', port=6379, password='123456')
    # r = redis.Redis(connection_pool=pool)
    # pipe = r.pipeline(transaction=True)
    # print(dir(pipe))
    # pipe.set('aa', '199')
    # pipe.set('bb', '299')
    # #print(pipe.get('bb'))
    # pipe.execute()
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'monitor',
            'USER': 'root',
            'PASSWORD': '123456',
            'HOST': '127.0.0.1',
            'PORT': '7999',
        }
    }
    db_dict = DATABASES['default']
    pool = open_db_pool(db_dict)
    print(pool, type(pool), dir(pool))

    conn = pool.connection()
    cur = conn.cursor()
    cur.execute("select * from monitor_hostbase where id='10' ORDER BY update_time desc;")
    rows = cur.fetchall()
    print(rows)
    cur.close()
    conn.close()


