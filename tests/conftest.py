"""测试默认使用 test 环境，需在导入应用配置之前生效。"""

import os

os.environ["APP_ENV"] = "test"
