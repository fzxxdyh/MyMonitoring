
from django import template
from django.utils.safestring import mark_safe
from math import ceil
from monitor import utils, models
from django.db import models as dj_models
from monitor.utils import POOL

register = template.Library()

@register.simple_tag
def display_hostbase(query_sets):
    '''
    <tr>
      <td>1,001</td>
      <td>Lorem</td>
      <td>ipsum</td>
    </tr>
    :param query_sets:
    :return:
    '''
    row_ele = ''
    per_page = query_sets.paginator.per_page #每页多少条
    number = query_sets.number  # 当前是第几页
    start = (number - 1) * per_page + 1 #当前页从几开始
    for index, host in enumerate(query_sets, start):
        row_ele += '''<tr>
        <td>{_index}</td>
        <td>{ip}</td>
        <td>{update_time}</td>
        <td>{os_release}</td>
        <td>{cpu_num}</td>
        <td>{memory_total}</td>
        <td>{disk_total}</td>
        <td>{swap_total}</td>
        </tr>'''.format(
            _index=index,  ip=host.ip, update_time=host.update_time.strftime('%Y-%m-%d %H:%M:%S'), os_release=host.os_release, cpu_num=host.cpu_num, memory_total=ceil(host.memory_total/1024/1024/1024), disk_total=ceil(host.disk_total/1024/1024/1024),
            swap_total=ceil(host.swap_total / 1024 / 1024 / 1024),
        )

    return mark_safe(row_ele)


@register.simple_tag
def display_hostlist(query_sets):
    row_ele = ''
    per_page = query_sets.paginator.per_page #每页多少条
    number = query_sets.number  # 当前是第几页
    start = (number - 1) * per_page + 1 #当前页从几开始
    for index, host in enumerate(query_sets, start):
        color = None
        if host.state == 0:
            color = "green"
        elif host.state == 1:
            color = "red"
        else:
            color = "darkgray"

        userkey_nums = len( models.Userkey.objects.filter(ip=host.ip).values('keyname').distinct() ) #distinct里不能有参数，就是以前面的字段去重
        row_ele += '''<tr>
        <td>{_index}</td>
        <td><a  href="/monitor/hosthistory/{ip}/">{ip}</a></td>
        <td>{update_time}</td>
        <td><a  href="/monitor/userkey_host/{ip}/">{userkey_nums}</a></td>
        <td><a  href="/monitor/host_ip_rule/{ip}/">{rules}</a></td>
        <td><a style="color:{color};" href="/monitor/hostlist/" onclick="change_host_state(this, '{ip}')">{state}</a></td>
        <td><a href="/monitor/hostnote/{ip}/">{note}</a></td>
        <td><a href="/monitor/host_delete/{ip}/"><img src="/static/img/del.png" style="width:30px;height:30px;"></a></td>
        </tr>'''.format(
            _index=index,  ip=host.ip,  update_time=host.update_time.strftime("%Y-%m-%d %H:%M:%S"), userkey_nums=userkey_nums, rules=len(host.rules.all()), state=host.get_state_display(), note=host.note, color=color,
        )

    return mark_safe(row_ele)


@register.simple_tag
def build_paginators(query_sets):
    '''返回整个分页元素'''
    page_btns = ''

    # added_dot_ele = False #
    # for page_num in query_sets.paginator.page_range:
    #     if page_num < 3 or page_num > query_sets.paginator.num_pages -2 \
    #             or abs(query_sets.number - page_num) <= 2: #代表最前2页或最后2页 #abs判断前后1页
    #         ele_class = ""
    #         if query_sets.number == page_num:
    #             added_dot_ele = False
    #             ele_class = "active"
    #         page_btns += '''<li class="%s"><a href="?page=%s">%s</a></li>''' % (
    #         ele_class, page_num,page_num)
    #
    #     else: #显示...
    #         if added_dot_ele == False: #现在还没加...
    #             page_btns += '<li><a>...</a></li>'
    #             added_dot_ele = True

    dot_flag = True
    for num in query_sets.paginator.page_range: # 如果总共12页，就是1--12
        if num == query_sets.number: # query_sets.number代表页面中的当前页数值
            dot_flag = True
            current_page = 'active'
        else:
            current_page = ''

        if num < 3 or abs(num-query_sets.number)<=2 or num > query_sets.paginator.num_pages - 2: #前后两页和中间页
            page_btns += '''<li class="%s"><a href="?_page=%s">%s</a></li>''' % (current_page,num, num)
        elif dot_flag:
            page_btns += '''<li><a>...</a></li>'''
            dot_flag = False

    return mark_safe(page_btns)




@register.simple_tag
def display_hostperformance(query_sets):
    # print('query_sets',query_sets)
    # print('pre_rows', pre_rows)
    '''
query_sets: (
       (9993, '10.10.10.2', datetime.datetime(2018, 12, 3, 14, 6, 54), 0.2, 11.0, 16.21, 0.0, 2341444, 3469185),
       (9994, '10.10.10.1', datetime.datetime(2018, 12, 3, 14, 7, 37, 726000), 10.4, 40.4, 41.2, 20.4, 117835484, 49492390)
       )
    '''
    row_ele = ''
    per_page = query_sets.paginator.per_page #每页多少条
    number = query_sets.number  # 当前是第几页
    start = (number - 1) * per_page + 1 #当前页从几开始
    for index, row in enumerate(query_sets, start):
        # if pre_rows[index - 1][1] == row[1]:#前后两行IP相等
        #     print("ip相等，数据是对的")
        #     interval = utils.dateDiffInSeconds(row[2], pre_rows[index - 1][2]) #两个日期间隔秒数
        #     sent_speed = round((pre_rows[index - 1][7] - row[7]) / interval / 1024, 2) #单位KB/s
        #     recv_speed = round((pre_rows[index - 1][8] - row[8]) / interval /1024 ,2) #单位KB/s
        # else:
        #     print("ip不等，数据是错的")
        #     sent_speed = 'error'
        #     recv_speed = 'error'

        row_ele += '''<tr>
        <td>{_index}</td>
        <td>{_ip}</td> 
        <td>{update_time}</td> 
        <td>{cpu_used_rate}%</td>
        <td>{memory_used_rate}%</td> 
        <td>{disk_used_rate}%</td> 
        <td>{swap_used_rate}%</td> 
        <td>{io_bytes_sent}</td>
        <td>{io_bytes_recv}</td>
        <td>{io_sent_kbs}</td>
        <td>{io_recv_kbs}</td>
        </tr>
         '''.format(
            _index=index,  _ip=row[1], update_time=row[2].strftime('%Y-%m-%d %H:%M:%S'), cpu_used_rate=row[3], memory_used_rate=row[4],
            disk_used_rate=row[5], swap_used_rate=row[6], io_bytes_sent=round(row[7]/1024/1024, 2), io_bytes_recv=round(row[8]/1024/1024, 2),
            io_sent_kbs= row[9],
            io_recv_kbs= row[10],
        )





    return mark_safe(row_ele)

@register.simple_tag
def display_keyname(rule=None):
    row_ele = ''
    default_key = ['cpu_used_rate', 'memory_used_rate', 'disk_used_rate', 'swap_used_rate', ] #默认
    conn = POOL.connection()
    cur = conn.cursor()
    sql = 'select ip, keyname from monitor_userkey group by ip, keyname '
    cur.execute(sql)
    rows = cur.fetchall()
    for line in rows:
        new_key = '%s:%s' %(line[0], line[1])
        default_key.append(new_key)
    cur.close()
    conn.close()
    for key in default_key:
        if rule and rule.keyname == key:
            select = "selected"
        else:
            select = ""
        row_ele += '<option {select} value="{key}">{key}</option>'.format(select=select, key=key)
    return mark_safe(row_ele)

@register.simple_tag
def display_symbol(rule=None):
    row_ele = ''
    symbol_field = models.Rules._meta.get_field("symbol")
    symbol_choices = symbol_field.get_choices() #[('', '---------'), (0, '=='), (3, '>'), (2, '>='), (-3, '<'), (-2, '<='), (-1, '!=')]
    length = len(symbol_choices) #长度
    for i in range(1,length, 1):#start, stop[, step])
        #print(rule.symbol, symbol_choices[i][0], '符号一样吗')
        if rule and rule.symbol == symbol_choices[i][0]:
            select = "selected"
        else:
            select = ""
        row_ele += '<option %s value="%d">%s</option>' % (select, symbol_choices[i][0], symbol_choices[i][1])
    return mark_safe(row_ele)


@register.simple_tag
def display_rule_list(query_sets):
    row_ele = ''
    per_page = query_sets.paginator.per_page  # 每页多少条
    number = query_sets.number  # 当前是第几页
    start = (number - 1) * per_page + 1  # 当前页从几开始
    for index, row in enumerate(query_sets, start):
        host_nums = len( row.host_set.all() ) # 反向查 ,在没有 ManyToManyField 字段的表中查
        symvol = getattr(row, 'get_symbol_display')()
        row_ele += '''<tr>
        <td><a href="/monitor/rule_list/{id}/">{_index}</a></td>
        <td>{counts}</td>
        <td style="display: none">{id}</td>
        <td>{keyname}</td>
        <td>{symbol}</td>
        <td>{keyvalue}</td>
        <td><a href="/monitor/rule_has_host/{id}/">{host_nums}</a></td>
        <td><a href="/monitor/rule_delete/{id}/"><img src="/static/img/del.png" style="width:30px;height:30px;"></a></td>
        </tr>'''.format(
            _index=index, id=row.id,  keyname=row.keyname, host_nums=host_nums,  symbol=symvol, keyvalue=row.keyvalue, counts=row.counts,
        )

    return mark_safe(row_ele)

@register.simple_tag
def display_rule_has_host(query_sets, rule):
    row_ele = ''
    per_page = query_sets.paginator.per_page  # 每页多少条
    number = query_sets.number  # 当前是第几页
    start = (number - 1) * per_page + 1  # 当前页从几开始
    for index, host in enumerate(query_sets, start):
        agent_state = models.Warning.objects.filter(ip=host.ip, state=-1)
        if agent_state:
            state = "agent无响应"
            color = "gray"
        else:
            state = models.Warning.objects.filter(ip=host.ip, rule_id=rule.id, state=1) #state=1表示已达报警次数
            if state:
                state = "告警"
                color = "red"
            else:
                state = "OK"
                color = "green"

        row_ele += '''<tr>
        <td>{_index}</td>
        <td>{ip}</td>
        <td style="color:{color}">{state}</td>
        </tr>'''.format(
            _index=index, ip=host.ip, color=color, state=state,
        )

    return mark_safe(row_ele)

@register.simple_tag
def display_hostmonitor(query_sets):
    row_ele = ''
    per_page = query_sets.paginator.per_page #每页多少条
    number = query_sets.number  # 当前是第几页
    start = (number - 1) * per_page + 1 #当前页从几开始
    for index, host in enumerate(query_sets, start):
        row_ele += '''<tr>
        <td>{_index}</td>
        <td>{ip}</td>
        <td><a href="/monitor/host_ip_rule/{ip}/">{rule_nums}</a></td>
        <td>{state}</td>
        </tr>'''.format(
            _index=index,  ip=host.ip, rule_nums=len(host.rules.all()), state="ok",
        )

    return mark_safe(row_ele)

@register.simple_tag
def host_choices(host_query_sets):
    row_ele = ''
    for host in host_query_sets:
        row_ele += '''<tr>
                       <td><input class="input_host" type="checkbox" value="{id}">{ip} 
                            <a id="a_{id}" href="/monitor/host_ip_rule/{ip}/">{rules}</a>
                       </td>
                       
                    </tr>'''.format(id=host.id, ip=host.ip, rules=len(host.rules.all()))
    return mark_safe(row_ele)

@register.simple_tag
def rule_choices(rule_query_sets):
    row_ele = ''
    for rule in rule_query_sets:
        rule_name = '连续%d次 %s %s%.2f' % (rule.counts, rule.keyname, rule.get_symbol_display(), rule.keyvalue)
        row_ele += '''<tr>
                       <td><input class="input_rule" type="checkbox" value="{id}">{rule_name}</td>
                    </tr>'''.format(id=rule.id, rule_name=rule_name)

    return mark_safe(row_ele)

@register.simple_tag
def display_host_ip_rule(query_sets, host_ip):
    row_ele = ''
    per_page = query_sets.paginator.per_page  # 每页多少条
    number = query_sets.number  # 当前是第几页
    start = (number - 1) * per_page + 1  # 当前页从几开始
    for index, rule in enumerate(query_sets, start):
        agent_state = models.Warning.objects.filter(ip=host_ip, state=-1)
        if agent_state:
            state = "agent无响应"
            color = "gray"
        else:
            state = models.Warning.objects.filter(ip=host_ip, rule_id=rule.id, state=1) #state=1表示已达报警次数
            if state:
                state = "告警"
                color = "red"
            else:
                state = "OK"
                color = "green"

        rule_name = '连续%d次 %s %s %.2f' % (rule.counts, rule.keyname, rule.get_symbol_display(), rule.keyvalue)
        row_ele += '''<tr>
                           <td><a href="/monitor/rule_list/{id}/">{_index}</a></td>
                           <td style="display: none">{rule_id}</td>
                           <td>{rule_name}</td>
                           <td style="color:{color}">{status}</td>
                           <td><a href="/monitor/host_remove_rule/{ip}/{rule_id}/"><img src="/static/img/del.png" style="width:30px;height:30px;"></a></td>
                        </tr>'''.format(id=rule.id, _index=index, rule_id=rule.id, ip=host_ip, rule_name=rule_name, color=color, status=state)

    return mark_safe(row_ele)


@register.simple_tag
def display_userkey(query_sets):
    row_ele = ''
    per_page = query_sets.paginator.per_page #每页多少条
    number = query_sets.number  # 当前是第几页
    start = (number - 1) * per_page + 1 #当前页从几开始
    for index, row in enumerate(query_sets, start):
        # key是否用作告警
        key_name = '{ip}:{keyname}'.format(ip=row[1], keyname=row[3])  #依次为：id ip update_time keyname keyvalue keyexp
        host = models.Host.objects.filter(ip=row[1]) #有可能没有

        if host and host[0].rules.all().filter(keyname=key_name):
            flag = "已启用"
            color = "green"
        else:
            color = "darkgray" #darkgray
            flag = '未启用'



        row_ele += '''<tr>
        <td>{_index}</td>
        <td style="display: none">{id}</td>
        <td>{ip}</td>
        <td>{keyname}</td>
        <td>{keyvalue}</td>
        <td>{update_time}</td>
        <td>{keyexp}</td>
        <td style="color:{color};">{flag}</td>
        <td><a href="/monitor/userkey/del/{ip}/{keyname}/"><img src="/static/img/del.png" style="width:30px;height:30px;"></a></td>
        </tr>'''.format(
            _index=index,  id=row[0], ip=row[1], keyname=row[3], keyvalue=row[4], update_time=row[2].strftime('%Y-%m-%d %H:%M:%S'), keyexp=row[5], flag=flag, color=color,
        )

    return mark_safe(row_ele)


@register.simple_tag
def display_hosthistory(query_sets):
    row_ele = ''
    per_page = query_sets.paginator.per_page #每页多少条
    number = query_sets.number  # 当前是第几页
    start = (number - 1) * per_page + 1 #当前页从几开始
    for index, row in enumerate(query_sets, start):
        if row.event_type == 0:
            event_type = "恢复"
            color = "green"
        else:
            event_type = "告警"
            color = "red"

        if row.rule:#不是agent
            if ":" in row.rule.keyname:
                keyname = row.rule.keyname.split(":")[1]
            else:
                keyname = row.rule.keyname
        else:
            keyname = "agent"


        row_ele += '''<tr>
        <td>{_index}</td>
        <td><a href="/monitor/hosthistory/{ip}/">{ip}</a></td>
        <td>{event_time}</td>
        <td style="color:{color};">{event_type}</td>
        <td>{keyname}</td>
        <td>{keyvalue}</td>
        <td><a href="/monitor/mailhistory/{id}/">{id}</a></td>
        </tr>'''.format(
            _index=index,  ip=row.ip, event_time=row.event_time.strftime('%Y-%m-%d %H:%M:%S'),color=color, event_type=event_type, keyname=keyname, keyvalue=row.keyvalue, id=row.mail.id,
        )

    return mark_safe(row_ele)


@register.simple_tag
def display_mail_list(query_sets):
    row_ele = ''
    per_page = query_sets.paginator.per_page #每页多少条
    number = query_sets.number  # 当前是第几页
    start = (number - 1) * per_page + 1 #当前页从几开始
    for index, row in enumerate(query_sets, start):

        row_ele += '''<tr>
        <td>{_index}</td>
        <td>{ip}</td>
        <td>{event_time}</td>
        <td>{sender}</td>
        <td>{receiver}</td>
        <td>{topic}</td>
        <td>{content}</td>
        </tr>'''.format(
            _index=index,  ip=row.ip, event_time=row.event_time.strftime('%Y-%m-%d %H:%M:%S'), sender=row.sender, receiver=row.receiver, topic=row.topic, content=row.content,
        )

    return mark_safe(row_ele)

@register.simple_tag
def display_script_hostinfo(query_sets):
    row_ele = ''
    per_page = query_sets.paginator.per_page #每页多少条
    number = query_sets.number  # 当前是第几页
    start = (number - 1) * per_page + 1 #当前页从几开始
    for index, row in enumerate(query_sets, start):
        if row.password:
            password = "******"
        else:
            password = ""
        row_ele += '''<tr>
        <td><a href="/monitor/script/hostinfo/{id}/">{_index}</a></td>
        <td>{ip}</td>
        <td>{port}</td>
        <td>{username}</td>
        <td>{password}</td>
        <td>{private_key}</td>
        <td><a href="/monitor/script/del_host/{id}/"><img src="/static/img/del.png" style="width:30px;height:30px;"></a></td>
        </tr>'''.format(
            _index=index,  id=row.id, ip=row.ip, port=row.port, username=row.username, password=password, private_key=row.private_key,
        )

    return mark_safe(row_ele)

@register.simple_tag
def display_new_obj(model_name):
    row_ele = ''
    table = getattr(models, model_name)
    # print('table别名', table._meta.verbose_name) 获得表别名
    fields_set = table._meta.get_fields()
    # print(fields_set)

    for field in fields_set:# 顺序：Rel字段 AutoField 普通字段 ManyToMany字段都排在最后
        if type(field) not in [dj_models.OneToOneRel, dj_models.ManyToOneRel, dj_models.ManyToManyRel, dj_models.AutoField]:#否则 field.verbose_name会报异常，而且这三个不需要

            if field.null:#允许为空
                required = ""
                color = ""
            else:
                required = "required"
                color = "red"

            row_ele += '''<label style="margin-left:20%;width:100px;color:{color}">{verbose_name}</label>
            '''.format(color=color,verbose_name=field.verbose_name)
            # python默认：当建表时没写field.verbose_name，则field.verbose_name = field.name


            width_size = "600px"
            if type(field) in [dj_models.ManyToManyField, dj_models.TextField]:
                multiple = "multiple"  #TextField字段没有此属性
                height_size = "200px"
            else:
                multiple = ""
                height_size = "50px"


            # 1、关系字段
            if type(field) in [dj_models.OneToOneField, dj_models.ForeignKey, dj_models.ManyToManyField]:
                rel_model = field.related_model
                option_ele = ''
                for row in rel_model.objects.all():
                    option_ele += '''<option value="{rel_id}">{row}</option>'''.format(rel_id=row.id, row=row)

                row_ele += '''
                    <select  {multiple} name="{field_name}" style="width:{width_size};height: {height_size};" {required}>
                        {option_ele}
                    </select>
                    '''.format(multiple=multiple, field_name=field.name, width_size=width_size, height_size=height_size,
                               required=required, option_ele=option_ele)

            # 2、choices字段
            elif field.choices:#不为空表明是choices字段
                option_ele = ''
                for row in field.get_choices():# [('', '---------'), (0, '正常'), (1, '异常'), (2, '告警')]
                    option_ele += '''<option value="{value}">{display_value}</option>'''.format(value=row[0], display_value=row[1])

                row_ele += '''<select  name="{field_name}" style="width: {width_size};height: {height_size};" {required}>
                                {option_ele}
                           </select>
                    '''.format(field_name=field.name, width_size=width_size, height_size=height_size, required=required, option_ele=option_ele)

            # 3、NullBooleanField  尽量不用吧
            # elif type(field) == dj_models.NullBooleanField:#比BooleanField多个Null
            #     row_ele += '''<select  name="{field_name}" style="width: {width_size};height: {height_size};" {required}>
            #                   <option value="">------</option>
            #                   <option value="1">Yes</option>    <!-- 这个值应该根据业务来 -->
            #                   <option value="0">No</option>
            #                </select> '''.format(field_name=field.name, width_size=width_size, height_size=height_size, required=required,)

            # 4、TextField
            elif type(field) == dj_models.TextField:
                row_ele += '''<textarea style="width:{width_size};height:{height_size};vertical-align:middle;" name="{field_name}" {required}> </textarea>
                       '''.format(width_size=width_size, height_size=height_size, field_name=field.name, required=required, )


            else:
                # 5、时间字段
                if type(field) == dj_models.DateTimeField:
                    input_type = "datetime-local"
                elif type(field) == dj_models.DateField:
                    input_type = "date"
                elif type(field) == dj_models.TimeField:
                    input_type = "time"

                # 6、EmailField
                elif type(field) == dj_models.EmailField:
                    input_type = "email"

                # 7、其他字段
                else:
                    input_type = "text"
                row_ele += '''<input type="{input_type}" name="{field_name}" {required} style="width: {width_size};height: {height_size};">
                           '''.format(input_type=input_type, field_name=field.name, required=required, width_size=width_size, height_size=height_size, )

            row_ele += '<hr/>' #水平线

    return mark_safe(row_ele)

# select_table
@register.simple_tag
def display_table_head(model_name):
    row_ele = '<th>序号</th>'
    table = getattr(models, model_name)
    fields_set = table._meta.get_fields()

    for field in fields_set:# 顺序：Rel字段 AutoField 普通字段 ManyToMany字段都排在最后
        if type(field) not in [dj_models.OneToOneRel, dj_models.ManyToOneRel, dj_models.ManyToManyRel, dj_models.ManyToManyField, dj_models.AutoField]:#否则 field.verbose_name会报异常，而且这三个不需要
            row_ele += '''<th>{verbose_name}</th>'''.format(verbose_name=field.verbose_name)


    row_ele += '<th>删除</th>'


    return mark_safe(row_ele)

# select_table
@register.simple_tag
def display_table_body(model_name, query_sets=None):
    if not query_sets:
        return ""
    row_ele = ''
    per_page = query_sets.paginator.per_page  # 每页多少条
    number = query_sets.number  # 当前是第几页
    start = (number - 1) * per_page + 1  # 当前页从几开始
    for index, row in enumerate(query_sets, start):
        row_ele += '''<tr><td><a href="/monitor/update/{model_name}/{obj_id}/">{index}</a></td>'''.format(model_name=model_name, obj_id=row.id, index=index)
        for field in row._meta.get_fields():  # 顺序：Rel字段 AutoField 普通字段 ManyToMany字段都排在最后
            if type(field) not in [dj_models.OneToOneRel, dj_models.ManyToOneRel, dj_models.ManyToManyRel,dj_models.ManyToManyField, dj_models.AutoField]:  # 否则 field.verbose_name会报异常，而且这三个不需要
                color = ""
                if field.choices:#是choices字段
                    value = getattr(row, "get_%s_display" % field.name)()
                    if value == "异常":
                        color = "red"

                elif type(field) in [dj_models.DateTimeField, dj_models.DateField, dj_models.TimeField]:
                    value = getattr(row, field.name).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    value = getattr(row, field.name)
                row_ele += '''<td style="color:{color}">{value}</td>'''.format(color=color, value=value)
        row_ele += '''<td><a href="/monitor/del/{model_name}/{id}/"><img src="/static/img/del.png" style="width:30px;height:30px;"></a></td>'''.format(model_name=model_name, id=row.id)
        row_ele += '</tr>'
    return mark_safe(row_ele)

@register.simple_tag
def display_update_obj(instance_obj):
    row_ele = ''
    fields_set = instance_obj._meta.get_fields()
    # print(fields_set)

    for field in fields_set:# 顺序：Rel字段 AutoField 普通字段 ManyToMany字段都排在最后
        if type(field) not in [dj_models.OneToOneRel, dj_models.ManyToOneRel, dj_models.ManyToManyRel, dj_models.AutoField]:#否则 field.verbose_name会报异常，而且这三个不需要

            if field.null:#允许为空
                required = ""
                color = ""
            else:
                required = "required"
                color = "red"

            row_ele += '''<label style="margin-left:20%;width:100px;color:{color}">{verbose_name}</label>
            '''.format(color=color,verbose_name=field.verbose_name)
            # python默认：当建表时没写field.verbose_name，则field.verbose_name = field.name


            width_size = "600px"
            if type(field) in [dj_models.ManyToManyField, dj_models.TextField]:
                multiple = "multiple"  #TextField字段没有此属性
                height_size = "200px"
            else:
                multiple = ""
                height_size = "50px"

            value = getattr(instance_obj, field.name)
            if value:
                if type(field) == dj_models.DateTimeField:
                    value = value.strftime("%Y-%m-%dT%H:%M")  # 2019-01-18T00:59
                elif type(field) == dj_models.DateField:
                    value = value.strftime("%Y-%m-%d")
                elif type(field) == dj_models.TimeField:
                    value = value.strftime("%H:%M")
            else:
                value = ""


            # 1、关系字段
            if type(field) in [dj_models.OneToOneField, dj_models.ForeignKey, dj_models.ManyToManyField]:
                rel_model = field.related_model
                rel_obj = getattr(instance_obj, field.name) #可能是一个对象，也可能是一个查询集
                option_ele = ''
                for row in rel_model.objects.all():
                    if type(field) == dj_models.ManyToManyField:
                        if row in rel_obj.all():
                            select = "selected"
                        else:
                            select = ""
                    else:
                        if row == rel_obj:
                            select = "selected"
                        else:
                            select = ""
                    option_ele += '''<option {select} value="{rel_id}">{row}</option>'''.format(select=select, rel_id=row.id, row=row)

                row_ele += '''
                    <select {multiple} name="{field_name}" style="width:{width_size};height: {height_size};" {required}>
                        {option_ele}
                    </select>
                    '''.format(multiple=multiple, field_name=field.name, width_size=width_size, height_size=height_size,
                               required=required, option_ele=option_ele)

            # 2、choices字段
            elif field.choices:#不为空表明是choices字段
                option_ele = ''
                for row in field.get_choices():# [('', '---------'), (0, '正常'), (1, '异常'), (2, '告警')]
                    if row[0] == getattr(instance_obj, field.name):
                        select = "selected"
                    else:
                        select = ""
                    option_ele += '''<option {select} value="{value}">{display_value}</option>'''.format(select=select, value=row[0], display_value=row[1])

                row_ele += '''<select  name="{field_name}" style="width: {width_size};height: {height_size};" {required}>
                                {option_ele}
                           </select>
                    '''.format(field_name=field.name, width_size=width_size, height_size=height_size, required=required, option_ele=option_ele)

            # 3、NullBooleanField
            # elif type(field) == dj_models.NullBooleanField:#比BooleanField多个Null
            #     row_ele += '''<select  name="{field_name}" style="width: {width_size};height: {height_size};" {required}>
            #                   <option value="">------</option>
            #                   <option value="1">Yes</option>    <!-- 这个值应该根据业务来 -->
            #                   <option value="0">No</option>
            #                </select> '''.format(field_name=field.name, width_size=width_size, height_size=height_size, required=required,)

            # 4、TextField
            elif type(field) == dj_models.TextField:
                row_ele += '''<textarea style="width:{width_size};height:{height_size};vertical-align:middle;" name="{field_name}" {required}>{value}</textarea>
                       '''.format(width_size=width_size, height_size=height_size, field_name=field.name, required=required, value=value )


            else:
                # 5、时间字段
                if type(field) == dj_models.DateTimeField:
                    input_type = "datetime-local"
                elif type(field) == dj_models.DateField:
                    input_type = "date"
                elif type(field) == dj_models.TimeField:
                    input_type = "time"

                # 6、EmailField
                elif type(field) == dj_models.EmailField:
                    input_type = "email"

                # 7、其他字段
                else:
                    input_type = "text"

                row_ele += '''<input type="{input_type}" name="{field_name}" {required} style="width: {width_size};height: {height_size};" value="{value}">
                           '''.format(input_type=input_type, field_name=field.name, required=required, width_size=width_size, height_size=height_size, value=value)

            row_ele += '<hr/>' #水平线

    return mark_safe(row_ele)