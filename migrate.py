#!/usr/bin/env python
"""
数据库迁移管理工具

这是一个便捷的命令行工具,用于管理Alembic数据库迁移。

使用方法:
    python migrate.py upgrade           # 升级到最新版本
    python migrate.py downgrade         # 降级一个版本
    python migrate.py current           # 查看当前版本
    python migrate.py history           # 查看迁移历史
    python migrate.py revision "描述"   # 创建新迁移
    python migrate.py stamp head        # 标记数据库为最新版本(不执行迁移)
"""

import sys
import subprocess
from pathlib import Path


def run_alembic_command(args: list[str]) -> int:
    """运行Alembic命令"""
    cmd = ["alembic"] + args
    print(f"执行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n可用命令:")
        print("  upgrade              - 升级到最新版本")
        print("  downgrade            - 降级一个版本")
        print("  current              - 查看当前版本")
        print("  history              - 查看迁移历史")
        print("  revision <message>   - 创建新迁移")
        print("  stamp <revision>     - 标记数据库版本(不执行迁移)")
        return 1

    command = sys.argv[1].lower()

    if command == "upgrade":
        return run_alembic_command(["upgrade", "head"])
    
    elif command == "downgrade":
        # 降级一个版本
        return run_alembic_command(["downgrade", "-1"])
    
    elif command == "current":
        return run_alembic_command(["current"])
    
    elif command == "history":
        return run_alembic_command(["history", "--verbose"])
    
    elif command == "revision":
        if len(sys.argv) < 3:
            print("错误: 请提供迁移描述")
            print("用法: python migrate.py revision \"迁移描述\"")
            return 1
        message = sys.argv[2]
        return run_alembic_command(["revision", "--autogenerate", "-m", message])
    
    elif command == "stamp":
        if len(sys.argv) < 3:
            print("错误: 请提供版本号")
            print("用法: python migrate.py stamp <revision>")
            print("常用: python migrate.py stamp head  # 标记为最新版本")
            return 1
        revision = sys.argv[2]
        return run_alembic_command(["stamp", revision])
    
    else:
        print(f"未知命令: {command}")
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main())
