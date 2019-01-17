from django.db import models

# Create your models here.

class User(models.Model):
    '''用户表'''
    username = models.CharField(max_length=32,unique=True)
    password = models.CharField(max_length=32)
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name ="用户表"
        verbose_name_plural ="用户表"

class Host(models.Model):
    '''主机状态表'''
    ip = models.CharField(max_length=15, null=True, blank=True, unique=True) #唯一
    rules = models.ManyToManyField("Rules")
    '''
    当Warning表中没有该主机记录，则state为OK，否则state为告警
    '''
    state_choices = ((0, 'OK'),(1, '告警'), (2, '维护'))
    state = models.SmallIntegerField(choices=state_choices, default=0) #通过orm操作时，default属性生效，通过SQL操作时，default无效，
    # 通过show create table monitor_d 查看，state字段是没有默认值的
    update_time = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=30, null=True, blank=True, default=None)

    def __str__(self):
        return self.ip

class HostBase(models.Model):
    '''主机配置信息表'''
    ip = models.CharField(max_length=15, null=True, blank=True, unique=True) #唯一
    update_time = models.DateTimeField(null=True, blank=True)
    os_release = models.CharField(max_length=20, null=True, blank=True)
    cpu_num = models.SmallIntegerField(null=True, blank=True) # cpu核数
    memory_total = models.BigIntegerField(null=True, blank=True) #内存/GB
    disk_total = models.BigIntegerField(null=True, blank=True) #磁盘容量 /GB
    swap_total = models.BigIntegerField(null=True, blank=True) #内存/GB


    def __str__(self):
        return self.ip

    class Meta:
        verbose_name ="主机基本表"
        verbose_name_plural ="主机基本表"

class HostPerformance(models.Model):
    '''主机性能数据表'''
    ip = models.CharField(max_length=15, null=True, blank=True)
    update_time = models.DateTimeField(null=True, blank=True)
    cpu_used_rate = models.FloatField(null=True, blank=True)
    memory_used_rate = models.FloatField(null=True, blank=True)
    disk_used_rate = models.FloatField(null=True, blank=True)
    swap_used_rate = models.FloatField(null=True, blank=True)
    io_bytes_sent = models.BigIntegerField(null=True, blank=True)
    io_bytes_recv = models.BigIntegerField(null=True, blank=True)
    io_sent_kbs = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) #保留两位小数
    io_recv_kbs = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)


    def __str__(self):
        return self.ip

    class Meta:
        verbose_name ="主机性能表"
        verbose_name_plural ="主机性能表"

class Userkey(models.Model):
    '''用户自定义检查key'''
    ip = models.CharField(max_length=15, null=True, blank=True)
    update_time = models.DateTimeField(null=True, blank=True)
    keyname = models.CharField(max_length=30, null=True, blank=True)
    keyvalue = models.IntegerField()
    keyexp = models.CharField(max_length=200, null=True, blank=True)



    def __str__(self):
        return self.ip + '-' + self.keyname


    class Meta:
        verbose_name ="用户key"
        verbose_name_plural ="用户key"
        unique_together=(("ip", "keyname", "update_time"),) #联合唯一


class Rules(models.Model):
    '''报警规则表'''
    keyname = models.CharField(max_length=50)
    symbol_choices = ((0, '=='), (3, '>'), (2, '>='), (-3, '<'), (-2, '<='), (-1, '!=') )
    symbol = models.SmallIntegerField(choices=symbol_choices)
    keyvalue = models.FloatField() # 触发的阀值
    counts = models.SmallIntegerField() #连续出现的次数

    def __str__(self):
        return self.keyname

    class Meta:
        unique_together = ('keyname', 'symbol', 'keyvalue', 'counts') #联合唯一

    def __str__(self):
        return self.keyname

class HostHistory(models.Model):
    '''主机事件历史'''
    ip = models.CharField(max_length=15, null=True, blank=True)
    event_time = models.DateTimeField(null=True, blank=True) #等于userkey.update_time或 HostPerformance.update_time
    event_choices = ((0, '恢复'),(1, '告警'))
    event_type = models.SmallIntegerField(choices=event_choices)
    rule = models.ForeignKey("Rules", on_delete=models.CASCADE, null=True, blank=True)
    keyvalue = models.FloatField(null=True, blank=True, default=None)
    mail = models.OneToOneField("SendMail", null=True, blank=True, default=None) #一对一

class Warning(models.Model):
    '''告警表'''

    def __doc__(self):
        msg = '''
        当主机触发一条告警，便在该表插入一条rule id, 已存在则忽略
        当主机恢复一条告警，便在该表删除一条记录
        '''
        return msg

    ip = models.CharField(max_length=15, null=True, blank=True)
    rule_id = models.IntegerField(null=True, blank=True, default=None)
    counts = models.SmallIntegerField(null=True, blank=True)  # 实际发生的次数，和Rules中的字段counts意义不同
    event_time = models.DateTimeField(null=True, blank=True)
    state_choices = ((0, '未达告警次数'),(1, '已达告警次数'), (-1, 'agent无响应'))
    state = models.SmallIntegerField(choices=state_choices , default=0)
    def __str__(self):
        return self.ip

    class Meta:
        unique_together = (("ip", "rule_id"),)

class SendMail(models.Model):
    sender = models.CharField(max_length=50)
    receiver = models.CharField(max_length=1000)
    topic = models.CharField(max_length=100)
    content = models.CharField(max_length=1000)
    event_time = models.DateTimeField(null=True, blank=True)
    ip = models.CharField(max_length=15, null=True, blank=True)


    def __str__(self):
        return self.topic


class Shost(models.Model):
    ip = models.CharField(max_length=15, null=True, blank=True, unique=True) #唯一
    username = models.CharField(max_length=20,)
    password = models.CharField(max_length=100,)
    port = models.IntegerField()
    private_key = models.CharField(max_length=100) #优先使用证书连接
    def __str__(self):
        return self.ip

class Script(models.Model):
    host = models.ForeignKey("Shost", on_delete=models.CASCADE)
    user = models.CharField(max_length=20, null=True, blank=True) #执行脚本的用户
    # crontab = models.CharField(max_length=20) #脚本执行周期
    cmd = models.CharField(max_length=200, null=True, blank=True) #脚本命令
    logfile = models.CharField(max_length=200) #日志文件
    ok_str = models.CharField(max_length=10, default="(--OK--)")
    status_choices = [(0, '正常'), (1, '异常')]
    status = models.SmallIntegerField(choices=status_choices, default=0, blank=True, null=True)
    check_time = models.DateTimeField(auto_now=True, verbose_name="检查时间", blank=True, null=True)

    def __str__(self):
        return self.host.ip + self.logfile








