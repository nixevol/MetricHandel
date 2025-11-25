from data_processor import process_config, process_multiple_configs
from pathlib import Path


def main():
    config_files = list(Path('./Models').glob('*.json'))
    results = process_multiple_configs(config_files)
    for config, count in results.items():
        print(f'{config}: 导入 {count} 条数据')


if __name__ == '__main__':
    main()
