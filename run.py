#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bottle-Agent 快速启动脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from main import main

if __name__ == "__main__":
    main()