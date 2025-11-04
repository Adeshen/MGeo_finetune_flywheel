# MGEO 训练配置文件说明

## 使用方法

### 1. 创建默认配置文件
```bash
python mgeo_finetune.py --create-config
```

### 2. 使用默认配置训练
```bash
python mgeo_finetune.py
```

### 3. 使用指定配置文件训练
```bash
python mgeo_finetune.py --config configs/train_config.ini
```

## 配置文件格式

配置文件采用 INI 格式，包含以下几个部分：

### [model] 模型配置
- `model_id`: 基础模型ID或本地路径

### [data] 数据配置
- `train_file`: 训练数据文件路径
- `test_file`: 验证数据文件路径

### [training] 训练参数
- `max_epochs`: 训练轮数
- `batch_size`: 批次大小
- `learning_rate`: 学习率
- `sequence_length`: 序列长度

### [output] 输出配置
- `output_dir`: 输出目录前缀
- `model_name`: 模型保存名称

## 预设配置文件

- `train_config.ini`: 默认配置
- `guangzhou_config.ini`: 广州数据训练配置
- `floor_config.ini`: 楼层数据训练配置

## 注意事项

1. 所有路径都相对于项目根目录
2. 训练完成后会自动添加时间戳到输出目录名
3. 确保数据文件存在，否则会报错

## 示例

### 创建自定义配置
```ini
[model]
model_id = iic/mgeo_backbone_chinese_base

[data]
train_file = ./data/ours/my_train.jsonl
test_file = ./data/ours/my_test.jsonl

[training]
max_epochs = 10
batch_size = 32
learning_rate = 1e-4
sequence_length = 128

[output]
output_dir = my_model
model_name = my_mgeo
```

### 使用已有模型继续训练
```ini
[model]
model_id = ./mgeo_trained_251024

[data]
train_file = ./data/ours/additional_train.jsonl
test_file = ./data/ours/additional_test.jsonl

[training]
max_epochs = 2
batch_size = 64
learning_rate = 1e-5
sequence_length = 256

[output]
output_dir = continued_model
model_name = continued_mgeo
```
