# MGeo Training

背景：在大模型能完全胜任自然语言任务(序列标注任务、分类任务、句子关系判断、生成式任务等)的情况，传统预训练Bert模型已经在学界边缘化。

问题：那么在业界，Bert模型还能如何继续发光发热？

搞清楚这个问题之前，首先要明白Bert模型与LLM之间的区别在哪?

LLM vs Bert：速度 与 标注数据
Bert优势是速度快，缺点需要大量标注数据，才能学到足够的泛化性，来处理不同的情况。

LLM优势是少样本快速上线，缺点是成本高、速度慢。



速度差距有多大呢？

1. 在序列标注任务，Bert模型在GPU上，可以在1秒内处理完数十万的文本序列;

2. 而使用LLM(假设20token/s) 需要1秒处理完一条。



标注数据量差距呢？

1. 在序列标注的实体识别任务，Bert模型需要几千条精心标注的数据；

2. 而LLM每个实体类别只需要4、5个案例。



线上NLP实体识别模型，往往需要承担每天的数百万请求。速度的鸿沟是无法弥补的！所以线上还是得用Bert。

但在迭代优化Bert，人工数据标注的成本相当高，这个问题怎么解决呢？

没错，就是使用LLM进行辅助标注数据。



Case案例-MGeo模型: LLM标注数据 + Bert迭代训练
使用LLM进行NLP实体标注，仅需要少量案例就能快速启动，速度远超人工标注。

因而，我们可以结合两者之长，用大模型的聪明，来生成海量数据，优化Bert模型。如此可以使得Bert 又快又准。



## MGeo-数据飞轮
1. 线上模型的自动化推理。
2. 利用智能体与地理知识库对结果，再次进行自动化标注。
3. 将智能体标注与线上推理结果差异化部分，形成反馈训练集。
4. 使用错误数据集合重训练MGeo模型。
5. 数据作为反馈用于Mgeo模型的迭代优化。
6. 重测原始测评数据集，指标提升则可上线新模型。


## 构建训练数据集-insight
在微调Bert模型，训练数据分布至关重要。如果数据样本没有涵盖大部分的分类，出现部分地址分类失败的情况。

我们发现，数据分布特征应该满足以下特性：

1. 定义类-短文本：每个实体类型，都有数条足够短的文本，对实体类型进行定义。
2. 复杂类-长文本：将各个实体类型自由组合，形成各种实体类型排序的长文本。
在实际场景中，我们很容易收集到，一系列的复杂类长文本，但是容易忽略了定义类的短文本。

因而，我们需要增加对短文本的定义，来完善数据分布。
例如，以下为短文本:

```json
{"address": "清远路0000-00号", "entities": {"road": "清远路", "roadno": "0000-00号"}}
{"address": "山口新村", "entities": {"poi": "山口新村"}}
{"address": "九堡商贸中心", "entities": {"poi": "九堡, 商贸中心"}}
```

以下为长文本:

```json
{"address": "浙江省温州市永嘉县五星工业区质检大楼对面旭日印花", "entities": {"prov": "浙江省", "city": "温州市", "district": "永嘉县", "devzone": "五星工业区", "poi": "质检大楼, 旭日印花", "assist": "对面"}}
{"address": "浙江省湖州市市辖区湖州市织里镇河西新村000幢", "entities": {"prov": "浙江省", "city": "湖州市, 湖州市", "district": "市辖区", "town": "织里镇", "poi": "河西新村", "houseno": "000幢"}}
{"address": "洞桥镇上凌工业区宁波市鄞州中旗工艺品有限公司", "entities": {"town": "洞桥镇", "devzone": "上凌工业区", "poi": "宁波市鄞州中旗工艺品有限公司"}}
{"address": "四川省成都市龙泉驿区龙都北路000号天悦国际", "entities": {"prov": "四川省", "city": "成都市", "district": "龙泉驿区", "road": "龙都北路", "roadno": "000号", "poi": "天悦国际"}}
```

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
