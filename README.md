# MGEO Training Configuration Guide

## Usage

### 1. Create Default Configuration File
```bash
python mgeo_finetune.py --create-config
```

### 2. Train with Default Configuration
```bash
python mgeo_finetune.py
```

### 3. Train with Specified Configuration File
```bash
python mgeo_finetune.py --config configs/train_config.ini
```

## Configuration File Format

The configuration file uses INI format and contains the following sections:

### [model] Model Configuration
- `model_id`: Base model ID or local path

### [data] Data Configuration
- `train_file`: Training data file path
- `test_file`: Validation data file path

### [training] Training Parameters
- `max_epochs`: Number of training epochs
- `batch_size`: Batch size
- `learning_rate`: Learning rate
- `sequence_length`: Sequence length

### [output] Output Configuration
- `output_dir`: Output directory prefix
- `model_name`: Model save name

## Preset Configuration Files

- `train_config.ini`: Default configuration
- `guangzhou_config.ini`: Guangzhou data training configuration
- `floor_config.ini`: Floor data training configuration

## Notes

1. All paths are relative to the project root directory
2. A timestamp will be automatically added to the output directory name after training completion
3. Ensure data files exist, otherwise an error will be thrown

## Examples

### Creating Custom Configuration
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

### Continue Training with Existing Model
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


# reference

https://github.com/PhantomGrapes/MGeo
