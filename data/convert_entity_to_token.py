import json
import pandas
import logging
from tqdm import tqdm



def convert_address_to_token(address_components: dict, original_address) -> dict:
    """
    将地址组件转换为token级别的NER标注
    
    Args:
        address_components: 地址分类结果的字典
        original_address: 原始地址字符串（用于验证）
    
    Returns:
        dict: 包含tokens和ner_tags的字典
    """
    
    tokens = []
    ner_tags = []
    
    # 创建一个位置映射表，记录每个实体在原始地址中的位置
    entity_positions = []
    
    # 处理每个组件，找到它们在原始地址中的位置
    for component_type, component_value in address_components.items():
        if not component_value:
            continue
        
        # 处理逗号分隔的多个值
        if isinstance(component_value, str) and ',' in component_value:
            entities = [entity.strip() for entity in component_value.split(',')]
        else:
            entities = [component_value]
        
        for entity in entities:
            if not entity:
                continue
            
            # 在原始地址中查找实体的位置
            start_pos = original_address.find(entity)
            if start_pos != -1:
                entity_positions.append({
                    'start': start_pos,
                    'end': start_pos + len(entity),
                    'text': entity,
                    'type': component_type
                })
    
    # 按在原始地址中的位置排序
    entity_positions.sort(key=lambda x: x['start'])
    
    # 现在按顺序处理每个字符
    current_pos = 0
    for entity in entity_positions:
        # 处理实体前的文本（如果有）
        if current_pos < entity['start']:
            gap_text = original_address[current_pos:entity['start']]
            for char in gap_text:
                tokens.append(char)
                ner_tags.append('O')
        
        # 处理实体本身 - 使用BIOES标注
        entity_text = entity['text']
        entity_length = len(entity_text)
        
        for i, char in enumerate(entity_text):
            tokens.append(char)
            if entity_length == 1:
                # 单字符实体用S-
                ner_tags.append(f"S-{entity['type']}")
            elif i == 0:
                # 开始字符用B-
                ner_tags.append(f"B-{entity['type']}")
            elif i == entity_length - 1:
                # 结束字符用E-
                ner_tags.append(f"E-{entity['type']}")
            else:
                # 中间字符用I-
                ner_tags.append(f"I-{entity['type']}")
        
        current_pos = entity['end']
    
    # 处理剩余文本（如果有）
    if current_pos < len(original_address):
        remaining_text = original_address[current_pos:]
        for char in remaining_text:
            tokens.append(char)
            ner_tags.append('O')
    
    return {
        "result": {
            "tokens": tokens,
            "ner_tags": ner_tags,
            "text": original_address
        }
    }

def batch_convert_entity_to_token(input_file, output_file):
    """
    主函数，处理输入文件并生成输出文件
    
    Args:
        input_file: 输入的jsonl文件路径（包含实体标注）
        output_file: 输出的jsonl文件路径（包含token级别的NER标注）
    """
    logger = logging.Logger(name="extract_address")
    
    input_ori_data = []
    result = []
    entities = []
    entities_set = set()
    entity_type_list = {}

    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                data = json.loads(line)
                address = data['address']
                entities = data['entities']

                token_data = convert_address_to_token(entities, address)

                result.append(token_data['result'])

                # 转换为11级分类
                if line_num % 100 == 0:
                    logger.info(f"Processed {line_num} lines")
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error at line {line_num}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error processing line {line_num}: {e}")
                continue

    with open(output_file, 'w', encoding='utf-8') as f:
        for no,line in enumerate(tqdm(result, desc="处理地址")):
            # 写入结果到jsonl文件
            f.write(json.dumps(line, ensure_ascii=False) + '\n')
            f.flush()  # 确保实时写入
    
    print(f"处理完成！结果已保存到: {output_file}")


    print("行号", len(result))


if __name__ == "__main__":
    input_file = "alibaba_opensource_data/format_entity_data/alibaba_formatted_entity.jsonl"
    output_file = "alibaba_opensource_data/bio_token/alibaba_tokens.jsonl"

    batch_convert_entity_to_token(input_file, output_file)
    




