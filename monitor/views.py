from django.shortcuts import render, HttpResponse, redirect
from account.views import login_auth
from . import models
from django.db import models as dj_models
# from client.get_hostinfo_thread import GetHostInfo, cmd_base, cmd_performance
from math import ceil
from django.core.paginator import PageNotAnInteger, EmptyPage, Paginator
from monitor.utils import get_md5_value, get_decode_value, get_encrypt_value, POOL, ssh_cmd
import json
from django.db.models import Max
from MyMonitoring import settings
from threading import Thread
import datetime



@login_auth
def index(request):
    '''监控首页'''
    _username = request.session.get('_username', None)  # 即使后面不加None，找不到也会返回默认None
    return render(request, 'monitor/index.html',
                  {'username': _username,
                   })

@login_auth
def hostlist(request):
    '''主机列表'''
    _username = request.session.get('_username', None)  # 即使后面不加None，找不到也会返回默认None
    if request.method == "POST":#更改主机状态值
        ip = request.POST.get("ip")
        host = models.Host.objects.get(ip=ip)
        # state的值为0 1 2
        if host.state == 2:
            host.state = 0
        else:
            host.state += 1

        host.save() #一定要保存，否则没了
        # return HttpResponse(json.dumps(host.get_state_display()))
        # test_dic = {'name':'dyh', 'age':18}
        # return HttpResponse(json.dumps(test_dic))

    rows = models.Host.objects.all().order_by('ip')
    paginator = Paginator(rows, 20)  # 每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常
    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1)  # 第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页
    return render(request, 'monitor/host_list.html',
                  {'username': _username,
                   'query_sets':query_sets,
                   })

@login_auth
def hostnote(request, ip):
    _username = request.session.get('_username', None)  # 即使后面不加None，找不到也会返回默认None
    host = models.Host.objects.get(ip=ip)
    if request.method == "POST":#修改备注信息
        note = request.POST.get("note")
        host.note = note
        host.save()
        return redirect("/monitor/hostlist/")
    return render(request, 'monitor/hostnote.html',
                  {'username': _username,
                   'host': host,

                   })

@login_auth
def host_delete(request, ip):
    '''主机列表'''
    _username = request.session.get('_username', None)  # 即使后面不加None，找不到也会返回默认None
    host = models.Host.objects.get(ip=ip)
    if request.method == "POST":#删除主机
        host.delete()
        hostbase = models.HostBase.objects.get(ip=ip)
        hostbase.delete()
        hostperf = models.HostPerformance.objects.filter(ip=ip)
        hostperf.delete()  #这样可以一次性删除查询集中的所有记录
        userkey = models.Userkey.objects.filter(ip=ip)
        userkey.delete()
        warn = models.Warning.objects.filter(ip=ip)
        warn.delete()
        return redirect("/monitor/hostlist/")
    return render(request, 'monitor/host_delete.html',
                  {'username': _username,
                   'host': host,
                   })

@login_auth
def hostbase(request):
    _username = request.session.get('_username', None)
    rows = models.HostBase.objects.all().order_by("ip")
    # 下面这个不是想要的结果，还是用sql吧，这种太麻烦
    # host_list = models.HostBase.objects.values("ip").annotate(update_time=Max("update_time"), os_release=Max("os_release"), cpu_num=Max("cpu_num"),
    #                                                           memory_total=Max("memory_total"),
    #                                                           disk_total=Max("disk_total"),
    #                                                           swap_total=Max("swap_total"),
    #
    #                                                            note=Max("note"),)
    # dbconn = POOL.connection()
    # cur = dbconn.cursor()
    # sql = '''select a.* from monitor_hostbase a,(select ip, max(update_time) update_time from monitor_hostbase group by ip) b
    #        where a.ip = b.ip and a.update_time = b.update_time;'''
    # cur.execute(sql)
    # rows = cur.fetchall()
    # print('rows:', rows)
    # cur.close()
    # dbconn.close()
    paginator = Paginator(rows, 20) #每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常
    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1) #第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页
    return render(request, 'monitor/hostbase.html',
                  {'username': _username,
                   'query_sets': query_sets,
                   })

@login_auth
def hostperformance(request):
    _username = request.session.get('_username')
    # host_list = models.Host.objects.all().order_by("ip")

    dbconn = POOL.connection()
    cur = dbconn.cursor()
    sql = '''select a.* from monitor_hostperformance a,(select ip, max(update_time) update_time from monitor_hostperformance group by ip) b 
           where a.ip = b.ip and a.update_time = b.update_time order by a.ip asc;'''
    cur.execute(sql)
    rows = cur.fetchall() #最新一次检查

    # 不需要再这样计算了，采集时直接存储在表中
    # sql = '''select a.* from monitor_HostPerformance a,
    #                 (select x.ip, max(x.update_time) update_time from monitor_HostPerformance x,
    #                         (select ip, max(update_time) update_time from monitor_HostPerformance group by ip) y
    #                  where x.ip = y.ip and x.update_time < y.update_time group by x.ip) b
    #           where a.ip = b.ip and a.update_time = b.update_time order by a.ip asc;'''
    # cur.execute(sql)
    # pre_rows = cur.fetchall() #最新检查的前一次，每个ip只有一行数据
    cur.close()
    dbconn.close()



    paginator = Paginator(rows, 20)  # 每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常



    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1)  # 第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页
    return render(request, 'monitor/hostperformance.html', {
        'username': _username,
        'query_sets': query_sets,
    })

@login_auth
def addrule(request):
    _username = request.session.get('_username', None)
    if request.method == "POST":#新增rule
        counts = request.POST.get("counts").strip()
        keyname = request.POST.get("keyname").strip()
        symbol = request.POST.get("symbol").strip()
        keyvalue = request.POST.get("keyvalue").strip()
        #abc123 = request.POST.get("abc123")
        #print(counts, keyname, symbol, keyvalue, abc123)
        rule = models.Rules(keyname=keyname, counts=int(counts), symbol=symbol, keyvalue=float(keyvalue))
        try:
            rule.save()
        except Exception as e:
            print('创建rule保存时异常',e)
            return HttpResponse("rule创建失败！")
        return redirect("/monitor/rule_list/")

    return render(request, 'monitor/addrule.html',
                  {"username": _username,
                   }
                  )

@login_auth
def rule_list(request):
    _username = request.session.get('_username', None)
    rows = models.Rules.objects.all().order_by("keyname")
    paginator = Paginator(rows, 20) #每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常
    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1) #第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页
    return render(request, 'monitor/rules_list.html',
                  {'username': _username,
                   'query_sets': query_sets,
                   })

@login_auth
def rule_modify(request, rule_id):
    _username = request.session.get('_username', None)

    rule = models.Rules.objects.get(id=rule_id)
    if request.method == "POST":#新增rule
        counts = request.POST.get("counts").strip()
        keyname = request.POST.get("keyname").strip()
        symbol = request.POST.get("symbol").strip()
        keyvalue = request.POST.get("keyvalue").strip()
        rule.keyname = keyname
        rule.counts = int(counts)
        rule.symbol = symbol
        rule.keyvalue = float(keyvalue)
        rule.save()
        return redirect("/monitor/rule_list/")
    return render(request, 'monitor/rule_modify.html',
                  {'username': _username,
                   'rule': rule,
                   })

@login_auth
def rule_has_host(request, rule_id):
    _username = request.session.get('_username', None)
    rule = models.Rules.objects.get(id=rule_id)
    rows = rule.host_set.all().order_by("ip")
    paginator = Paginator(rows, 20) #每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常
    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1) #第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页
    return render(request, 'monitor/rule_has_host.html',
                  {'username': _username,
                   'query_sets': query_sets,
                   'rule': rule,
                   })

@login_auth
def hostmonitor(request):
    _username = request.session.get('_username', None)

    rows = models.Host.objects.all().order_by("ip")
    paginator = Paginator(rows, 20) #每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常
    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1) #第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页
    return render(request, 'monitor/hostmonitor.html',
                  {'username': _username,
                   'query_sets': query_sets,
                  }
                  )

@login_auth
def host_rule_set(request):
    _username = request.session.get('_username', None)


    if request.method == "POST":#主机规则配置
        hosts_info = {}  # 无效的设置
        # print("post方式")
        # print("type:", request.POST.get("action_type"))
        # print("host_ids:", request.POST.get("host_ids"),)
        # print("rule_ids:", request.POST.get("rule_ids"))

        # request.POST.get(key) 找不到,不会报错,返回None
        action_type = request.POST.get("action_type") # clear or set
        host_ids = request.POST.get("host_ids")
        if host_ids:
            host_ids = host_ids.split(',') #以逗号分隔的字符串, 用split转成列表

        if action_type == "set":#配置
            rule_ids = request.POST.get("rule_ids")
            #print("vies中", host_ids, rule_ids)
            if rule_ids:
                rule_ids = rule_ids.split(',')
            for host_id in host_ids:
                host = models.Host.objects.get(id=int(host_id))
                hosts_info[host.ip] = {} #初始化
                hosts_info[host.ip]['aid'] = 'a_%s'% str(host.id) #a标签的ID
                # hosts_info[host.ip]['rules'] = 0  # 该主机拥有的rule数量
                hosts_info[host.ip]['invalid_rule'] = [] #无效的rule
                for rule_id in rule_ids:
                    rule = models.Rules.objects.get(id=int(rule_id))
                    #判断host是否具有该rule
                    if ':' in rule.keyname:#不是公共的key,前缀是Ip
                        ip = rule.keyname.split(':')[0]
                        if ip == host.ip:#是该host的key
                            host.rules.add(rule)  # 如果已有，则会忽略
                            host.save()  # 写不写都可以,写上吧, 之前记得host.delete()之后是不能save的,否则删除的又回来了
                        else:#没有匹配上，不是该host的key
                            hosts_info[host.ip]['invalid_rule'].append(rule.keyname)
                    else:#是公共的key
                        host.rules.add(rule)
                        host.save()

                hosts_info[host.ip]['rules'] = len(host.rules.all())  # 该主机拥有的rule数量


            # invaild_dic = invalid_set #这种不叫复制一份，内存ID是相同的
            # print(id(invaild_dic), id(invalid_set))
            # invalid_dic = {}
            # for key in invalid_set:
            #     if  invalid_set[key]:
            #         invalid_dic[key] = invalid_set[key]  #RuntimeError: dictionary changed size during iteration，字典在跌代时不能变更，所以copy一份
            #         print(id(invalid_dic[key]), id(invalid_set[key]))
                #print(host.rules.all())
        elif action_type == "clear":#清空
            for host_id in host_ids:
                host = models.Host.objects.get(id=int(host_id))
                # print('操作前', host.rules.all())
                # print(dir(host.rules))
                host.rules.clear()
                host.save() #写不写都可以
                # print('操作后',host.rules.all())
        # return redirect('/monitor/') #使用了ajax，此处的返回对前端无效
        #print('最终：', hosts_info)


        return HttpResponse(json.dumps(hosts_info))  #方法1、处理ajax提交
        # 方法2、处理form提交，在POST里无需返回，与get共用返回页







    host_query_sets = models.Host.objects.all()
    rule_query_sets = models.Rules.objects.all().order_by("keyname")
    return render(request, 'monitor/host_rule_set.html',
                  {'username': _username,
                    'host_query_sets':host_query_sets,
                   'rule_query_sets':rule_query_sets,

                  }
                  )

@login_auth
def host_ip_rule(request, host_ip):
    _username = request.session.get('_username', None)

    host = models.Host.objects.get(ip=host_ip)
    rows = host.rules.all()

    paginator = Paginator(rows, 20)  # 每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常
    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1)  # 第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页
    return render(request, 'monitor/host_ip_rule.html', {
        'username': _username,
        'host': host,
        'query_sets': query_sets,
    })

@login_auth
def host_remove_rule(request, host_ip, rule_id):
    _username = request.session.get('_username', None)

    host = models.Host.objects.get(ip=host_ip)
    rule = models.Rules.objects.get(id=rule_id)
    if request.method == "POST":#移除主机中的一条规则
        host.rules.remove(rule)
        return redirect("/monitor/host_ip_rule/%s/" % host.ip)


    return render(request, 'monitor/host_remove_rule.html', {
        'username': _username,
        'host': host,
        'rule': rule,
    })

@login_auth
def rule_delete(request, rule_id):
    _username = request.session.get('_username', None)

    rule = models.Rules.objects.get(id=rule_id)
    if request.method == "POST":#删除一条rule
        warn_list = models.Warning.objects.filter(rule_id=rule_id)
        for warn in warn_list:
            warn.delete() #如果此条rule已触发告警，这样直接删除可能会导致缺少发送恢复邮件
        rule.delete()  # host中包含此rule会自动删除
        # rule.save() #前面虽然执行了delete，但rule对象还存在内存中，一旦save，便相当于新插入一条，所以此处不能save
        return redirect("/monitor/rule_list/")


    return render(request, 'monitor/rule_delete.html', {
        'username': _username,
        'rule': rule,
    })


@login_auth
def userkey(request):
    _username = request.session.get('_username', None)

    dbconn = POOL.connection()
    cur = dbconn.cursor()
    sql = '''select a.* from monitor_userkey a,(select ip, keyname,max(update_time) update_time from monitor_userkey group by ip,keyname) b
           where a.ip = b.ip and a.keyname=b.keyname and a.update_time = b.update_time;'''
    cur.execute(sql)
    rows = cur.fetchall()
    #print('views rows:', rows)
    cur.close()
    dbconn.close()
    paginator = Paginator(rows, 20) #每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常
    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1) #第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页
    return render(request, 'monitor/userkey.html',
                  {'username': _username,
                   'query_sets': query_sets,
                   })

@login_auth
def userkey_del(request, ip, keyname):
    _username = request.session.get('_username', None)
    userkey_objs = models.Userkey.objects.filter(ip=ip, keyname=keyname)
    if request.method == "POST":
        userkey_objs.delete()
        return redirect('/monitor/userkey/')
    return render(request, 'monitor/userkey_del.html', {
        'username': _username,
        'ip':ip,
        'keyname':keyname,
    })

@login_auth
def userkey_host(request, ip):
    _username = request.session.get('_username', None)

    dbconn = POOL.connection()
    cur = dbconn.cursor()
    sql = '''select a.* from monitor_userkey a ,(select ip, keyname,max(update_time) update_time from monitor_userkey where ip='%s' group by ip,keyname) b
               where a.ip = b.ip and a.keyname=b.keyname and a.update_time = b.update_time;''' % ip
    cur.execute(sql)
    rows = cur.fetchall()
    #print('rows:', rows)
    cur.close()
    dbconn.close()

    paginator = Paginator(rows, 20) #每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常
    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1) #第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页
    return render(request, 'monitor/userkey.html',
                  {'username': _username,
                   'query_sets': query_sets,
                   })


@login_auth
def hosthistory(request):
    _username = request.session.get('_username', None)
    if request.method == "POST":#更改主机状态值
        pass
        # return HttpResponse(json.dumps(host.get_state_display()))
        # test_dic = {'name':'dyh', 'age':18}
        # return HttpResponse(json.dumps(test_dic))

    rows = models.HostHistory.objects.all().order_by('-event_time')
    paginator = Paginator(rows, 20)  # 每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常
    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1)  # 第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页
    return render(request, 'monitor/hosthistory.html',
                  {'username': _username,
                   'query_sets':query_sets,
                   })


@login_auth
def hosthistory_ip(request, ip):
    _username = request.session.get('_username', None)
    if request.method == "POST":#更改主机状态值
        pass
        # return HttpResponse(json.dumps(host.get_state_display()))
        # test_dic = {'name':'dyh', 'age':18}
        # return HttpResponse(json.dumps(test_dic))

    rows = models.HostHistory.objects.filter(ip=ip).order_by('event_time')
    paginator = Paginator(rows, 20)  # 每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常
    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1)  # 第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页
    return render(request, 'monitor/hosthistory.html',
                  {'username': _username,
                   'query_sets':query_sets,
                   })


@login_auth
def mailhistory(request):
    _username = request.session.get('_username', None)
    if request.method == "POST":#更改主机状态值
        pass
        # return HttpResponse(json.dumps(host.get_state_display()))
        # test_dic = {'name':'dyh', 'age':18}
        # return HttpResponse(json.dumps(test_dic))

    rows = models.SendMail.objects.all().order_by('-event_time')
    paginator = Paginator(rows, 20)  # 每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常
    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1)  # 第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页
    return render(request, 'monitor/mail_list.html',
                  {'username': _username,
                   'query_sets':query_sets,
                   })

@login_auth
def mailhistory_id(request, id):
    _username = request.session.get('_username', None)
    if request.method == "POST":#更改主机状态值
        pass
        # return HttpResponse(json.dumps(host.get_state_display()))
        # test_dic = {'name':'dyh', 'age':18}
        # return HttpResponse(json.dumps(test_dic))

    rows = models.SendMail.objects.filter(id=int(id))
    paginator = Paginator(rows, 20)  # 每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常
    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1)  # 第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页
    return render(request, 'monitor/mail_list.html',
                  {'username': _username,
                   'query_sets':query_sets,
                   })

@login_auth
def script_hostinfo(request):
    _username = request.session.get('_username', None)
    rows = models.Shost.objects.all().order_by("ip")
    paginator = Paginator(rows, 20)  # 每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常
    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1)  # 第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页
    return render(request, 'monitor/script_hostinfo.html',{
        'username': _username,
        'query_sets':query_sets,

    })

@login_auth
def addhost(request):
    _username = request.session.get('_username', None)
    if request.method == "POST":#新增主机
        ip_str = request.POST.get("ip").strip()
        ip_list = ip_str.split(",")
        username = request.POST.get("username").strip()
        password = request.POST.get("password", "").strip()
        port = request.POST.get("port").strip()
        private_key = request.POST.get("private_key", "").strip()
        if len(password) > 32:
            return HttpResponse("密码长度不能大于32位")

        enc_pass = get_encrypt_value(password)

        if ip_list and port and username and (password or private_key):# ip，用户，（密码与证书二选一）
            for ip in ip_list:
                host = models.Shost(ip=ip.strip(), port=int(port), username=username, password=enc_pass, private_key=private_key)
                host.save()
        return redirect('/monitor/script/hostinfo/')


    return render(request, 'monitor/addhost.html')

@login_auth
def script_modifyhost(request, id):
    _username = request.session.get('_username', None)
    host = models.Shost.objects.get(id=id)
    if request.method == "POST":#主机信息修改
        print("修改主机信息--》", request.POST)

        username = request.POST.get("username").strip()
        password = request.POST.get("password", "").strip() #用户输入标签
        print("获取的password:", password)
        port = request.POST.get("port").strip()
        private_key = request.POST.get("private_key", "").strip()
        print(host.password, password, '对比一下')
        if password == host.password:# 没改密码
            enc_pass = password
        else:
            if len(password) > 32:
                return HttpResponse("密码长度不能大于32位")
            enc_pass = get_encrypt_value(password)

        host.username = username
        host.password = enc_pass
        host.port = port
        host.private_key = private_key
        host.save()
        return redirect('/monitor/script/hostinfo/')


    return render(request, 'monitor/script_modifyhost.html',{
        'username': _username,
        'host':host,
    })

@login_auth
def script_del_host(request, id):
    _username = request.session.get('_username', None)

    host = models.Shost.objects.get(id=id)
    if request.method == "POST":#删除一条rule
        script_sets = host.script_set.all()
        for script in script_sets:
            script.delete()
        host.delete()
        return redirect("/monitor/script/hostinfo/")


    return render(request, 'monitor/script_del_host.html', {
        'username': _username,
        'host': host,
    })

@login_auth
def script_status(request):
    _username = request.session.get('_username', None)
    rows = models.Script.objects.all().order_by("ip")
    paginator = Paginator(rows, 20)  # 每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常
    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1)  # 第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页
    return render(request, 'monitor/script_hostinfo.html',{
        'username': _username,
        'query_sets':query_sets,

    })

# 增、删、改、查
@login_auth
def new_obj(request, model_name):
    _username = request.session.get('_username', None)
    if request.method == "POST":#新建记录
        print('post-->', request.POST, type(request.POST))
        model_class = getattr(models, model_name)
        fields_set = model_class._meta.get_fields()
        instance_obj = model_class() #这种方式创建的实例，不管字段是为非空，都可以成功，但如果没有instance_obj.save()前，使用ManyToMany字段时会报错
        # instance_obj = model_class.objects.create() #这种方式创建的实例，可以使用ManyToMany字段，但在建表创建非空字段时，不能设置default=None，否则此处报错
        for key, value in request.POST.items():#如果key对应的是一个列表，这样得到的value只是列表中的一个元素
            if value and key != "csrfmiddlewaretoken":
                for field in fields_set:
                    if field.name == key:#就是这个字段
                        if type(field) in [dj_models.OneToOneField, dj_models.ForeignKey]:
                            print(field.name, type(field))
                            rel_model = field.related_model
                            rel_instances = rel_model.objects.get(id=value)
                            setattr(instance_obj, key, rel_instances)
                        elif type(field) == dj_models.ManyToManyField:

                            # 非常重要
                            instance_obj.save()  # 一定要先保存一下，否则getattr(instance_obj, key)会报错


                            mtm_obj = getattr(instance_obj, key) # 得到多对多的字段对象
                            value_list = request.POST.getlist(key)  # 这样才能得到列表全部数据
                            rel_model = field.related_model
                            for id in value_list:
                                rel_instances = rel_model.objects.get(id=id)
                                mtm_obj.add(rel_instances)  #如果已有，不会重复添加
                        elif type(field) in [dj_models.IntegerField, dj_models.BigIntegerField, dj_models.FloatField, dj_models.SmallIntegerField,]:
                            value = float(value)
                            setattr(instance_obj, key, value)

                        else:#其他字段类型
                            setattr(instance_obj, key, value)
        instance_obj.save()

        return redirect('/monitor/select/%s/' % model_name)
    return render(request, 'monitor/new_obj.html',{
        'username': _username,
        'model_name':model_name,
    })

@login_auth
def del_obj(request, model_name, obj_id):
    _username = request.session.get('_username', None)
    model_class = getattr(models, model_name)
    instance_obj = model_class.objects.get(id=obj_id)
    if request.method == "POST":
        instance_obj.delete()
        return redirect('/monitor/select/%s/' % model_name)

    return render(request, 'monitor/del_obj.html',{
        'username': _username,
        'model_name':model_name,
        'instance_obj':instance_obj,
    })

@login_auth
def update_obj(request, model_name, obj_id):
    _username = request.session.get('_username', None)
    model_class = getattr(models, model_name)
    instance_obj = model_class.objects.get(id=obj_id)
    if request.method == "POST":#更新记录
        print('post-->', request.POST, type(request.POST))
        fields_set = model_class._meta.get_fields()
        # instance_obj = model_class() #这种方式创建的实例，当使用ManyToMany字段时会报错
        # instance_obj = model_class.objects.create() #这种方式创建的实例，可以使用ManyToMany字段，但在建表创建非空字段时，不能设置default=None，否则此处报错
        for key, value in request.POST.items():#如果key对应的是一个列表，这样得到的value只是列表中的一个元素
            if value and key != "csrfmiddlewaretoken":
                for field in fields_set:
                    if field.name == key:#就是这个字段
                        if type(field) in [dj_models.OneToOneField, dj_models.ForeignKey]:
                            rel_model = field.related_model
                            rel_instances = rel_model.objects.get(id=value)
                            setattr(instance_obj, key, rel_instances)
                        elif type(field) == dj_models.ManyToManyField:
                            mtm_obj = getattr(instance_obj, key) # 得到多对多的字段对象
                            for rel_obj in mtm_obj.all(): #先清空，这是唯一和new_obj不同的地方
                                mtm_obj.remove(rel_obj)
                            value_list = request.POST.getlist(key)  # 这样才能得到列表全部数据
                            rel_model = field.related_model
                            for id in value_list:
                                rel_instances = rel_model.objects.get(id=id)
                                mtm_obj.add(rel_instances)  #如果已有，不会重复添加
                        elif type(field) in [dj_models.IntegerField, dj_models.BigIntegerField, dj_models.FloatField, dj_models.SmallIntegerField,]:
                            value = float(value)
                            setattr(instance_obj, key, value)

                        else:#其他字段类型
                            setattr(instance_obj, key, value)
        instance_obj.save()


        return redirect('/monitor/select/%s/' % model_name)
    return render(request, 'monitor/update_obj.html',{
        'username': _username,
        'model_name':model_name,
        'instance_obj': instance_obj,

    })

@login_auth
def select_model(request, model_name):
    _username = request.session.get('_username', None)
    if request.method == "POST":#刷新脚本状态
        thread_list = []
        for script in models.Script.objects.all():
            t = Thread(target=ssh_cmd, args=(script,) )#优先使用证书连接
            t.start()
            thread_list.append(t)
        for t in thread_list:
            t.join() #等待所有线程结束
        return redirect('/monitor/select/Script/') #如果不重定向，页面点刷新永远是POST
    model_class = getattr(models, model_name)
    rows = model_class.objects.all().order_by("id")
    paginator = Paginator(rows, 5)  # 每页20条
    current_page = request.GET.get('_page')  # 找不到就为None,触发后面PageNotAnInteger异常
    try:
        query_sets = paginator.page(current_page)
    except PageNotAnInteger:  # 如果page为None，就会触发这个异常
        # If page is not an integer, deliver first page.
        query_sets = paginator.page(1)  # 第一页
    except EmptyPage:  # 大于paginator.num_pages或者小于1
        # If page is out of range (e.g. 9999), deliver last page of results.
        # query_sets = paginator.page(paginator.num_pages)  #最后一页
        query_sets = paginator.page(1)  # 全部定到第一页

    return render(request, 'monitor/select_model.html', {
        'username': _username,
        'model_name':model_name,
        'query_sets':query_sets,
    })
