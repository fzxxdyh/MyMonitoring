import configparser

conf = configparser.ConfigParser()
conf.read("config.ini", encoding="utf-8")

print(dir(conf))

for k,v in conf.items("Userkey"):
    print(k, v)