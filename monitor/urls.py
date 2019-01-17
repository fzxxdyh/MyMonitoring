"""MyMonitoring URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from . import views

urlpatterns = [
    url(r'^$', views.index, name="monitor_index"),
    url(r'^hostnote/(?P<ip>\d+.\d+.\d+.\d+)/', views.hostnote, name="hostnote"),
    url(r'^hostlist/', views.hostlist, name="hostlist"),
    url(r'^host_delete/(?P<ip>\d+.\d+.\d+.\d+)/', views.host_delete, name="host_delete"),
    url(r'^hostbase/', views.hostbase, name="hostbase"),
    url(r'^hostperformance/', views.hostperformance, name="hostperformance"),
    url(r'^hostmonitor/', views.hostmonitor, name="hostmonitor"),
    url(r'^addrule/', views.addrule, name="addrule"),
    url(r'^rule_list/(?P<rule_id>\d+)/', views.rule_modify, name="rule_modify"),
    url(r'^rule_list/', views.rule_list, name="rule_list"),
    url(r'^rule_delete/(?P<rule_id>\d+)/', views.rule_delete, name="rule_delete"),
    url(r'^rule_has_host/(?P<rule_id>\d+)/', views.rule_has_host, name="rule_has_host"),
    url(r'^host_rule_set/', views.host_rule_set, name="host_rule_set"),
    url(r'^host_ip_rule/(?P<host_ip>\d+.\d+.\d+.\d+)/', views.host_ip_rule, name="host_ip_rule"),
    url(r'^host_remove_rule/(?P<host_ip>\d+.\d+.\d+.\d+)/(?P<rule_id>\d+)/', views.host_remove_rule, name="host_remove_rule"),
    url(r'^userkey/del/(?P<ip>\d+.\d+.\d+.\d+)/(?P<keyname>\w+)/', views.userkey_del, name="userkey_del"),
    url(r'^userkey/', views.userkey, name="userkey"),
    url(r'^userkey_host/(?P<ip>\d+.\d+.\d+.\d+)/', views.userkey_host, name="userkey_host"),
    url(r'^hosthistory/(?P<ip>\d+.\d+.\d+.\d+)/', views.hosthistory_ip, name="hosthistory_ip"),
    url(r'^hosthistory/', views.hosthistory, name="hosthistory"),
    url(r'^mailhistory/(?P<id>\d+)/', views.mailhistory_id, name="mailhistory_id"),
    url(r'^mailhistory/', views.mailhistory, name="mailhistory"),
    url(r'^script/addhost/', views.addhost, name="addhost"),
    url(r'^script/hostinfo/(?P<id>\d+)/', views.script_modifyhost, name="script_modifyhost"),
    url(r'^script/del_host/(?P<id>\d+)/', views.script_del_host, name="script_del_host"),
    url(r'^script/hostinfo/', views.script_hostinfo, name="script_hostinfo"),
    url(r'^script/status/', views.script_status, name="script_status"),
    url(r'^new/(?P<model_name>[\w_][\w\d_]*)/', views.new_obj, name="new_obj"), #字母或_开头，后面是字母数字_，重复0+次
    url(r'^del/(?P<model_name>[\w_][\w\d_]*)/(?P<obj_id>\d+)/', views.del_obj, name="del_obj"),
    url(r'^update/(?P<model_name>[\w_][\w\d_]*)/(?P<obj_id>\d+)/', views.update_obj, name="update_obj"),
    url(r'^select/(?P<model_name>[\w_][\w\d_]*)/', views.select_model, name="select_model"),



]
