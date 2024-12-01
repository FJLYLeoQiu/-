#!/usr/bin/env python3
import os
import sys
import shutil
import datetime
import argparse

def create_backup(file_path, backup_dir='backups'):
    """
    创建文件备份
    :param file_path: 要备份的文件路径
    :param backup_dir: 备份目录
    :return: 备份文件路径
    """
    try:
        # 确保文件存在
        if not os.path.exists(file_path):
            print(f"错误: 文件 {file_path} 不存在")
            return None

        # 创建备份目录
        backup_dir = os.path.join(os.path.dirname(file_path), backup_dir)
        os.makedirs(backup_dir, exist_ok=True)

        # 生成备份文件名
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = os.path.basename(file_path)
        backup_name = f"{os.path.splitext(file_name)[0]}_{timestamp}{os.path.splitext(file_name)[1]}"
        backup_path = os.path.join(backup_dir, backup_name)

        # 创建备份
        shutil.copy2(file_path, backup_path)
        print(f"已创建备份: {backup_path}")
        return backup_path

    except Exception as e:
        print(f"备份失败: {str(e)}")
        return None

def restore_backup(backup_path, target_path=None):
    """
    从备份文件还原
    :param backup_path: 备份文件路径
    :param target_path: 目标还原路径，如果为None则还原到原位置
    :return: 是否成功
    """
    try:
        if not os.path.exists(backup_path):
            print(f"错误: 备份文件 {backup_path} 不存在")
            return False

        if target_path is None:
            # 从备份文件名推断原始文件路径
            original_name = os.path.basename(backup_path).split('_')[0]
            target_path = os.path.join(os.path.dirname(os.path.dirname(backup_path)), 
                                     original_name + os.path.splitext(backup_path)[1])

        # 创建还原前的备份
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        current_backup = os.path.join(os.path.dirname(backup_path), 
                                    f"pre_restore_{timestamp}{os.path.splitext(target_path)[1]}")
        
        if os.path.exists(target_path):
            shutil.copy2(target_path, current_backup)
            print(f"已创建还原前备份: {current_backup}")

        # 还原文件
        shutil.copy2(backup_path, target_path)
        print(f"已还原文件到: {target_path}")
        return True

    except Exception as e:
        print(f"还原失败: {str(e)}")
        return False

def list_backups(file_path, backup_dir='backups'):
    """
    列出指定文件的所有备份
    :param file_path: 原始文件路径
    :param backup_dir: 备份目录
    :return: 备份文件列表
    """
    try:
        backup_dir = os.path.join(os.path.dirname(file_path), backup_dir)
        if not os.path.exists(backup_dir):
            print(f"备份目录不存在: {backup_dir}")
            return []

        file_name = os.path.splitext(os.path.basename(file_path))[0]
        backups = []
        
        for f in os.listdir(backup_dir):
            if f.startswith(file_name) and '_2' in f:  # 确保是带时间戳的备份文件
                backup_path = os.path.join(backup_dir, f)
                timestamp = f.split('_')[1].split('.')[0]
                date = datetime.datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
                backups.append((date, backup_path))

        # 按时间排序
        backups.sort(reverse=True)
        return [b[1] for b in backups]

    except Exception as e:
        print(f"列出备份失败: {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(description='文件备份和还原工具')
    parser.add_argument('action', choices=['backup', 'restore', 'list'], help='要执行的操作')
    parser.add_argument('file_path', help='要操作的文件路径')
    parser.add_argument('--backup-dir', default='backups', help='备份目录名称')
    parser.add_argument('--restore-path', help='还原目标路径（仅用于restore操作）')

    args = parser.parse_args()

    if args.action == 'backup':
        create_backup(args.file_path, args.backup_dir)
    elif args.action == 'restore':
        restore_backup(args.file_path, args.restore_path)
    elif args.action == 'list':
        backups = list_backups(args.file_path, args.backup_dir)
        if backups:
            print("\n可用的备份文件:")
            for i, backup in enumerate(backups, 1):
                print(f"{i}. {backup}")
        else:
            print("没有找到备份文件")

if __name__ == '__main__':
    main()
