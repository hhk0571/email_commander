class Config(object):
    SMTP_SERVER  = "smtp.163.com" # 发送邮件的服务器
    SMTP_PORT    = 0 # 通常设为0即可, 除非服务器指定使用特殊端口
    POP_SERVER   = "pop.163.com" # 接收邮件的服务器
    POP_INTERVAL = 1 # 接收邮件的间隔, 单位为分钟. 建议不要太频繁, 5~10分钟为宜.
    ENABLE_SSL   = False # 是否启用SSL, True(是), False(否)
    USERNAME     = "xxxx@163.com" # 邮箱账户名
    PASSWORD     = "xxxx" # 邮箱账户密码 (有些邮箱用的是授权码)
    ENABLE_PROXY = False # 是否启用代理, True(是), False(否), 如果设为True, 需要配置下面三个参数
    PROXY_TYPE   = 'HTTP' # HTTP, SOCKS4, SOCKS5 三选一, 其中HTTP比较常用
    PROXY_IP     = 'xx.xx.xx.xx' # 代理IP地址
    PROXY_PORT   = 8080 # 代理端口
    DEBUG_LEVEL  = 0 # 0 - disable, 1 - enable
    WHITE_LIST   = { # 白名单(也叫信任名单), 只接受来自下列邮箱的指令
        "xxxx@qq.com",  # 信任邮箱, 可添加多个
        "xxxx@163.com",
    }
