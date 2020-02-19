class Config(object):
    SMTP_SERVER  = "smtp.163.com"
    SMTP_PORT    = 0
    POP_SERVER   = "pop.163.com"
    POP_INTERVAL = 1 # in minutes
    ENABLE_SSL   = False
    USERNAME     = "xxxx@163.com"
    PASSWORD     = "xxxx"
    DEBUG_LEVEL  = 0 # 0 - disable, 1 - enable
    WHITE_LIST   = {
        USERNAME,
        "xxxx@qq.com",
    }
