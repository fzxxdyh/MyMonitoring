



if __name__ == '__main__':
    import os
    import django
    import getpass
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyMonitoring.settings')
    django.setup()
    from monitor.models import Host
    from monitor.utils import get_encrypt_value

    for i in range(100):
        ip = '200.100.100.%s' % str(i+1)
        port, username, passwd, cpu , memory, disk = 2222, 'dyh', '!!!dyh@123[    ]-_./{}|~', 8, 32, 1024
        host = Host(ip=ip, ssh_port=port, username=username, password=get_encrypt_value(passwd), cpu_num=cpu, memory_total=memory, disk_total=disk)
        host.save()

    print('finish')