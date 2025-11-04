import os
import argparse
import configparser
from datetime import datetime
from modelscope.msdatasets import MsDataset
from modelscope.metainfo import Trainers, Preprocessors
from modelscope.utils.constant import ModelFile, Tasks
from modelscope.trainers import build_trainer

def load_config(config_path):
    """加载训练配置文件"""
    config = configparser.ConfigParser()
    config.read(config_path, encoding='utf-8')
    
    # 验证必要的配置项
    required_sections = ['model', 'data', 'training', 'output']
    for section in required_sections:
        if not config.has_section(section):
            raise ValueError(f"配置文件缺少必要的 [{section}] 部分")
    
    return config

def create_default_config(config_path):
    """创建默认配置文件"""
    config = configparser.ConfigParser()
    
    config['model'] = {
        'model_id': 'iic/mgeo_backbone_chinese_base'
    }
    
    config['data'] = {
        'train_file': './data/ours/guangzhou_train_1024.jsonl',
        'test_file': './data/ours/guangzhou_testset_file_1020.jsonl'
    }
    
    config['training'] = {
        'max_epochs': '3',
        'batch_size': '128',
        'learning_rate': '3e-4',
        'sequence_length': '256'
    }
    
    config['output'] = {
        'output_dir': 'tmp_dir',
        'model_name': 'mgeo_trained'
    }
    
    # 确保配置目录存在
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        config.write(f)
    
    print(f"已创建默认配置文件: {config_path}")
    return config

def finetune(model_id,
             train_dataset,
             eval_dataset,
             name=Trainers.nlp_text_ranking_trainer,
             cfg_modify_fn=None,
             **kwargs):
    kwargs = dict(
        model=model_id,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        work_dir=tmp_dir,
        cfg_modify_fn=cfg_modify_fn,
        **kwargs)

    os.environ['LOCAL_RANK'] = '0'
    trainer = build_trainer(name=name, default_args=kwargs)
    trainer.train()

def cfg_modify_fn(cfg, config, label_enumerate_values, trainset_length):
    """修改训练配置"""
    cfg.task = 'token-classification'
    cfg['dataset'] = {
        'train': {
            'labels': label_enumerate_values,
            'first_sequence': 'tokens',
            'label': 'ner_tags',
            'sequence_length': config.getint('training', 'sequence_length')
        }
    }
    cfg['preprocessor'] = {
        'type': 'token-cls-tokenizer',
        'padding': 'max_length'
    }
    cfg.train.max_epochs = config.getint('training', 'max_epochs')
    cfg.train.dataloader.batch_size_per_gpu = config.getint('training', 'batch_size')
    cfg.train.optimizer.lr = config.getfloat('training', 'learning_rate')
    cfg.train.hooks = [
    {
        'type': 'CheckpointHook',
        'interval': 1
    },
    {
        'type': 'TextLoggerHook',
        'interval': 100
    }, {
        'type': 'IterTimerHook'
    }, {
        'type': 'EvaluationHook',
        'by_epoch': True
    }]
    cfg.train.lr_scheduler.total_iters = int(trainset_length / 32) * cfg.train.max_epochs

    return cfg

def get_label_list(labels):
    unique_labels = set()
    for label in labels:
        unique_labels = unique_labels | set(label)
    label_list = list(unique_labels)
    label_list.sort()
    return label_list

def main():
    """主函数：基于配置文件启动训练"""
    parser = argparse.ArgumentParser(description='MGEO 模型微调训练')
    parser.add_argument('--config', '-c', type=str, 
                       default='configs/train_config.ini',
                       help='训练配置文件路径')
    parser.add_argument('--create-config', action='store_true',
                       help='创建默认配置文件')
    
    args = parser.parse_args()
    
    # 如果指定创建配置文件
    if args.create_config:
        create_default_config(args.config)
        return
    
    # 检查配置文件是否存在
    if not os.path.exists(args.config):
        print(f"配置文件不存在: {args.config}")
        print("使用 --create-config 参数创建默认配置文件")
        return
    
    # 加载配置
    config = load_config(args.config)
    print(f"使用配置文件: {args.config}")
    
    # 从配置文件读取参数
    model_id = config.get('model', 'model_id')
    train_file = config.get('data', 'train_file')
    test_file = config.get('data', 'test_file')
    output_dir_name = config.get('output', 'output_dir')
    model_name = config.get('output', 'model_name')
    
    print(f"模型ID: {model_id}")
    print(f"训练数据: {train_file}")
    print(f"测试数据: {test_file}")
    
    # 检查数据文件是否存在
    if not os.path.exists(train_file):
        raise FileNotFoundError(f"训练数据文件不存在: {train_file}")
    if not os.path.exists(test_file):
        raise FileNotFoundError(f"测试数据文件不存在: {test_file}")
    
    # 加载数据集
    train_dataset = MsDataset.load('json', data_files={'train': [train_file]})
    dev_dataset = MsDataset.load('json', data_files={'validation': [test_file]})
    
    # 获取标签列表
    label_enumerate_values = get_label_list(train_dataset._hf_ds['ner_tags'] + dev_dataset._hf_ds['ner_tags'])
    print(f"标签列表: {label_enumerate_values}")
    
    # 创建带时间戳的输出目录
    timestamp = datetime.now().strftime("%y%m%d_%H%M")
    global tmp_dir
    tmp_dir = f"{output_dir_name}_{timestamp}"
    
    # 开始训练
    print("开始训练...")
    finetune(
        model_id=model_id,
        train_dataset=train_dataset,
        eval_dataset=dev_dataset,
        cfg_modify_fn=lambda cfg: cfg_modify_fn(cfg, config, label_enumerate_values, len(train_dataset)),
        name='nlp-base-trainer')
    
    # 输出结果
    final_output_dir = os.path.join(tmp_dir, ModelFile.TRAIN_OUTPUT_DIR)
    print(f'模型已保存到: {final_output_dir}')
    
    # 可选：重命名输出目录
    if model_name != 'mgeo_trained':
        new_name = f"{model_name}_{timestamp}"
        new_path = os.path.join(os.path.dirname(tmp_dir), new_name)
        if os.path.exists(tmp_dir):
            os.rename(tmp_dir, new_path)
            print(f'输出目录已重命名为: {new_path}')

if __name__ == '__main__':
    main()