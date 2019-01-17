#! coding: utf-8


import configparser
import pymysql
# import schedule
import psutil
import platform
import datetime
import time
import os
import sys
import threading
# import signal
import logging
import subprocess

class Collect:
    '''数据采集'''
    def __init__(self, config_file):
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_file) # 如果config_file之前就是绝对路径，os.path.join不会做拼接操作
        self.conf = configparser.ConfigParser()
        self.conf.read(self.config_file, encoding="utf-8")
        self.ip = self.conf.get('database', 'ip')
        self.port = self.conf.get('database', 'port')
        self.dbname = self.conf.get('database', 'dbname')
        self.user = self.conf.get('database', 'user')
        self.passwd = self.conf.get('database', 'passwd')
        self.local_ip = self.conf.get('localhost', 'local_ip')  #本地IP
        self.can_del_history_data = self.conf.get('localhost', 'can_del_history_data')  #是否能删除数据
        self.del_data_interval = eval(self.conf.get('localhost', 'del_data_interval'))
        self.logfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.conf.get('localhost', 'logfile'))
        self.logerror = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.conf.get('localhost', 'logerror'))

        self.base_check_interval = eval(self.conf.get('HostBase', 'check_interval'))
        self.performance_check_interval = eval(self.conf.get('HostPerformance', 'check_interval'))
        self.performance_data_keep_time = eval(self.conf.get('HostPerformance', 'data_keep_time'))

        # self.userkeys = self.conf.options("Userkey") #返回的是一个列表，只返回选项


    def open_db_conn(self):
        '''
        注意：如果长时间不操作，连接会被mysql断开，程序报错：
        ERROR (2006, "MySQL server has gone away (BrokenPipeError(32, 'Broken pipe'))")
        mysql> show variables like '%timeout%';
+-----------------------------+----------+
| Variable_name               | Value    |
+-----------------------------+----------+
| connect_timeout             | 10       |
| delayed_insert_timeout      | 300      |
| have_statement_timeout      | YES      |
| innodb_flush_log_at_timeout | 1        |
| innodb_lock_wait_timeout    | 50       |
| innodb_rollback_on_timeout  | OFF      |
| interactive_timeout         | 28800    |
| lock_wait_timeout           | 31536000 |
| net_read_timeout            | 30       |
| net_write_timeout           | 60       |
| rpl_stop_slave_timeout      | 31536000 |
| slave_net_timeout           | 60       |
| wait_timeout                | 28800    |
+-----------------------------+----------+
13 rows in set (0.00 sec)

mysql>
        :return:
        '''
        connect = pymysql.connect(host=self.ip, port=int(self.port), database=self.dbname, user=self.user, password=self.passwd, charset="utf8")
        # cursor = conn.cursor()
        # print('新建了一个db连接, conn id:',  id(connect))
        return connect

    def dateDiffInSeconds(self, date1, date2):
        '''求两个日期之间的秒数'''
        interval = date2 - date1
        return interval.days * 24 * 3600 + interval.seconds

    def get_os_release(self):
        return platform.system()

    def get_cpu_num(self):
        return psutil.cpu_count()

    def get_cpu_used_rate(self):
        return psutil.cpu_percent() #当前CPU使用率，非阻塞返回

    def get_memory_total(self):
        return psutil.virtual_memory().total #和free有偏差

    def get_memory_used_rate(self):
        return psutil.virtual_memory().percent

    def get_swap_total(self):
        return psutil.swap_memory().total

    def get_swap_used_rate(self):
        return psutil.swap_memory().percent

    def get_disk_total(self):
        total = 0 #所有磁盘总大小
        partitions = psutil.disk_partitions() #返回的是一个列表
        for part in partitions:
            if "rw" in part.opts: #是可读写的盘，否则psutil.disk_usage(光盘) Windows下会报错
                mountpoint = part.mountpoint #返回挂载点，比如 /  /home
                disk_info = psutil.disk_usage(mountpoint) #mountpoint是必传的参数, Windows下光盘会报错
                total += disk_info.total  #字节
        return total

    def get_disk_used_rate(self):
        total = 0 #所有磁盘总大小
        used = 0 #已用大小
        partitions = psutil.disk_partitions() #返回的是一个列表
        for part in partitions:
            if "rw" in part.opts:  # 是可读写的盘，否则psutil.disk_usage(光盘) Windows下会报错
                mountpoint = part.mountpoint #返回挂载点，比如 /  /home
                disk_info = psutil.disk_usage(mountpoint) #mountpoint是必传的参数
                total += disk_info.total  #字节
                used += disk_info.used   #字节
        return round(used*100/total, 2)  #百分比

    def get_io_bytes_sent(self):
        return psutil.net_io_counters().bytes_sent

    def get_io_bytes_recv(self):
        return psutil.net_io_counters().bytes_recv


    def get_hostbase(self):
        conn = self.open_db_conn()
        cur = conn.cursor()
        hostbase_info = {}

        cur.execute('''select COLUMN_NAME from information_schema.columns where TABLE_NAME="monitor_hostbase" ''')

        all_rows = cur.fetchall()
        #元组:(('id',), ('ip',), ('update_time',), ('cpu_used_rate',), ('memory_used_rate',), ('disk_used_rate',), ('swap_used_rate',), ('io_bytes_sent',), ('io_bytes_recv',))

        sql = "delete from monitor_hostbase where ip='%s'" % self.local_ip
        cur.execute(sql) #开始前执行一遍删除
        conn.commit()
        cur.close()
        conn.close()
        print('get_hostbase,删除了多少行:',cur.rowcount, sql)
        update_flag = False #后面第一次用insert,以后用update

        try:
            while True:
                # 超过一定时间，mysql会将连接断开
                conn = self.open_db_conn()
                cur = conn.cursor()
                #update_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                update_time = datetime.datetime.now()
                print(update_time, "get_hostbase starting")
                # for field in HostBase._meta.get_fields(): # 获取django model 所有字段的方法
                #     field_name = field.name
                for row in all_rows:
                    field_name = row[0]
                    if field_name not in ["id", "ip", "update_time", "note"]:#这四个字段没有对应的方法
                        hostbase_info[field_name] = getattr(self, 'get_%s' % field_name)() #反射，最后的括号表示执行方法

                # cur.execute('select count(1) from monitor_hostbase where ip=self.local_ip') #  ((3423,),) 或  ((0,),)
                # counts = cur.fetchall()[0][0] #第一个0表示结果集的第一行,第二个0表示第一行的第一个字段

                if update_flag:#0行或多行
                    sql = '''update monitor_hostbase set update_time='%s', os_release='%s',  \
                            cpu_num=%d,  memory_total=%d,  disk_total=%d, swap_total=%d  where ip='%s' ''' % \
                          (update_time, hostbase_info['os_release'], hostbase_info['cpu_num'], hostbase_info['memory_total'], hostbase_info['disk_total'], hostbase_info['swap_total'], self.local_ip)

                else:
                    sql = '''insert into monitor_hostbase(ip, update_time, os_release, cpu_num, memory_total, disk_total, swap_total) values('%s', '%s', '%s', %d, %d, %d, %d)''' % \
                          (self.local_ip, update_time, hostbase_info['os_release'], hostbase_info['cpu_num'],
                           hostbase_info['memory_total'], hostbase_info['disk_total'], hostbase_info['swap_total'])
                    update_flag = True #以后就用update

                #print("sql:", sql)
                cur.execute(sql)
                conn.commit()
                cur.close()
                conn.close()
                #print("base end:", datetime.datetime.now())
                #print("how long base sleep?", float(self.base_check_interval))
                if float(self.base_check_interval) < 3600:
                    self.base_check_interval = 3600
                time.sleep(float(self.base_check_interval))

        except Exception as e:
            print("ERROR: get_hostbase, ", e)
            logging.error(e)
            cur.close()
            conn.close()
            os._exit(1)



    def get_hostperformance(self):#传一个conn、cur进来，免得每次请求一个DB连接
        conn = self.open_db_conn()
        cur = conn.cursor()

        hostbase_info = {}
        cur.execute('''select COLUMN_NAME from information_schema.columns where TABLE_NAME="monitor_hostperformance" ''')
        all_rows = cur.fetchall()

        try:
            while True:
                update_time = datetime.datetime.now()
                print(update_time, "get_hostperformance starting")
                # print(all_rows)
                # for field in HostBase._meta.get_fields(): # 获取django model 所有字段的方法
                #     field_name = field.name
                for row in all_rows:
                    field_name = row[0]
                    if field_name not in ["id", "ip", "update_time", "io_sent_kbs", "io_recv_kbs"]:#这五个字段没有对应的方法
                        hostbase_info[field_name] = getattr(self, 'get_%s' % field_name)() #反射，最后的括号表示执行方法
                # print(hostbase_info)

                #计算IO速率
                sql = '''select update_time, io_bytes_sent, io_bytes_recv from  monitor_hostperformance where ip="{ip}" and update_time=(select max(update_time) from monitor_hostperformance where ip="{ip}")  '''.format(ip=self.local_ip)
                cur.execute(sql)
                # (datetime.datetime(2018, 12, 4, 18, 34, 11, 382600), 224583565, 547297414)
                pre_row = cur.fetchone() #返回一个一维元组，如果是fetchall则返回二维元组
                if pre_row:#上面找不到就返回一个None类型，如果是fetchall则返回空的元组()
                    interval = self.dateDiffInSeconds(pre_row[0], update_time) #小的时间在前面，返回两个时间的秒数
                    io_sent_kbs = round((hostbase_info['io_bytes_sent'] - pre_row[1]) / interval / 1024, 2) #单位KB/s
                    io_recv_kbs = round((hostbase_info['io_bytes_recv'] - pre_row[2]) / interval / 1024, 2) #单位KB/s
                else:#没找到，有可能是第一次插入
                    io_sent_kbs = 0
                    io_recv_kbs = 0

                #print("io_sent_kbs, io_recv_kbs", io_sent_kbs, io_recv_kbs)
                sql = '''insert into monitor_hostperformance(ip, update_time, cpu_used_rate, memory_used_rate, disk_used_rate, swap_used_rate, io_bytes_sent, io_bytes_recv, io_sent_kbs, io_recv_kbs) values('%s', '%s', %f, %f, %f, %f, %d, %d, %f,%f)''' % \
                      (self.local_ip, update_time, hostbase_info['cpu_used_rate'], hostbase_info['memory_used_rate'],hostbase_info['disk_used_rate'], hostbase_info['swap_used_rate'],hostbase_info['io_bytes_sent'], hostbase_info['io_bytes_recv'],
                       io_sent_kbs, io_recv_kbs
                       )
                #print("sql:", sql)
                cur.execute(sql)
                conn.commit()
                #print("performance end:", datetime.datetime.now())
                #print("how long performance sleep?", float(self.performance_check_interval))
                if float(self.performance_check_interval) < 30:
                    self.performance_check_interval = 30 #30秒
                time.sleep(float(self.performance_check_interval))
                #print("performance time sleep end:", datetime.datetime.now())
        except Exception as e:
            print("ERROR: get_hostperformance, ", e)
            logging.error(e)
            cur.close()
            conn.close()
            os._exit(1)

    # def create_test_data(self):
    #     conn = self.open_db_conn()
    #     cur = conn.cursor()
    #     now = datetime.datetime.now()
    #     for i in range(200):
    #         update_time = now - datetime.timedelta(days=i)
    #         # print(now, update_time)
    #         sql = "insert into monitor_hostbase(update_time) values('%s')" % update_time
    #         cur.execute(sql)
    #         sql = "insert into monitor_hostperformance(update_time) values('%s')" % update_time
    #         cur.execute(sql)
    #     conn.commit()
    #     cur.close()
    #     conn.close()

    def get_userkey(self):
        conn = self.open_db_conn()
        cur = conn.cursor()
        hostbase_info = {}
        ip = self.local_ip
        try:
            while True:
                update_time = datetime.datetime.now()
                print(update_time, "get_userkey starting")
                for key, expre in self.conf.items("Userkey"):
                    sub_obj = subprocess.Popen(expre, shell=True, stdout=subprocess.PIPE)
                    sub_obj.wait()
                    value = sub_obj.stdout.read().strip()
                    hostbase_info[key] = float(value)
                    # print(hostbase_info)
                    sql = '''insert into monitor_userkey(ip, update_time, keyname, keyvalue, keyexp) values('%s', '%s', '%s', %f, '%s')''' % \
                      (ip, update_time, key, hostbase_info[key], expre)
                    # print("sql:", sql)
                    cur.execute(sql)
                conn.commit()
                if float(self.performance_check_interval) < 30:
                    self.performance_check_interval = 30 #10秒
                time.sleep(float(self.performance_check_interval))

        except Exception as e:
            print("ERROR: get_userkey ,", e)
            logging.error(e)
            cur.close()
            conn.close()
            os._exit(1)

    def del_history_data(self):
        try:
            while True:
                # 对于长时连接，每次新建
                conn = self.open_db_conn()
                cur = conn.cursor()
                now_time = datetime.datetime.now()
                print(now_time, "del_history_data starting")

                performance_time = now_time - datetime.timedelta(days=self.performance_data_keep_time)

                # 1、删除monitor_userkey过期数据
                sql = '''delete from monitor_userkey where update_time < '%s'; ''' % performance_time
                cur.execute(sql)
                # 2、删除monitor_hostperformance过期数据
                sql = '''delete from monitor_hostperformance where update_time < '%s'; ''' % performance_time
                cur.execute(sql)
                conn.commit()
                cur.close()
                conn.close()
                if float(self.del_data_interval) < 3600:
                    self.del_data_interval = 3600
                time.sleep(float(self.del_data_interval)) #清除数据间隔
        except Exception as e:
            print("Error: del_history_data ,", e)
            logging.error(e)
            cur.close()
            conn.close()
            os._exit(1)





    def send_mail(self, hosthistory=None):
        import smtplib
        from email.mime.text import MIMEText
        from email.header import Header
        print("开始发邮件" )
        sender = 'xxxxxxxx@qq.com'  # 发件人
        passwd = 'passwordxxxx'  # smtp授权码
        receiver = ['xxxxxxxx@qq.com', ]  # 列表，收件人

        if hosthistory:
            if hosthistory.rule:
                if ":" in hosthistory.rule.keyname:
                    rule_name = hosthistory.rule.keyname.split(":")[1] #用户自定义key
                else:
                    rule_name = hosthistory.rule.keyname #系统key
            else:
                rule_name = "agent"
            if hosthistory.event_type == 0:
                topic = "恢复:%s %s" % (hosthistory.ip, rule_name)
            else:
                topic = "告警:%s %s" % (hosthistory.ip, rule_name)
            sendmail = models.SendMail(sender=sender, receiver=str(receiver), topic=topic, content=topic, event_time=hosthistory.event_time, ip=hosthistory.ip)
            sendmail.save()
            hosthistory.mail = sendmail
            hosthistory.save()
        else:
            topic = "测试邮件"


        msg = MIMEText(topic, 'plain', 'utf-8')  # 邮件正文
        msg['Subject'] = Header(topic, "utf-8")  # 邮件主题

        # msg["From"] 与 msg["To"] 可省略不写，则别名显示为空<>
        msg['From'] = Header("监控邮件发送", "utf-8")  # 发件人别名
        msg['To'] = Header("监控邮件接收", "utf-8")  # 收件人别名

        server = smtplib.SMTP_SSL("smtp.qq.com", 465)  # 发件人邮箱中的SMTP服务器，端口是465
        server.login(sender, passwd)  # 括号中对应的是发件人邮箱账号、授权码
        server.sendmail(sender, receiver, msg.as_string())  # 括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
        server.quit()  # 关闭连接
        print("已发送邮件：%s" % topic)

    def check_host_alived(self, host):
        '''检查主机是否存活'''
        print("check_host_alived starting")
        update_time_dic = models.HostPerformance.objects.filter(ip=host.ip).aggregate(max_update_time=Max('update_time')) #找不到ip不会报错，返回{'max_update_time': None}
        if update_time_dic['max_update_time']:#不为空
            if not host.update_time:
                host.update_time = update_time_dic['max_update_time']

            warn_list = models.Warning.objects.filter(ip=host.ip, state=-1)  # 是一个列表
            if warn_list and host.update_time < update_time_dic['max_update_time']:# 1、无响应---》响应
                host.update_time = update_time_dic['max_update_time']
                host.save()
                for warn in warn_list:#正常情况下只有一个
                    warn.delete()
                hosthistory = models.HostHistory(ip=host.ip, event_time=update_time_dic['max_update_time'],event_type=0, rule=None, keyvalue=None, mail=None)
                hosthistory.save()
                self.send_mail(hosthistory)
                print("主机状态：1、无响应---》响应 %s" % host.ip)
                return True

            elif warn_list and host.update_time >= update_time_dic['max_update_time']:# 2、无响应---》无响应
                for warn in warn_list:#正常情况下只有一个
                    warn.counts += 1  # 次数加1
                    warn.save()
                print("主机状态：2、无响应---》无响应 %s" % host.ip)
                return False

            elif not warn_list and host.update_time < update_time_dic['max_update_time']:# 3、响应---》响应
                host.update_time = update_time_dic['max_update_time']
                host.save()
                print("主机状态：3、响应---》响应 %s " % host.ip)
                return True

            elif not warn_list and host.update_time >= update_time_dic['max_update_time']:# 4、响应---》无响应

                now_time = datetime.datetime.now()
                warn = models.Warning(ip=host.ip, rule_id=None, counts=1, event_time=now_time, state=-1)
                warn.save()
                hosthistory = models.HostHistory(ip=host.ip, event_time=now_time, event_type=1, rule=None,keyvalue=None, mail=None)
                hosthistory.save()
                self.send_mail(hosthistory)
                print("主机状态：4、响应---》无响应 %s" % host.ip)
                return False

        return False


    def check_host_rules(self):
        # performance_key = ['cpu_used_rate', 'memory_used_rate', 'disk_used_rate', 'swap_used_rate']
        try:
            while True:
                now_time = datetime.datetime.now()
                print(now_time, "check_host_rules starting")
                # 1、检查主机rule
                hosts = models.Host.objects.exclude(state=2) #不等于2，不处于维护状态
                for host in hosts:
                    if self.check_host_alived(host):#在性能表中一定能找到该主机
                        rules = host.rules.all()
                        for rule in rules:
                            if ":" not in rule.keyname:#系统性能key
                                update_time_dic = models.HostPerformance.objects.filter(ip=host.ip).aggregate(max_update_time=Max('update_time'))  # 找不到ip不会报错，返回{'max_update_time': None}
                                row = models.HostPerformance.objects.filter(ip=host.ip, update_time=update_time_dic["max_update_time"])[0]  # 位置1
                                # print(rule.keyname, len(rule.keyname), "测试4444")
                                value = getattr(row, rule.keyname) #用反射
                            else:#用户自定义key
                                keyname = rule.keyname.split(":")[1] # 格式 ip:keyname
                                update_time_dic = models.Userkey.objects.filter(ip=host.ip, keyname=keyname).aggregate(max_update_time=Max('update_time'))  # 找不到不会报错，返回{'max_update_time': None}
                                # print(update_time_dic, "测试这里", host.ip, keyname, ) # 测试这里
                                row = models.Userkey.objects.filter(ip=host.ip, keyname=keyname, update_time=update_time_dic["max_update_time"] )[0]  # 位置2
                                value = row.keyvalue #无需反射

                            exp = "(%f %s %f)" % (float(value), rule.get_symbol_display(), float(rule.keyvalue))#现在是否到达阀值
                            warn_list = models.Warning.objects.filter(ip=host.ip, rule_id=rule.id)  # 查找故障表里有没有
                            if warn_list and eval(exp):#1、故障-->故障
                                warn = warn_list[0]
                                warn.counts += 1
                                warn.event_time = row.update_time
                                warn.save()
                                if warn.state == 0 and warn.counts >= rule.counts:#
                                    warn.state = 1
                                    warn.save()
                                    hosthistory = models.HostHistory(ip=host.ip,event_time=update_time_dic['max_update_time'],event_type=1, rule=rule, keyvalue=value,mail=None)
                                    hosthistory.save()
                                    self.send_mail(hosthistory)

                            elif not warn_list and eval(exp):# 2、正常 --> 故障
                                if rule.counts == 1:
                                    warn = models.Warning(ip=host.ip, rule_id=rule.id, counts=1, event_time=update_time_dic['max_update_time'], state=1)
                                    warn.save()
                                    hosthistory = models.HostHistory(ip=host.ip,event_time=update_time_dic['max_update_time'],event_type=1, rule=rule, keyvalue=value,mail=None)
                                    hosthistory.save()
                                    self.send_mail(hosthistory)
                                else:
                                    warn = models.Warning(ip=host.ip, rule_id=rule.id, counts=1, event_time=update_time_dic['max_update_time'], state=0)
                                    warn.save()
                            elif warn_list and not eval(exp):#3、故障---》正常
                                for warn in warn_list:#正常情况只有一条
                                    warn.delete()
                                hosthistory = models.HostHistory(ip=host.ip,event_time=update_time_dic['max_update_time'],event_type=0, rule=rule, keyvalue=value,mail=None)
                                hosthistory.save()
                                self.send_mail(hosthistory)

                            else:#没有， 4、正常 --》 正常
                                pass



                    # 无论Host是否存活
                    print("更新host表")
                    update_time_dic = models.HostPerformance.objects.filter(ip=host.ip).aggregate(max_update_time=Max('update_time'))  # 找不到ip不会报错，返回{'max_update_time': None}
                    if update_time_dic["max_update_time"] and host.update_time < update_time_dic["max_update_time"]:
                        host.update_time = update_time_dic["max_update_time"]
                        host.save()

                    if host.state == 0 and models.Warning.objects.filter(ip=host.ip).exclude(state=0):#排除state=0
                        host.state = 1 #告警
                        host.save()
                    elif host.state == 1 and ( not models.Warning.objects.filter(ip=host.ip).exclude(state=0)  ):
                        host.state = 0
                        host.save()

                # 2、查找是否有新增主机
                '''
                >>> models.HostPerformance.objects.values("ip").distinct()
                <QuerySet [{'ip': '10.10.10.2'}, {'ip': '10.10.10.3'}]>
                >>>
                >>> models.HostPerformance.objects.values_list("ip").distinct()
                <QuerySet [('10.10.10.2',), ('10.10.10.3',)]>
                >>>
                '''
                ips = models.HostPerformance.objects.values_list('ip').annotate(update_time=Max("update_time"))
                # print(ips.query)
                # print(ips)
                for row in ips:
                    ip, update_time = row[0], row[1]
                    # print(row)
                    if not models.Host.objects.filter(ip=ip):
                        host = models.Host(ip=ip, state=0, update_time=update_time, note=None)
                        host.save()

                # 3、 sleep，

                time.sleep(200)


        except Exception as e:
            print("ERROR: check_host_rules ,", e)
            logging.error(e)
            os._exit(1)





def monitorClient(collect):
    print("monitorClient starting!")
    if platform.system() == 'Linux':
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
        #os.chdir('/') #修改工作目录
        os.setsid() #设置新的会话连接
        os.umask(0) #重新设置文件创建权限
        pid = os.fork()
        if pid > 0:
            sys.exit(0)

    sys.stdout.flush()
    sys.stderr.flush()

    #如果程序有stdout、stderr一定要写入文件或写入os.devnull，不能在终端打印，因为deamon是没有终端的，找不到输出的容量，daemon进程会直接退出
    si = open(os.devnull, 'r')
    so = open(collect.logfile, 'a+')
    se = open(collect.logerror, 'a+')

    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())




    LOG_FORMAT = "%(asctime)s %(module)s %(funcName)s %(lineno)d %(levelname)s %(message)s"  # 配置输出日志格式
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S %a'  # 配置输出时间的格式，注意月份和天数不要搞乱了

    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, datefmt= DATE_FORMAT, filename=collect.logerror, ) #只记录异常日志
    logging.FileHandler(collect.logerror, encoding="utf-8")
    # check.create_test_data()
    # check.del_history_data()

    # 当有多个任务时，执行时间互不影响，猜测schedule.run_pending()应该使用了多进程或多线程
    # 两次执行的真正间隔时间 = 任务的执行时间 +　设置的间隔时间
    # schedule.every(check.base_check_interval).seconds.do(check.get_hostbase, conn, cur1)  # 真正产生的间隔时间15秒 = 10 + time.sleep(5)
    # schedule.every(check.performance_check_interval).seconds.do(check.get_hostperformance, conn, cur2)  # 真正产生的间隔时间30秒 = 20 + time.sleep(10)
    # schedule.every(1).days.do(check.del_history_data)  # 每天执行
    # while True:
    #     schedule.run_pending()

    # thread_list = []
    # t1 = threading.Thread(target=check.get_hostbase, args=(conn1, cur1))
    # t2 = threading.Thread(target=check.get_hostperformance, args=(conn2, cur2))
    # # thread_list.append(t1)
    # # thread_list.append(t2)
    # t1.start()
    # t2.start()


    t1 = threading.Thread(target=collect.get_hostbase, name="t_get_hostbase")
    t2 = threading.Thread(target=collect.get_hostperformance, name="t_get_hostperformance")
    t3 = threading.Thread(target=collect.get_userkey, name="get_userkey")
    t1.start()
    t2.start()
    t3.start()
    if collect.can_del_history_data.upper() == "TRUE":
        t4 = threading.Thread(target=collect.del_history_data, name="del_history_data")
        t4.start()




    # g1 = gevent.spawn(check.get_hostbase, conn1, cur1)
    # g2 = gevent.spawn(check.get_hostperformance, conn2, cur2)
    # g1.start()
    # g2.start()
    # g1.join()
    # g2.join()


def monitorServer(collect):
    print('monitorServer starting!')
    t5 = threading.Thread(target=collect.check_host_rules, name="check_host_rules")
    t5.start()



if __name__ == "__main__":
    # import gevent
    # from gevent import monkey
    # monkey.patch_all()

    # 定点执行
    # now_time = datetime.datetime.now()
    # run_str = '''%d-%d-%d 10:00:00''' % (now_time.year, now_time.month, now_time.day)
    # run_time = datetime.datetime.strptime(run_str, "%Y-%m-%d %H:%M:%S")
    # interval = run_time - now_time
    # if run_time < now_time:
    #     wait_time = interval.days*24*3600 + interval.seconds + 24*3600
    # else:
    #     wait_time = interval.days*24*3600 + interval.seconds
    # time.sleep(wait_time)

    print("main starting!")
    config_file = "config.ini"
    collect = Collect(config_file)
    if len(sys.argv) == 2:
        if sys.argv[1].upper() == "CLIENT":#客户端角色
            monitorClient(collect)
        elif sys.argv[1].upper() == "SERVER":#服务端角色
            import django
            from django.db.models import Max
            import os
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyMonitoring.settings')
            django.setup()
            from monitor import models

            monitorClient(collect)
            time.sleep(10)
            monitorServer(collect)
        else:
            print("Usage: python3 %s server|client" % sys.argv[0])
    else:
        print("Usage: python3 %s server|client" % sys.argv[0])
    print("main end")
